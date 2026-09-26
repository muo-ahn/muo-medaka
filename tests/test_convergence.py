"""The convergence rule for gene claims, and the species field it rests on.

PRD §8. A single shared phenotype nominates the right gene 3 times in 12 on the
traits whose answer is known, so a gene reached by inference has to converge
before it may be recorded. These tests pin the rule against the seed data and
against claims built to break it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medaka_ontology.convergence import (
    KNOWN_VIOLATIONS,
    GeneBasis,
    GeneGraph,
    classify,
    gene_claim_violations,
    leave_one_out,
)
from medaka_ontology.lexicon import is_ambiguous
from medaka_ontology.loader import SeedValidationError, load_dir, validate
from medaka_ontology.models import Claim

REPO = Path(__file__).resolve().parents[1]
BASELINE = (
    REPO / ".claude" / "skills" / "trait-literature-search" / "scripts"
    / "validate_rule.baseline.json"
)


@pytest.fixture(scope="module")
def bundle():
    return load_dir()


def _gene_claim(bundle, trait, gene):
    for claim in bundle.claims:
        if (claim.predicate.value == "associated_with_gene"
                and claim.subject.name == trait and claim.object.name == gene):
            return claim
    raise AssertionError(f"no claim {trait} -> {gene}")


def _with_claim(bundle, trait, gene, **evidence):
    copy = bundle.model_copy(deep=True)
    copy.claims.append(
        Claim(
            predicate="associated_with_gene",
            subject={"label": "OrnamentalTrait", "name": trait},
            object={"label": "Gene", "name": gene},
            evidence=[{"paper": "kon2026", "finding": "test fixture", **evidence}],
        )
    )
    return copy


@pytest.mark.parametrize(
    ("trait", "gene"),
    [("yellow", "slc45a2"), ("albino", "tyr"), ("fused centrum", "wnt4b")],
)
def test_genes_cloned_in_medaka_are_direct(bundle, trait, gene):
    assert classify(_gene_claim(bundle, trait, gene)) is GeneBasis.DIRECT


def test_miyuki_gets_no_gene(bundle):
    """Its three nominations each arrive from one neighbour, and all three sit
    on the wrong chromosome."""
    graph = GeneGraph(bundle)
    assert "miyuki" not in graph.gene_claims
    assert not any(n.convergent for n in graph.nominate("miyuki").values())


def test_attributions_nobody_tested_are_exempt(bundle):
    for trait, gene in [("panda", "pnp4a"), ("daruma", "wnt4b"), ("albino", "oca2")]:
        assert classify(_gene_claim(bundle, trait, gene)) is GeneBasis.UNASSERTED


def test_known_violations_are_exactly_the_real_ones(bundle):
    """Both directions. A new violation must fail, and so must a listed one that
    has been fixed, so the list cannot outlive the data error it records."""
    assert set(gene_claim_violations(bundle)) == set(KNOWN_VIOLATIONS)


def test_the_known_violations_list_is_what_the_user_signed_off(bundle):
    """Empty since leucophore free -> sox5 was corrected to slc2a15b (sox5 was
    cloned from ml-3, not lf). Growing this list is a decision, not a way to make
    validate pass."""
    assert KNOWN_VIOLATIONS == frozenset()


def test_an_inferred_gene_without_convergence_fails_validation(bundle):
    bad = _with_claim(bundle, "miyuki", "zic1", experiment_type="phenotype overlap",
                      level="OBSERVATIONAL")
    with pytest.raises(SeedValidationError, match="miyuki -> zic1: inferred gene"):
        validate(bad)


def test_a_direct_gene_passes_without_convergence(bundle):
    ok = _with_claim(bundle, "miyuki", "zic1", experiment_type="positional cloning",
                     level="CAUSAL_VARIANT", species="Oryzias latipes")
    validate(ok)


def test_a_claim_resting_only_on_unknown_evidence_is_exempt(bundle):
    ok = _with_claim(bundle, "miyuki", "zic1", experiment_type="literature attribution",
                     level="UNKNOWN")
    validate(ok)


def test_strong_evidence_must_state_its_species(bundle):
    """The default is medaka, so a zebrafish knockout whose author forgot the
    field would otherwise pass as medaka functional validation."""
    bad = _with_claim(bundle, "miyuki", "zic1", experiment_type="genome editing",
                      level="FUNCTIONAL_VALIDATION")
    with pytest.raises(SeedValidationError, match="does not state its species"):
        validate(bad)


def test_zebrafish_evidence_never_makes_a_claim_direct(bundle):
    claim = _with_claim(bundle, "miyuki", "zic1", experiment_type="genome editing",
                        level="OBSERVATIONAL", species="Danio rerio").claims[-1]
    assert classify(claim) is GeneBasis.INFERRED


def test_contradicting_evidence_does_not_make_a_claim_direct(bundle):
    claim = _with_claim(bundle, "miyuki", "zic1", experiment_type="positional cloning",
                        level="CAUSAL_VARIANT", species="Oryzias latipes",
                        stance="CONTRADICTS").claims[-1]
    assert classify(claim) is GeneBasis.UNASSERTED


def test_leave_one_out_matches_the_stored_baseline(bundle):
    """Re-run `validate_rule.py --update-baseline` when a change is meant to move
    these numbers, and say why in the commit."""
    result = leave_one_out(bundle)
    assert result == json.loads(BASELINE.read_text(encoding="utf-8"))
    assert result["vetoed_correct"] == 0


def test_surname_trait_names_are_ambiguous():
    for word in ("kagami", "miyuki"):
        assert is_ambiguous(word), word
