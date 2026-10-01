"""Model-level invariants: deterministic ids, required provenance, and the
evidence/interpretation split the PRD insists on."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from medaka_ontology.models import (
    Claim,
    Entity,
    EntityRef,
    Evidence,
    Paper,
    claim_id,
    entity_id,
    slugify,
)
from medaka_ontology.vocabulary import (
    EvidenceLevel,
    NodeLabel,
    Predicate,
    ReviewReason,
    Stance,
)


def _ev(**kw) -> Evidence:
    base = dict(paper="kon2026", experiment_type="GWAS", finding="a finding")
    return Evidence(**{**base, **kw})


def _claim(**kw) -> Claim:
    base = dict(
        predicate=Predicate.ASSOCIATED_WITH_GENE,
        subject=EntityRef(label=NodeLabel.ORNAMENTAL_TRAIT, name="orochi"),
        object=EntityRef(label=NodeLabel.GENE, name="adcy5"),
        evidence=[_ev()],
    )
    return Claim(**{**base, **kw})


# --- ids --------------------------------------------------------------------


def test_entity_id_is_stable_across_case_and_spacing():
    assert entity_id(NodeLabel.GENE, "adcy5") == entity_id(NodeLabel.GENE, "ADCY5")
    assert entity_id(NodeLabel.LOCUS, "orochi chr21 interval") == entity_id(
        NodeLabel.LOCUS, "Orochi  chr21   interval"
    )


def test_entity_id_separates_labels():
    assert entity_id(NodeLabel.GENE, "adcy5") != entity_id(NodeLabel.HUMAN_GENE, "adcy5")


def test_slugify_never_returns_empty_for_non_ascii():
    """Japanese labels must not all collapse onto one id."""
    a, b = slugify("ヒカリ"), slugify("ダルマ")
    assert a and b and a != b


def test_symmetric_claim_id_is_direction_independent():
    a = claim_id(Predicate.RESEMBLES, "trait:hirenaga", "trait:swallow")
    b = claim_id(Predicate.RESEMBLES, "trait:swallow", "trait:hirenaga")
    assert a == b


def test_asymmetric_claim_id_is_direction_dependent():
    a = claim_id(Predicate.SUBSUMES, "trait:ywko", "trait:yellow")
    b = claim_id(Predicate.SUBSUMES, "trait:yellow", "trait:ywko")
    assert a != b


def test_paper_id_prefers_doi_so_two_handles_cannot_split_a_paper():
    one = Paper(key="kon2026", title="t", doi="10.1093/molbev/msag021")
    two = Paper(key="kon_2026_mbe", title="t", doi="10.1093/MOLBEV/MSAG021")
    assert one.id == two.id


# --- provenance -------------------------------------------------------------


def test_paper_without_any_identifier_is_rejected():
    with pytest.raises(ValidationError):
        Paper(key="mystery", title="untraceable")


def test_claim_without_evidence_is_rejected():
    """PRD §2.2: an association is not a fact until it carries a source."""
    with pytest.raises(ValidationError):
        _claim(evidence=[])


def test_gene_without_species_is_rejected():
    with pytest.raises(ValidationError):
        Entity(label=NodeLabel.GENE, name="kcnk5b")


def test_alias_and_unverified_label_cannot_overlap():
    with pytest.raises(ValidationError):
        Entity(
            label=NodeLabel.ORNAMENTAL_TRAIT,
            name="hikari",
            aliases=["Da"],
            unverified_labels=["Da"],
        )


def test_p_value_written_bare_in_yaml_is_kept_as_text():
    entity = Entity(label=NodeLabel.LOCUS, name="x", best_p_value=6.28e-25)
    assert isinstance(entity.best_p_value, str)
    assert "e-25" in entity.best_p_value.lower()


# --- contradiction handling, PRD §9 -----------------------------------------


def test_claim_with_both_stances_is_disputed():
    claim = _claim(
        evidence=[
            _ev(stance=Stance.SUPPORTS),
            _ev(finding="a contrary finding", stance=Stance.CONTRADICTS),
        ]
    )
    assert claim.is_disputed


def test_disputed_claim_is_flagged_for_review_without_being_told():
    claim = _claim(
        evidence=[
            _ev(stance=Stance.SUPPORTS, level=EvidenceLevel.QTL_GWAS_ASSOCIATION),
            _ev(finding="contrary", stance=Stance.CONTRADICTS, level=EvidenceLevel.OBSERVATIONAL),
        ]
    )
    assert ReviewReason.CONTRADICTORY_EVIDENCE in claim.derived_review_reasons()


def test_causal_variant_claims_always_reach_a_human():
    """PRD §12 lists new causal variant assertions as review-triggering."""
    claim = _claim(
        predicate=Predicate.CAUSED_BY_VARIANT,
        object=EntityRef(label=NodeLabel.GENETIC_VARIANT, name="adcy5 exon8 56-bp deletion"),
        evidence=[_ev(level=EvidenceLevel.CAUSAL_VARIANT)],
    )
    assert ReviewReason.NEW_CAUSAL_VARIANT in claim.derived_review_reasons()


def test_unknown_level_evidence_flags_the_claim():
    claim = _claim(evidence=[_ev(level=EvidenceLevel.UNKNOWN)])
    assert ReviewReason.EVIDENCE_LEVEL_UNCLEAR in claim.derived_review_reasons()


def test_strongest_support_ignores_contradicting_evidence():
    claim = _claim(
        evidence=[
            _ev(stance=Stance.SUPPORTS, level=EvidenceLevel.OBSERVATIONAL),
            _ev(
                finding="strong but contrary",
                stance=Stance.CONTRADICTS,
                level=EvidenceLevel.CAUSAL_VARIANT,
            ),
        ]
    )
    assert claim.strongest_support is EvidenceLevel.OBSERVATIONAL


def test_claim_with_only_contradicting_evidence_has_no_support():
    claim = _claim(evidence=[_ev(stance=Stance.CONTRADICTS)])
    assert claim.strongest_support is EvidenceLevel.UNKNOWN
    assert not claim.is_disputed


def test_evidence_id_is_shared_across_claims_it_bears_on():
    """One finding, one node -- otherwise 'what did this paper contribute?'
    cannot be answered."""
    ev = _ev()
    assert ev.id_for("paper:doi:x") == _ev().id_for("paper:doi:x")
    assert ev.id_for("paper:doi:x") != ev.id_for("paper:doi:y")


# --- labels, ADR 0005 ---------------------------------------------------------


def _label(**kw):
    from medaka_ontology.models import Label

    return Label(**{"text": "オロチ", "lang": "ja", "vocab": ["bv:0137"], **kw})


def test_a_label_names_its_language_and_a_source():
    with pytest.raises(ValidationError, match="BCP 47"):
        _label(lang="Japanese")
    with pytest.raises(ValidationError, match="bv:0001"):
        _label(vocab=["137"])
    with pytest.raises(ValidationError, match="ATTESTED but names no source"):
        _label(vocab=[])
    assert _label(vocab=[], status="UNVERIFIED").status.value == "UNVERIFIED"
    for tag in ("ja", "ja-Latn", "ko", "en", "zh-Hant"):
        assert _label(lang=tag).lang == tag


def test_names_are_derived_from_labels_and_unverified_ones_are_kept_apart():
    entity = Entity(
        label=NodeLabel.ORNAMENTAL_TRAIT,
        name="x",
        labels=[
            _label(kind="PREFERRED"),
            _label(text="orochi-jp", lang="ja-Latn", kind="ROMANIZATION"),
            _label(text="大蛇", vocab=[], status="UNVERIFIED"),
        ],
    )
    assert entity.japanese_name == "オロチ"
    assert entity.aliases == ["orochi-jp"]
    assert entity.unverified_labels == ["大蛇"]


def test_an_unverified_preferred_label_does_not_become_the_japanese_name():
    entity = Entity(
        label=NodeLabel.ORNAMENTAL_TRAIT,
        name="x",
        labels=[_label(kind="PREFERRED", vocab=[], status="UNVERIFIED")],
    )
    assert entity.japanese_name is None
    assert entity.unverified_labels == ["オロチ"]


def test_labels_cannot_be_written_beside_the_fields_they_replace():
    with pytest.raises(ValidationError, match="labels"):
        Entity(
            label=NodeLabel.ORNAMENTAL_TRAIT, name="x", japanese_name="オロチ", labels=[_label()]
        )


def test_two_preferred_labels_in_one_language_are_refused_but_two_languages_are_not():
    with pytest.raises(ValidationError, match="PREFERRED"):
        Entity(
            label=NodeLabel.ORNAMENTAL_TRAIT,
            name="x",
            labels=[_label(kind="PREFERRED"), _label(text="別名", kind="PREFERRED")],
        )
    Entity(
        label=NodeLabel.ORNAMENTAL_TRAIT,
        name="x",
        labels=[_label(kind="PREFERRED"), _label(text="오로치", lang="ko", kind="PREFERRED")],
    )


def test_deriving_names_is_idempotent_when_a_validated_entity_is_revalidated():
    """Pydantic re-runs after-validators when an Entity instance is placed in a
    SeedBundle. The first version of the fold read its own output as a
    hand-written japanese_name and refused every entity with a label."""
    from medaka_ontology.models import SeedBundle

    entity = Entity(label=NodeLabel.ORNAMENTAL_TRAIT, name="x", labels=[_label(kind="PREFERRED")])
    bundle = SeedBundle(entities=[entity])
    assert bundle.entities[0].japanese_name == "オロチ"
