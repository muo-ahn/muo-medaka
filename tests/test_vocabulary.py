"""The vocabulary is the ontology's only guard against silent category errors,
so its refusals are tested as carefully as its acceptances."""

from __future__ import annotations

import pytest

from medaka_ontology.vocabulary import (
    ENTITY_LABELS,
    EVIDENCE_RANK,
    PREDICATE_SHAPES,
    SYMMETRIC_PREDICATES,
    EvidenceLevel,
    NodeLabel,
    Predicate,
    VocabularyError,
    validate_claim_shape,
)


def test_every_predicate_declares_a_shape():
    """A predicate with no declared shape would bypass validation entirely."""
    assert set(Predicate) == set(PREDICATE_SHAPES)


def test_declared_shapes_only_reference_claim_endpoints():
    for predicate, (subjects, objects) in PREDICATE_SHAPES.items():
        assert subjects <= ENTITY_LABELS, predicate
        assert objects <= ENTITY_LABELS, predicate


def test_symmetric_predicates_have_matching_domain_and_range():
    """If A->B is allowed but B->A is not, canonicalising the id would produce a
    claim that fails its own shape check."""
    for predicate in SYMMETRIC_PREDICATES:
        subjects, objects = PREDICATE_SHAPES[predicate]
        assert subjects == objects, predicate


def test_valid_claim_passes():
    validate_claim_shape(Predicate.ASSOCIATED_WITH_GENE, NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.GENE)


def test_human_phenotype_cannot_hang_off_a_medaka_gene():
    """PRD §10. The comparative layer must stay one hop away from medaka."""
    with pytest.raises(VocabularyError):
        validate_claim_shape(
            Predicate.HUMAN_GENE_ASSOCIATED_WITH, NodeLabel.GENE, NodeLabel.HUMAN_PHENOTYPE
        )


def test_no_predicate_accepts_a_human_phenotype_from_a_medaka_subject():
    medaka_subjects = ENTITY_LABELS - {NodeLabel.HUMAN_GENE, NodeLabel.HUMAN_PHENOTYPE}
    for predicate, (subjects, objects) in PREDICATE_SHAPES.items():
        if NodeLabel.HUMAN_PHENOTYPE in objects:
            assert not (subjects & medaka_subjects), predicate


def test_gene_cannot_have_a_phenotype_directly():
    with pytest.raises(VocabularyError):
        validate_claim_shape(Predicate.HAS_PHENOTYPE, NodeLabel.GENE, NodeLabel.PHENOTYPE)


def test_causal_variant_requires_a_variant_object():
    with pytest.raises(VocabularyError) as exc:
        validate_claim_shape(
            Predicate.CAUSED_BY_VARIANT, NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.GENE
        )
    assert "GeneticVariant" in str(exc.value)


def test_unknown_ranks_below_every_classified_level():
    """PRD §5. An unclassified finding must never outrank a classified weak one."""
    unknown = EVIDENCE_RANK[EvidenceLevel.UNKNOWN]
    others = [v for k, v in EVIDENCE_RANK.items() if k is not EvidenceLevel.UNKNOWN]
    assert unknown < min(others)


def test_every_evidence_level_is_ranked():
    assert set(EvidenceLevel) == set(EVIDENCE_RANK)


# --- the genetic layer, ADR 0006 ----------------------------------------------

GENETIC_PREDICATES = {
    Predicate.INHERITED_AS,
    Predicate.ALLELE_OF,
    Predicate.DOMINANT_OVER,
    Predicate.INCOMPLETELY_DOMINANT_OVER,
    Predicate.REQUIRES_ALLELE,
    Predicate.LINKED_TO,
    Predicate.MASKS,
    Predicate.COMPOSED_OF,
}


def test_the_genetic_predicates_are_a_closed_set_with_ceilings():
    """AC-5: each new predicate has a shape (the first test above) and a ceiling
    table, so a new experiment name cannot reach an unbounded level on it."""
    from medaka_ontology.ceilings import PREDICATE_CEILINGS

    assert GENETIC_PREDICATES <= set(Predicate)
    assert GENETIC_PREDICATES <= set(PREDICATE_CEILINGS)


def test_inferred_is_the_lowest_stated_level_and_above_unknown():
    """ADR 0006. INFERRED is ours, not a source's, so it sits below even a
    breeder's statement, and above UNKNOWN, which says nothing at all."""
    stated = [
        v
        for k, v in EVIDENCE_RANK.items()
        if k not in (EvidenceLevel.UNKNOWN, EvidenceLevel.INFERRED)
    ]
    assert (
        EVIDENCE_RANK[EvidenceLevel.UNKNOWN] < EVIDENCE_RANK[EvidenceLevel.INFERRED] < min(stated)
    )


def test_allele_dominance_is_between_alleles_and_masking_between_traits():
    validate_claim_shape(
        Predicate.DOMINANT_OVER, NodeLabel.GENETIC_VARIANT, NodeLabel.GENETIC_VARIANT
    )
    validate_claim_shape(Predicate.MASKS, NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.ORNAMENTAL_TRAIT)
    with pytest.raises(VocabularyError):
        validate_claim_shape(Predicate.DOMINANT_OVER, NodeLabel.GENE, NodeLabel.GENE)
    with pytest.raises(VocabularyError):
        validate_claim_shape(Predicate.REQUIRES_ALLELE, NodeLabel.GENE, NodeLabel.GENETIC_VARIANT)


def test_linked_to_is_symmetric_and_inheritance_modes_are_a_node_label():
    assert Predicate.LINKED_TO in SYMMETRIC_PREDICATES
    assert NodeLabel.INHERITANCE_MODE in ENTITY_LABELS
    validate_claim_shape(
        Predicate.INHERITED_AS, NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.INHERITANCE_MODE
    )


def test_inheritance_mode_entities_are_exactly_the_closed_set():
    from medaka_ontology.loader import load_dir
    from medaka_ontology.vocabulary import InheritanceModeName

    modes = {e.name for e in load_dir().entities if e.label is NodeLabel.INHERITANCE_MODE}
    assert modes == {m.value for m in InheritanceModeName}
