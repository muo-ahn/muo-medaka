"""The controlled vocabulary of the ontology.

PRD §4: "초기에는 relation vocabulary를 과도하게 확장하지 않는다. 새 relation이
필요한 경우 기존 relation으로 표현할 수 없는지 먼저 확인한 뒤 확장한다."

That discipline only holds if something enforces it, so the vocabulary lives here
as closed enums with a declared domain and range, and `validate_claim_shape` runs
on every write path.
"""

from __future__ import annotations

from enum import StrEnum


class NodeLabel(StrEnum):
    """Entity types. PRD §3."""

    ORNAMENTAL_TRAIT = "OrnamentalTrait"
    PHENOTYPE = "Phenotype"
    GENE = "Gene"
    GENETIC_VARIANT = "GeneticVariant"
    LOCUS = "Locus"
    BIOLOGICAL_MECHANISM = "BiologicalMechanism"
    ANATOMY = "Anatomy"
    STRAIN = "Strain"
    # Comparative layer, PRD §10. Distinct labels so that a human phenotype can
    # never be reached from a medaka gene by a careless query.
    HUMAN_GENE = "HumanGene"
    HUMAN_PHENOTYPE = "HumanPhenotype"
    # Provenance and assertion machinery, not domain entities.
    PAPER = "Paper"
    EVIDENCE = "Evidence"
    CLAIM = "Claim"


#: Labels that may appear as the subject or object of a :Claim.
ENTITY_LABELS: frozenset[NodeLabel] = frozenset(
    {
        NodeLabel.ORNAMENTAL_TRAIT,
        NodeLabel.PHENOTYPE,
        NodeLabel.GENE,
        NodeLabel.GENETIC_VARIANT,
        NodeLabel.LOCUS,
        NodeLabel.BIOLOGICAL_MECHANISM,
        NodeLabel.ANATOMY,
        NodeLabel.STRAIN,
        NodeLabel.HUMAN_GENE,
        NodeLabel.HUMAN_PHENOTYPE,
    }
)

#: Short prefix used when minting deterministic entity ids.
LABEL_PREFIX: dict[NodeLabel, str] = {
    NodeLabel.ORNAMENTAL_TRAIT: "trait",
    NodeLabel.PHENOTYPE: "pheno",
    NodeLabel.GENE: "gene",
    NodeLabel.GENETIC_VARIANT: "var",
    NodeLabel.LOCUS: "locus",
    NodeLabel.BIOLOGICAL_MECHANISM: "mech",
    NodeLabel.ANATOMY: "anat",
    NodeLabel.STRAIN: "strain",
    NodeLabel.HUMAN_GENE: "hgene",
    NodeLabel.HUMAN_PHENOTYPE: "hpheno",
    NodeLabel.PAPER: "paper",
    NodeLabel.EVIDENCE: "ev",
    NodeLabel.CLAIM: "claim",
}


class Predicate(StrEnum):
    """Claim predicates. PRD §4.

    One predicate beyond the PRD's starting list is included deliberately:

    `SUBSUMES`. The seed GWAS (Kon et al. 2026) defines umbrella phenotype classes
    -- `YWKo` covers yellow/white/kouhaku, `kurobuchi` is declared to include
    sanshoku and kuroaka -- and runs a separate GWAS on each. Their intervals
    therefore share signal *by construction*. Without a subsumption relation the
    graph would show kurobuchi and sanshoku independently associating with the same
    chr14 locus and that would read as replication when it is an artefact of
    overlapping label sets. `resembles` cannot express it: subsumption is directed
    and much stronger than resemblance.
    """

    HAS_PHENOTYPE = "has_phenotype"
    ASSOCIATED_WITH_GENE = "associated_with_gene"
    ASSOCIATED_WITH_LOCUS = "associated_with_locus"
    CAUSED_BY_VARIANT = "caused_by_variant"
    AFFECTS_ANATOMY = "affects_anatomy"
    PARTICIPATES_IN = "participates_in"
    ORTHOLOG_OF = "ortholog_of"
    RESEMBLES = "resembles"
    CO_OCCURS_WITH = "co_occurs_with"
    MODIFIED_BY = "modified_by"
    EPISTATIC_WITH = "epistatic_with"
    PLEIOTROPIC_WITH = "pleiotropic_with"
    SUBSUMES = "subsumes"
    # PRD §8. A breeder trait and a lab mutant that *might* share a genetic
    # background. Deliberately not an alias: aliases are naming, this is a
    # biological assertion and so needs evidence like any other claim.
    PUTATIVELY_SAME_AS = "putatively_same_as"
    # PRD §10. A human phenotype attaches to a human gene, never to a medaka one.
    HUMAN_GENE_ASSOCIATED_WITH = "human_gene_associated_with"


_TRAIT_OR_PHENO = frozenset({NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.PHENOTYPE})
_GENOMIC = frozenset({NodeLabel.GENE, NodeLabel.LOCUS, NodeLabel.GENETIC_VARIANT})

#: predicate -> (allowed subject labels, allowed object labels)
PREDICATE_SHAPES: dict[Predicate, tuple[frozenset[NodeLabel], frozenset[NodeLabel]]] = {
    Predicate.HAS_PHENOTYPE: (
        frozenset({NodeLabel.ORNAMENTAL_TRAIT}),
        frozenset({NodeLabel.PHENOTYPE}),
    ),
    Predicate.ASSOCIATED_WITH_GENE: (_TRAIT_OR_PHENO, frozenset({NodeLabel.GENE})),
    Predicate.ASSOCIATED_WITH_LOCUS: (_TRAIT_OR_PHENO, frozenset({NodeLabel.LOCUS})),
    Predicate.CAUSED_BY_VARIANT: (_TRAIT_OR_PHENO, frozenset({NodeLabel.GENETIC_VARIANT})),
    Predicate.AFFECTS_ANATOMY: (
        frozenset({NodeLabel.PHENOTYPE}),
        frozenset({NodeLabel.ANATOMY}),
    ),
    Predicate.PARTICIPATES_IN: (
        frozenset({NodeLabel.GENE}),
        frozenset({NodeLabel.BIOLOGICAL_MECHANISM}),
    ),
    Predicate.ORTHOLOG_OF: (
        frozenset({NodeLabel.GENE}),
        frozenset({NodeLabel.HUMAN_GENE, NodeLabel.GENE}),
    ),
    Predicate.RESEMBLES: (_TRAIT_OR_PHENO, _TRAIT_OR_PHENO),
    Predicate.CO_OCCURS_WITH: (_TRAIT_OR_PHENO, _TRAIT_OR_PHENO),
    Predicate.MODIFIED_BY: (_TRAIT_OR_PHENO, _GENOMIC),
    Predicate.EPISTATIC_WITH: (
        frozenset({NodeLabel.GENE, NodeLabel.LOCUS}),
        frozenset({NodeLabel.GENE, NodeLabel.LOCUS}),
    ),
    Predicate.PLEIOTROPIC_WITH: (
        frozenset({NodeLabel.PHENOTYPE}),
        frozenset({NodeLabel.PHENOTYPE}),
    ),
    Predicate.SUBSUMES: (_TRAIT_OR_PHENO, _TRAIT_OR_PHENO),
    Predicate.PUTATIVELY_SAME_AS: (
        frozenset({NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.STRAIN, NodeLabel.PHENOTYPE}),
        frozenset({NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.STRAIN, NodeLabel.PHENOTYPE}),
    ),
    Predicate.HUMAN_GENE_ASSOCIATED_WITH: (
        frozenset({NodeLabel.HUMAN_GENE}),
        frozenset({NodeLabel.HUMAN_PHENOTYPE}),
    ),
}

#: Predicates whose subject and object are interchangeable. Claim ids for these are
#: canonicalised by sorting the endpoints, so `A resembles B` and `B resembles A`
#: are one claim rather than two half-evidenced ones.
SYMMETRIC_PREDICATES: frozenset[Predicate] = frozenset(
    {
        Predicate.RESEMBLES,
        Predicate.CO_OCCURS_WITH,
        Predicate.EPISTATIC_WITH,
        Predicate.PLEIOTROPIC_WITH,
        Predicate.PUTATIVELY_SAME_AS,
    }
)


class EvidenceLevel(StrEnum):
    """PRD §5, strongest first.

    `UNKNOWN` is not a failure state. PRD §5: "잘못된 확신보다 불확실성을 보존하는
    것을 우선한다."
    """

    CAUSAL_VARIANT = "CAUSAL_VARIANT"
    FUNCTIONAL_VALIDATION = "FUNCTIONAL_VALIDATION"
    FINE_MAPPING = "FINE_MAPPING"
    QTL_GWAS_ASSOCIATION = "QTL_GWAS_ASSOCIATION"
    EXPRESSION_ASSOCIATION = "EXPRESSION_ASSOCIATION"
    OBSERVATIONAL = "OBSERVATIONAL"
    BREEDER_OBSERVATION = "BREEDER_OBSERVATION"
    UNKNOWN = "UNKNOWN"


#: Sort rank; higher is stronger. `UNKNOWN` sorts below everything rather than in
#: the middle -- an unclassified finding must never outrank a classified weak one.
EVIDENCE_RANK: dict[EvidenceLevel, int] = {
    EvidenceLevel.CAUSAL_VARIANT: 70,
    EvidenceLevel.FUNCTIONAL_VALIDATION: 60,
    EvidenceLevel.FINE_MAPPING: 50,
    EvidenceLevel.QTL_GWAS_ASSOCIATION: 40,
    EvidenceLevel.EXPRESSION_ASSOCIATION: 30,
    EvidenceLevel.OBSERVATIONAL: 20,
    EvidenceLevel.BREEDER_OBSERVATION: 10,
    EvidenceLevel.UNKNOWN: 0,
}


class Stance(StrEnum):
    """How a piece of evidence bears on a claim. PRD §4, §9."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


class TraitCategory(StrEnum):
    """Top-level grouping of ornamental traits, following the seed paper's own
    sectioning of its Table 1."""

    BODY_COLOR = "BODY_COLOR"
    BODY_SHAPE = "BODY_SHAPE"
    FIN_MORPHOLOGY = "FIN_MORPHOLOGY"
    EYE_MORPHOLOGY = "EYE_MORPHOLOGY"
    SCALE = "SCALE"
    OTHER = "OTHER"


class ReviewStatus(StrEnum):
    """PRD §12. Nothing is silently accepted."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_INFO = "NEEDS_INFO"


class ReviewReason(StrEnum):
    """Why an item was routed to a human. PRD §12, one member per bullet, plus
    `UNVERIFIED_LABEL` for strings that entered the graph without provenance
    (PRD §2.4) -- the seed paper romanises every trait name, so all Japanese
    orthography is reconstruction until a native speaker signs off."""

    NEW_ORNAMENTAL_TRAIT = "NEW_ORNAMENTAL_TRAIT"
    NEW_CAUSAL_VARIANT = "NEW_CAUSAL_VARIANT"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    LOW_RESOLUTION_CONFIDENCE = "LOW_RESOLUTION_CONFIDENCE"
    BREEDER_ACADEMIC_LINK = "BREEDER_ACADEMIC_LINK"
    NEW_RELATION_TYPE_NEEDED = "NEW_RELATION_TYPE_NEEDED"
    FULLTEXT_UNAVAILABLE = "FULLTEXT_UNAVAILABLE"
    EVIDENCE_LEVEL_UNCLEAR = "EVIDENCE_LEVEL_UNCLEAR"
    UNVERIFIED_LABEL = "UNVERIFIED_LABEL"
    BROKEN_CITATION = "BROKEN_CITATION"
    NAME_COLLISION = "NAME_COLLISION"


class PaperState(StrEnum):
    """Where a paper is in the discovery pipeline.

    Persisted on the :Paper node so a scheduled run never rediscovers or
    reprocesses what it already handled, and so a failure is recorded as a state
    rather than as an absence. PRD §11; issue #1 §2.

    `INACCESSIBLE` is terminal-ish but not final: a paywalled paper may become
    open access later, so `reset-state` can move it back.
    """

    DISCOVERED = "DISCOVERED"
    METADATA_RESOLVED = "METADATA_RESOLVED"
    FULLTEXT_AVAILABLE = "FULLTEXT_AVAILABLE"
    INACCESSIBLE = "INACCESSIBLE"
    EXTRACTION_PENDING = "EXTRACTION_PENDING"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


#: States a run may pick up for the next step. Anything else is done or parked.
ACTIONABLE_PAPER_STATES: frozenset[PaperState] = frozenset(
    {
        PaperState.DISCOVERED,
        PaperState.METADATA_RESOLVED,
        PaperState.FULLTEXT_AVAILABLE,
        PaperState.EXTRACTION_PENDING,
    }
)


class CandidateStatus(StrEnum):
    """A proposal's standing. Candidates are never claims until accepted."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ResolutionStatus(StrEnum):
    """How an extracted mention mapped onto the existing ontology. Issue #1 §6.

    `AMBIGUOUS` and `NEW` both route to a human. Silently merging on a fuzzy name
    match is how an ontology acquires entities that are two things at once, and
    PRD §8 is explicit that a shared name is not evidence of shared biology.
    """

    RESOLVED_EXACT = "RESOLVED_EXACT"
    RESOLVED_ALIAS = "RESOLVED_ALIAS"
    AMBIGUOUS = "AMBIGUOUS"
    NEW = "NEW"


class VocabularyError(ValueError):
    """Raised when a claim violates the declared predicate shape."""


def validate_claim_shape(
    predicate: Predicate, subject_label: NodeLabel, object_label: NodeLabel
) -> None:
    """Reject claims outside the declared domain and range.

    This is what keeps PRD §10's warning from decaying into a comment nobody
    reads: a `HumanPhenotype` cannot be hung off a medaka `Gene`, because
    `human_gene_associated_with` accepts only a `HumanGene` subject, and no other
    predicate accepts a `HumanPhenotype` object at all.
    """
    try:
        subjects, objects = PREDICATE_SHAPES[predicate]
    except KeyError as exc:  # pragma: no cover - unreachable while Predicate is closed
        raise VocabularyError(f"predicate {predicate!r} has no declared shape") from exc

    if subject_label not in subjects:
        raise VocabularyError(
            f"{predicate.value}: subject must be one of "
            f"{sorted(s.value for s in subjects)}, got {subject_label.value}"
        )
    if object_label not in objects:
        raise VocabularyError(
            f"{predicate.value}: object must be one of "
            f"{sorted(o.value for o in objects)}, got {object_label.value}"
        )
