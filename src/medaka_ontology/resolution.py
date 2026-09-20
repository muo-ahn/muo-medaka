"""Map extracted names onto existing entities, and propose genuinely new ones.

Issue #1 §6. The rule that matters: low confidence produces a review candidate,
never a silent merge. PRD §8 is explicit that a shared name is not evidence of
shared biology, and an ontology that merges on a fuzzy string match acquires
entities that are quietly two things at once -- the `panda` collision in the seed
data is what that looks like when it has already happened.

On proposing new entities, there is a limit worth stating plainly. The extractor
finds co-mentions of entities the graph already knows, so by construction it
cannot discover a trait it has never heard of; that would need named-entity
recognition, which is the kind of inference this pipeline refuses to make
(see `extraction`). What it can do honestly is notice **gene symbols**, because
gene nomenclature is a real orthographic convention rather than a guess about
meaning: a lowercase alphanumeric token ending in a digit, sitting in a sentence
that also names a known trait, is a gene symbol far more often than it is
anything else. Those become NEW proposals for a human to confirm.

New ornamental traits are therefore expected to arrive through a person reading
the review queue and noticing an unfamiliar name in a quote -- not through this
module inventing one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from neo4j import Session

from .lexicon import Lexicon, find_mentions, has_medaka_anchor, sentences
from .vocabulary import NodeLabel, ResolutionStatus, ReviewReason

#: Gene-symbol orthography: lowercase letters then digits, optionally a trailing
#: letter (`zic1`, `slc45a2`, `kcnq5a`, `adcy5`, `pnp4a`).
#:
#: The trailing digit is required, and that is a real limitation rather than an
#: oversight. Symbols with no digit -- `tyr`, `kita`, `pmela`, `mitfa` -- are
#: orthographically indistinguishable from ordinary words, so this rule cannot
#: see them and will not pretend to. Loosening it to accept pure-alphabetic
#: tokens would propose every noun in the paper as a gene, which is worse than
#: missing some: the review queue is the scarce resource here.
#:
#: Digitless symbols therefore have to arrive through a person reading a quote in
#: the queue, the same route as a new trait name.
GENE_SYMBOL = re.compile(r"\b([a-z]{2,8}\d{1,3}[a-z]?)\b")

#: Structural references that match the gene-symbol shape. Figure, table and
#: chromosome labels are pervasive in this corpus, and medaka has 24 chromosomes,
#: so the ranges are generated rather than listed by hand -- the first version
#: stopped at chr9 and duly proposed `chr21` as a gene.
_STRUCTURAL_PREFIXES = ("fig", "figure", "table", "chr", "chromosome", "panel", "lane")
_COUNTER_PREFIXES = ("no", "type", "step", "day", "week", "group", "exp", "set", "run")

NOT_GENE_SYMBOLS: frozenset[str] = frozenset(
    [f"{prefix}{n}" for prefix in _STRUCTURAL_PREFIXES for n in range(1, 41)]
    + [f"{prefix}{n}" for prefix in _COUNTER_PREFIXES for n in range(1, 21)]
    + [
        # Reagents and buffers
        "co2", "h2o", "mgcl2", "cacl2", "nacl2", "kcl2", "naoh", "hcl1",
        "ph5", "ph6", "ph7", "ph8", "ph9",
        # Generation and progeny labels
        "f1", "f2", "f3", "p1", "p2", "n1", "n2",
    ]
)


@dataclass
class Resolution:
    """What an extracted name mapped to."""

    query_name: str
    label: NodeLabel
    status: ResolutionStatus
    entity_id: str | None = None
    entity_name: str | None = None
    alternatives: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.status in {ResolutionStatus.AMBIGUOUS, ResolutionStatus.NEW}

    @property
    def review_reasons(self) -> list[ReviewReason]:
        if self.status is ResolutionStatus.AMBIGUOUS:
            return [ReviewReason.LOW_RESOLUTION_CONFIDENCE]
        if self.status is ResolutionStatus.NEW:
            reasons = [ReviewReason.LOW_RESOLUTION_CONFIDENCE]
            if self.label is NodeLabel.ORNAMENTAL_TRAIT:
                reasons.append(ReviewReason.NEW_ORNAMENTAL_TRAIT)
            return reasons
        return []


_EXACT = """
MATCH (n) WHERE any(l IN labels(n) WHERE l = $label)
  AND toLower(n.name) = toLower($name)
RETURN n.id AS id, n.name AS name
"""

_BY_ALIAS = """
MATCH (n) WHERE any(l IN labels(n) WHERE l = $label)
  AND any(a IN coalesce(n.aliases, []) WHERE toLower(a) = toLower($name))
RETURN n.id AS id, n.name AS name
"""

#: Cross-label check. A name that already exists under a *different* label is
#: not a match, but it is a reason to stop and look: it usually means either a
#: genuine collision or an extraction that guessed the wrong type.
_ANY_LABEL = """
MATCH (n) WHERE toLower(n.name) = toLower($name)
RETURN n.id AS id, n.name AS name, head(labels(n)) AS label
"""


def resolve(session: Session, label: NodeLabel, name: str) -> Resolution:
    """Look one name up, preferring exact match, then sourced alias."""
    exact = [dict(r) for r in session.run(_EXACT, label=label.value, name=name)]
    if len(exact) == 1:
        return Resolution(
            name, label, ResolutionStatus.RESOLVED_EXACT, exact[0]["id"], exact[0]["name"]
        )
    if len(exact) > 1:
        return Resolution(
            name, label, ResolutionStatus.AMBIGUOUS,
            alternatives=[r["id"] for r in exact],
        )

    by_alias = [dict(r) for r in session.run(_BY_ALIAS, label=label.value, name=name)]
    if len(by_alias) == 1:
        return Resolution(
            name, label, ResolutionStatus.RESOLVED_ALIAS,
            by_alias[0]["id"], by_alias[0]["name"],
        )
    if len(by_alias) > 1:
        return Resolution(
            name, label, ResolutionStatus.AMBIGUOUS,
            alternatives=[r["id"] for r in by_alias],
        )

    other_label = [
        dict(r) for r in session.run(_ANY_LABEL, name=name) if r["label"] != label.value
    ]
    if other_label:
        return Resolution(
            name, label, ResolutionStatus.AMBIGUOUS,
            alternatives=[f"{r['label']}:{r['id']}" for r in other_label],
        )

    return Resolution(name, label, ResolutionStatus.NEW)


@dataclass
class ProposedGene:
    """A gene symbol seen beside a known entity but absent from the ontology."""

    symbol: str
    quote: str
    paper_id: str
    section: str | None
    near_entities: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        from .models import content_digest

        return "newgene:" + content_digest(self.paper_id, self.symbol)


def propose_new_genes(
    paper_id: str,
    text: str,
    lexicon: Lexicon,
    section: str | None = None,
) -> list[ProposedGene]:
    """Gene-symbol-shaped tokens the ontology does not have.

    Only sentences that already name a known entity, or medaka itself, are
    considered. Without that guard the pattern would harvest every symbol in
    every paper, which is a way to add thousands of genes and no knowledge.
    """
    known = {form.text.lower() for form in lexicon.forms}
    proposals: dict[str, ProposedGene] = {}

    for sentence in sentences(text):
        mentions = find_mentions(sentence, lexicon)
        if not mentions and not has_medaka_anchor(sentence):
            continue
        for match in GENE_SYMBOL.finditer(sentence):
            symbol = match.group(1).lower()
            if symbol in known or symbol in NOT_GENE_SYMBOLS:
                continue
            existing = proposals.get(symbol)
            if existing is not None:
                continue
            proposals[symbol] = ProposedGene(
                symbol=symbol,
                quote=sentence,
                paper_id=paper_id,
                section=section,
                near_entities=sorted({m.entity_name for m in mentions}),
            )
    return list(proposals.values())
