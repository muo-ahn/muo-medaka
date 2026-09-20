"""Propose candidate knowledge from full text. Never assert it.

Issue #1 §4: "Extraction should produce candidate knowledge, not automatically
asserted truth."

What this does is narrow on purpose. It finds sentences where two entities the
ontology already knows are named together, and offers that sentence as a
candidate claim for a human to accept or reject. It does not parse the sentence,
does not decide what the authors meant, and does not resolve negation -- a
sentence saying "no coding mutations were found in pnp4a" produces the same
candidate as one asserting the opposite, and the reviewer reads the quote.

That is a deliberate ceiling, not an unfinished feature. This repository exists
because trait-gene statements circulate without their evidence grade until they
harden into fact (PRD §2.2, §5). An extractor that guessed at claims would
manufacture exactly that, at machine speed, with a provenance trail that looked
respectable. Co-mention plus the verbatim sentence is the strongest thing that
can be produced here without inventing confidence.

Evidence level is treated the same way. Cue phrases suggest a level and the cue
is recorded alongside, but the candidate itself carries UNKNOWN until a person
accepts it, and any candidate whose cue points at causal or functional evidence
is flagged for review no matter what.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .acquisition import FullText
from .lexicon import Lexicon, find_mentions, sentences
from .models import MEDAKA
from .vocabulary import (
    PREDICATE_SHAPES,
    EvidenceLevel,
    NodeLabel,
    Predicate,
    ReviewReason,
)

#: Tried in order, so the weakest claim that fits a label pair wins. When a
#: sentence could support either "associated with" or "modified by", the
#: ontology should record the one that asserts less.
#:
#: Membership matters as much as order. The relations left out are the ones where
#: co-mention carries no information at all:
#:
#: - `resembles`, `co_occurs_with`, `pleiotropic_with` between two traits. Any
#:   paper listing this study's phenotypes names them together; that is a
#:   sentence about a table, not about resemblance.
#: - `epistatic_with` between two genes. "candidate genes including kcna10,
#:   kcna3, and kcnd3" is an enumeration, and calling it epistasis would be an
#:   invention.
#: - `putatively_same_as`. Asserting a breeder trait and a lab mutant share a
#:   genetic background is exactly the judgement PRD §8 reserves for a person.
#:
#: Dropping them was not a tuning decision. In the first run against real papers
#: they were most of the output, which would have made the review queue
#: unreadable and so made the whole pipeline pointless.
PREDICATE_PREFERENCE: tuple[Predicate, ...] = (
    Predicate.ASSOCIATED_WITH_GENE,
    Predicate.ASSOCIATED_WITH_LOCUS,
    Predicate.HAS_PHENOTYPE,
    Predicate.PARTICIPATES_IN,
    Predicate.AFFECTS_ANATOMY,
    Predicate.MODIFIED_BY,
    Predicate.ORTHOLOG_OF,
    Predicate.CAUSED_BY_VARIANT,
    Predicate.HUMAN_GENE_ASSOCIATED_WITH,
)

#: cue -> the level it hints at. Matched case-insensitively on word boundaries.
LEVEL_CUES: tuple[tuple[str, EvidenceLevel], ...] = (
    (r"genome[- ]edit\w*", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"CRISPR", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"knock[- ]?out", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"knock[- ]?down", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"morpholino", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"phenocop\w+", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"rescue\w*", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"transgenic", EvidenceLevel.FUNCTIONAL_VALIDATION),
    (r"causal variant", EvidenceLevel.CAUSAL_VARIANT),
    (r"responsible for", EvidenceLevel.CAUSAL_VARIANT),
    (r"causative", EvidenceLevel.CAUSAL_VARIANT),
    (r"fine[- ]mapp\w+", EvidenceLevel.FINE_MAPPING),
    (r"positional clon\w+", EvidenceLevel.FINE_MAPPING),
    (r"co[- ]?segregat\w+", EvidenceLevel.FINE_MAPPING),
    (r"genome[- ]wide association", EvidenceLevel.QTL_GWAS_ASSOCIATION),
    (r"\bGWAS\b", EvidenceLevel.QTL_GWAS_ASSOCIATION),
    (r"\bQTL\b", EvidenceLevel.QTL_GWAS_ASSOCIATION),
    (r"linkage analysis", EvidenceLevel.QTL_GWAS_ASSOCIATION),
    (r"RNA[- ]?seq", EvidenceLevel.EXPRESSION_ASSOCIATION),
    (r"expression\w* (?:level|analys|profil)\w*", EvidenceLevel.EXPRESSION_ASSOCIATION),
    (r"\bqPCR\b|\bRT-PCR\b", EvidenceLevel.EXPRESSION_ASSOCIATION),
    (r"in situ hybridi\w+", EvidenceLevel.EXPRESSION_ASSOCIATION),
)

#: Species names that mark text as comparative. Acceptance then applies the
#: existing comparative ceiling, so this is not cosmetic labelling.
SPECIES_CUES: tuple[tuple[str, str], ...] = (
    (r"zebrafish|Danio rerio|\bD\. rerio\b", "Danio rerio"),
    (r"\bmouse\b|\bmice\b|\bmurine\b|Mus musculus", "Mus musculus"),
    (r"\bhuman\b|Homo sapiens|\bpatients?\b", "Homo sapiens"),
    (r"\bfugu\b|Takifugu", "Takifugu rubripes"),
    (r"stickleback|Gasterosteus", "Gasterosteus aculeatus"),
    (r"goldfish|Carassius", "Carassius auratus"),
    (r"corn snake|Pantherophis|\bsnake\b", "Pantherophis guttatus"),
    (r"\bloach\b|Misgurnus|Paramisgurnus", "Misgurnus anguillicaudatus"),
    (r"\bchicken\b|Gallus gallus", "Gallus gallus"),
    (r"\bXenopus\b", "Xenopus laevis"),
    (r"\baxolotl\b|Ambystoma", "Ambystoma mexicanum"),
    (r"\bsalmon\b|Salmo salar", "Salmo salar"),
    (r"\btilapia\b|Oreochromis", "Oreochromis niloticus"),
    (r"\bcarp\b|Cyprinus carpio", "Cyprinus carpio"),
    (r"\bcatfish\b|Ictalurus", "Ictalurus punctatus"),
    (r"\bbetta\b|Betta splendens", "Betta splendens"),
    (r"\bguppy\b|Poecilia reticulata", "Poecilia reticulata"),
)

#: Sentences naming more entities than this are almost always list-like -- a
#: table caption or a summary enumerating every candidate gene -- where
#: co-mention carries no information. Pairs from them would dominate the queue.
MAX_MENTIONS_PER_SENTENCE = 6

#: A single paper should not be able to flood the review queue.
MAX_CANDIDATES_PER_PAPER = 60

_NEGATION = re.compile(
    r"\b(?:no|not|neither|nor|without|failed to|did not|does not|cannot|"
    r"unlikely|rule[sd]? out|absence of)\b",
    re.IGNORECASE,
)


@dataclass
class CandidateMention:
    entity_id: str
    entity_name: str
    label: NodeLabel
    matched_text: str
    ambiguous: bool


@dataclass
class CandidateClaim:
    """A proposal. Not a claim until a human accepts it."""

    paper_id: str
    predicate: Predicate
    subject: CandidateMention
    object: CandidateMention
    quote: str
    section: str | None = None
    suggested_level: EvidenceLevel = EvidenceLevel.UNKNOWN
    level_cue: str | None = None
    species: str = MEDAKA
    negated: bool = False
    review_reasons: list[ReviewReason] = field(default_factory=list)

    @property
    def id(self) -> str:
        from .models import content_digest

        return "cand:" + content_digest(
            self.paper_id,
            self.predicate.value,
            self.subject.entity_id,
            self.object.entity_id,
            self.quote,
        )

    def as_properties(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "predicate": self.predicate.value,
            "subject_id": self.subject.entity_id,
            "subject_name": self.subject.entity_name,
            "subject_label": self.subject.label.value,
            "subject_matched": self.subject.matched_text,
            "object_id": self.object.entity_id,
            "object_name": self.object.entity_name,
            "object_label": self.object.label.value,
            "object_matched": self.object.matched_text,
            "quote": self.quote,
            "section": self.section,
            "suggested_level": self.suggested_level.value,
            "level_cue": self.level_cue,
            "species": self.species,
            "negated": self.negated,
            "review_reasons": [r.value for r in self.review_reasons],
        }


#: Shapes the vocabulary permits but co-mention cannot support.
#:
#: `ortholog_of` accepts Gene -> Gene so that a medaka-to-medaka paralogue can be
#: recorded by hand. Automatically, though, two medaka genes in one sentence is
#: an enumeration -- "genes crucial for xanthophore development (pax3a, csf1ra,
#: and sox10)" -- and proposing orthology for each pair invents a relationship
#: the sentence never claimed. Cross-species (Gene -> HumanGene) stays allowed,
#: since that is what the relation is actually for here.
UNSUPPORTED_BY_COMENTION: frozenset[tuple[Predicate, NodeLabel, NodeLabel]] = frozenset(
    {(Predicate.ORTHOLOG_OF, NodeLabel.GENE, NodeLabel.GENE)}
)


def predicate_for(subject: NodeLabel, obj: NodeLabel) -> Predicate | None:
    """The weakest predicate whose declared shape accepts this label pair."""
    for predicate in PREDICATE_PREFERENCE:
        subjects, objects = PREDICATE_SHAPES[predicate]
        if subject not in subjects or obj not in objects:
            continue
        if (predicate, subject, obj) in UNSUPPORTED_BY_COMENTION:
            continue
        return predicate
    return None


def detect_level(text: str) -> tuple[EvidenceLevel, str | None]:
    """Strongest cue present, with the phrase that triggered it.

    Returning the cue matters more than returning the level: a reviewer can
    check a phrase, and cannot check a bare label.
    """
    from .vocabulary import EVIDENCE_RANK

    best: tuple[EvidenceLevel, str | None] = (EvidenceLevel.UNKNOWN, None)
    for pattern, level in LEVEL_CUES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and EVIDENCE_RANK[level] > EVIDENCE_RANK[best[0]]:
            best = (level, match.group(0))
    return best


def detect_species(text: str, default: str = MEDAKA) -> str:
    for pattern, species in SPECIES_CUES:
        if re.search(pattern, text, re.IGNORECASE):
            return species
    return default


def detect_paper_species(title: str | None, abstract: str | None) -> str:
    """The organism a paper is *about*, from its title and abstract.

    Sentence-level detection is not enough on its own, and the failure is not
    subtle. A corn-snake chromatophore paper contains the sentence "melanophores
    were characterised by the expression of genes associated with melanogenesis,
    such as MLANA, OCA2, DCT, and TYR" -- which names no species at all. Judged
    sentence by sentence that is a medaka finding, and it would enter the graph
    as one, at full strength, with the comparative ceiling never triggering.

    So the paper's own subject becomes the default for every sentence in it, and
    a sentence naming a different organism can still override. A paper that
    mentions medaka anywhere in its title or abstract is treated as medaka, since
    the sentence-level cue is then the more reliable signal.
    """
    head = f"{title or ''} {abstract or ''}"
    if not head.strip():
        return MEDAKA
    if re.search(r"medaka|Oryzias", head, re.IGNORECASE):
        return MEDAKA
    return detect_species(head)


def _review_reasons(candidate: CandidateClaim) -> list[ReviewReason]:
    reasons: set[ReviewReason] = set()
    # Every candidate is unreviewed by construction; these mark the ones whose
    # cost of being wrong is highest.
    if candidate.suggested_level in {
        EvidenceLevel.CAUSAL_VARIANT,
        EvidenceLevel.FUNCTIONAL_VALIDATION,
    }:
        reasons.add(ReviewReason.NEW_CAUSAL_VARIANT)
    if candidate.predicate is Predicate.CAUSED_BY_VARIANT:
        reasons.add(ReviewReason.NEW_CAUSAL_VARIANT)
    if candidate.suggested_level is EvidenceLevel.UNKNOWN:
        reasons.add(ReviewReason.EVIDENCE_LEVEL_UNCLEAR)
    if candidate.subject.ambiguous or candidate.object.ambiguous:
        reasons.add(ReviewReason.LOW_RESOLUTION_CONFIDENCE)
    return sorted(reasons, key=lambda r: r.value)


def extract_from_text(
    paper_id: str,
    text: str,
    lexicon: Lexicon,
    section: str | None = None,
    default_species: str = MEDAKA,
) -> list[CandidateClaim]:
    """Candidates from one block of text."""
    candidates: list[CandidateClaim] = []
    for sentence in sentences(text):
        mentions = find_mentions(sentence, lexicon)
        # Collapse repeats of the same entity within one sentence.
        unique = {m.entity_id: m for m in mentions}
        if len(unique) < 2 or len(unique) > MAX_MENTIONS_PER_SENTENCE:
            continue

        level, cue = detect_level(sentence)
        species = detect_species(sentence, default=default_species)
        negated = bool(_NEGATION.search(sentence))
        forms = list(unique.values())

        for i, first in enumerate(forms):
            for second in forms[i + 1 :]:
                for subj, obj in ((first, second), (second, first)):
                    predicate = predicate_for(subj.label, obj.label)
                    if predicate is None:
                        continue
                    candidate = CandidateClaim(
                        paper_id=paper_id,
                        predicate=predicate,
                        subject=CandidateMention(
                            subj.entity_id, subj.entity_name, subj.label,
                            subj.text, subj.ambiguous,
                        ),
                        object=CandidateMention(
                            obj.entity_id, obj.entity_name, obj.label,
                            obj.text, obj.ambiguous,
                        ),
                        quote=sentence,
                        section=section,
                        suggested_level=level,
                        level_cue=cue,
                        species=species,
                        negated=negated,
                    )
                    candidate.review_reasons = _review_reasons(candidate)
                    candidates.append(candidate)
                    break  # one direction per pair; the shape decides which
    return candidates


def extract_from_fulltext(
    fulltext: FullText,
    lexicon: Lexicon,
    max_candidates: int = MAX_CANDIDATES_PER_PAPER,
    default_species: str = MEDAKA,
) -> list[CandidateClaim]:
    """Candidates from a paper, section by section so provenance survives."""
    seen: set[str] = set()
    out: list[CandidateClaim] = []
    for name, body in fulltext.sections.items():
        from .acquisition import _is_evidence_section

        if not _is_evidence_section(name):
            continue
        for candidate in extract_from_text(
            fulltext.paper_id, body, lexicon, section=name, default_species=default_species
        ):
            if candidate.id in seen:
                continue
            seen.add(candidate.id)
            out.append(candidate)
            if len(out) >= max_candidates:
                return out
    return out


def extract_from_abstract(
    paper_id: str, abstract: str, lexicon: Lexicon, default_species: str = MEDAKA
) -> list[CandidateClaim]:
    """Fallback for papers with no open full text.

    Kept separate, and the section recorded as `Abstract (no full text)`, so a
    reviewer can see that the paper was never read past its summary rather than
    having to infer it.
    """
    return extract_from_text(
        paper_id,
        abstract,
        lexicon,
        section="Abstract (no full text)",
        default_species=default_species,
    )
