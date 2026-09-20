"""Surface forms of ontology entities, and how safely each can be matched in text.

This module exists because of a single problem that decides whether automated
extraction is useful or worthless: many ornamental trait names are ordinary
English words.

`black`, `white`, `blue`, `gold` and `yellow` are trait names here. So is
`panda`. So is `deme` -- which in a genetics paper almost always means a local
interbreeding population, not the protruding-eye medaka trait. Matching those
forms naively against the literature produces a stream of false co-mentions that
a reviewer then has to wade through, and a review queue nobody trusts is a review
queue nobody reads.

So every surface form is classified. Distinctive forms (`orochi`, `zic1`,
`hirenaga`, `toumeirin`) match on their own. Ambiguous ones only count when the
surrounding sentence independently establishes that it is talking about medaka
or about an unambiguous entity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from neo4j import Session

from .vocabulary import ENTITY_LABELS, NodeLabel

#: Trait and gene names that are also ordinary English words, or that carry a
#: well-established unrelated meaning in genetics. Curated explicitly rather than
#: derived from a heuristic, because the cost of a wrong call is asymmetric: a
#: form wrongly marked ambiguous loses some recall, while a form wrongly marked
#: safe poisons the review queue.
AMBIGUOUS_SURFACE_FORMS: frozenset[str] = frozenset(
    {
        # Colour words used as trait names
        "black",
        "white",
        "blue",
        "gold",
        "yellow",
        # Ordinary nouns and verbs
        "panda",
        "swallow",
        "aurora",
        "longfin",
        "bigeye",
        "albino",
        "rame",
        # "deme" is a standard population-genetics term. In this corpus the
        # trait meaning is almost certainly the rarer one.
        "deme",
        # Laboratory mutant names that read as ordinary phrases
        "guanineless",
        "few melanophore",
        "leucophore free",
        "fused centrum",
        # Anatomy and phenotype terms that are generic on their own
        "scale",
        "iris",
        "peritoneum",
        "dorsal fin",
        "caudal fin",
        "vertebral column",
        "melanogenesis",
        "cAMP signaling",
        "skeletal system development",
        "chromatophore development",
        "iridophore development",
        "dorsoventral patterning",
        "loss of melanophores",
        "loss of xanthophores",
        "fin ray elongation",
        "fin membrane elongation",
        "shortened body axis",
        "eyeball protrusion",
        "eyeball enlargement",
        "hyper-melanism",
        "iridophore depletion",
        "ectopic dorsal iridophore",
        "bioelectric fin size regulation",
    }
)

#: Terms that establish a sentence really is about this organism. An ambiguous
#: form only counts in their company.
MEDAKA_ANCHORS: tuple[str, ...] = (
    "medaka",
    "oryzias",
    "latipes",
)

#: Forms shorter than this are never matched on their own, whatever they are.
#: Two- and three-character strings collide with abbreviations everywhere.
MIN_SAFE_LENGTH = 4


@dataclass(frozen=True)
class SurfaceForm:
    """One string that may denote one entity."""

    text: str
    entity_id: str
    entity_name: str
    label: NodeLabel
    ambiguous: bool

    @property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(rf"(?<!\w){re.escape(self.text)}(?!\w)", re.IGNORECASE)


@dataclass
class Lexicon:
    """Every surface form the graph knows about, indexed for matching."""

    forms: list[SurfaceForm] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.forms)

    @property
    def safe(self) -> list[SurfaceForm]:
        return [f for f in self.forms if not f.ambiguous]

    @property
    def ambiguous(self) -> list[SurfaceForm]:
        return [f for f in self.forms if f.ambiguous]

    def for_label(self, label: NodeLabel) -> list[SurfaceForm]:
        return [f for f in self.forms if f.label is label]


def is_ambiguous(text: str) -> bool:
    """Whether a surface form needs corroboration before it counts."""
    normalized = text.strip().lower()
    if len(normalized) < MIN_SAFE_LENGTH:
        return True
    if normalized in AMBIGUOUS_SURFACE_FORMS:
        return True
    # A bare number or a token with no letters is never a usable name.
    return not any(ch.isalpha() for ch in normalized)


def has_medaka_anchor(text: str) -> bool:
    lowered = text.lower()
    return any(anchor in lowered for anchor in MEDAKA_ANCHORS)


_LEXICON_QUERY = """
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN $labels)
RETURN n.id AS id, n.name AS name, head(labels(n)) AS label,
       coalesce(n.aliases, []) AS aliases
"""


def build_lexicon(session: Session) -> Lexicon:
    """Read every entity's name and sourced aliases out of the graph.

    `unverified_labels` are deliberately excluded. They are unsourced
    reconstruction (PRD §2.4), and the corpus is English-language literature in
    which they would not appear anyway -- admitting them would add risk without
    adding reach.
    """
    lexicon = Lexicon()
    seen: set[tuple[str, str]] = set()
    for record in session.run(_LEXICON_QUERY, labels=[x.value for x in ENTITY_LABELS]):
        label = NodeLabel(record["label"])
        for text in [record["name"], *record["aliases"]]:
            if not text:
                continue
            key = (text.lower(), record["id"])
            if key in seen:
                continue
            seen.add(key)
            lexicon.forms.append(
                SurfaceForm(
                    text=text,
                    entity_id=record["id"],
                    entity_name=record["name"],
                    label=label,
                    ambiguous=is_ambiguous(text),
                )
            )
    return lexicon


def find_mentions(text: str, lexicon: Lexicon) -> list[SurfaceForm]:
    """Surface forms occurring in `text`, with the ambiguity rule applied.

    An ambiguous form is admitted only if the same text independently mentions
    medaka or contains at least one unambiguous entity form. That second route
    matters: a sentence naming `zic1` has already proved what it is about, so
    `black` alongside it is far more likely to be the trait.
    """
    safe_hits = [f for f in lexicon.safe if f.pattern.search(text)]
    corroborated = bool(safe_hits) or has_medaka_anchor(text)
    if not corroborated:
        return safe_hits

    ambiguous_hits = [f for f in lexicon.ambiguous if f.pattern.search(text)]
    return safe_hits + ambiguous_hits


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def sentences(text: str) -> list[str]:
    """Split into sentences well enough for co-mention windows.

    Deliberately crude. Scientific prose defeats naive splitters with `et al.`,
    `Fig. 2`, `e.g.` and species abbreviations, so the few guards below cover the
    cases that actually appear in this corpus; anything subtler would need a real
    parser and would not change which mentions get found, only where the window
    edges fall.
    """
    protected = text
    for abbreviation in ("et al.", "e.g.", "i.e.", "Fig.", "cf.", "ca.", "approx."):
        protected = protected.replace(abbreviation, abbreviation.replace(".", "\x00"))
    parts = _SENTENCE_SPLIT.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]
