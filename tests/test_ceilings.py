"""The experiment-type ceiling on evidence levels. ADR 0003.

These pin the rule against the seed data and against evidence built to break it.
"""

from __future__ import annotations

import pytest

from medaka_ontology.ceilings import (
    EXPERIMENT_CEILINGS,
    KNOWN_CEILING_VIOLATIONS,
    ceiling_of,
    ceiling_violations,
)
from medaka_ontology.convergence import GeneBasis, classify
from medaka_ontology.loader import SeedValidationError, load_dir, validate
from medaka_ontology.models import Claim
from medaka_ontology.vocabulary import EvidenceLevel


@pytest.fixture(scope="module")
def bundle():
    return load_dir()


def _with_evidence(bundle, predicate="associated_with_gene", **evidence):
    obj = {"label": "Gene", "name": "zic1"}
    if predicate == "has_phenotype":
        obj = {"label": "Phenotype", "name": "dorsal-to-ventral identity transformation"}
    copy = bundle.model_copy(deep=True)
    copy.claims.append(
        Claim(
            predicate=predicate,
            subject={"label": "OrnamentalTrait", "name": "miyuki"},
            object=obj,
            evidence=[{"paper": "kon2026", "finding": "test fixture",
                       "species": "Oryzias latipes", **evidence}],
        )
    )
    return copy


def test_known_ceiling_violations_are_exactly_the_real_ones(bundle):
    """Both directions. A new breach must fail, and so must a listed one whose
    data has been fixed, so the list cannot outlive the error it records."""
    assert set(ceiling_violations(bundle)) == set(KNOWN_CEILING_VIOLATIONS)


def test_the_known_list_is_the_one_adr_0003_signed_off():
    """Eleven items, each named in ADR 0003 §Consequences. Growing this list is
    a decision, not a way to make validate pass."""
    assert len(KNOWN_CEILING_VIOLATIONS) == 11


def test_every_type_the_seed_uses_has_a_ceiling(bundle):
    assert not [why for why in ceiling_violations(bundle).values() if "no ceiling" in why]


@pytest.mark.parametrize(
    ("experiment_type", "ceiling"),
    [
        ("variant calling", EvidenceLevel.QTL_GWAS_ASSOCIATION),
        ("GWAS", EvidenceLevel.QTL_GWAS_ASSOCIATION),
        ("  Expression Analysis ", EvidenceLevel.EXPRESSION_ASSOCIATION),
        ("variant calling and genome editing", EvidenceLevel.FUNCTIONAL_VALIDATION),
        ("positional cloning and morpholino knockdown", EvidenceLevel.CAUSAL_VARIANT),
        ("positional cloning and a new assay", None),
        ("", None),
    ],
)
def test_ceiling_of(experiment_type, ceiling):
    assert ceiling_of(experiment_type) is ceiling


def test_fine_mapping_on_variant_calling_fails(bundle):
    bad = _with_evidence(bundle, experiment_type="variant calling", level="FINE_MAPPING")
    with pytest.raises(SeedValidationError, match="miyuki -> zic1: kon2026 evidence FINE_MAPPING"):
        validate(bad)


def test_expression_recorded_as_function_fails(bundle):
    bad = _with_evidence(bundle, experiment_type="expression analysis",
                         level="FUNCTIONAL_VALIDATION")
    with pytest.raises(SeedValidationError, match="ceiling EXPRESSION_ASSOCIATION"):
        validate(bad)


def test_an_unknown_experiment_type_fails(bundle):
    bad = _with_evidence(bundle, experiment_type="vibes", level="OBSERVATIONAL")
    with pytest.raises(SeedValidationError, match="'vibes' has no ceiling"):
        validate(bad)


def test_an_empty_experiment_type_fails_cleanly(bundle):
    bad = _with_evidence(bundle, experiment_type="  ", level="OBSERVATIONAL")
    with pytest.raises(SeedValidationError, match="has no experiment_type"):
        validate(bad)


def test_a_level_below_its_ceiling_passes(bundle):
    ok = _with_evidence(bundle, experiment_type="positional cloning",
                        level="FUNCTIONAL_VALIDATION")
    validate(ok)


def test_predicates_outside_adr_0003_are_not_ceiled(bundle):
    ok = _with_evidence(bundle, predicate="has_phenotype", experiment_type="vibes",
                        level="OBSERVATIONAL")
    assert not [k for k in ceiling_violations(ok) if k[1] == "miyuki"]


def test_a_compound_type_is_direct_when_any_part_is(bundle):
    """Otherwise renaming ohtsuka2004's type to name its morpholino would
    silently drop Da mutant -> zic1 out of DIRECT."""
    claim = _with_evidence(bundle, experiment_type="positional cloning and morpholino knockdown",
                           level="FUNCTIONAL_VALIDATION").claims[-1]
    assert classify(claim) is GeneBasis.DIRECT


def test_a_knockdown_alone_is_not_direct(bundle):
    claim = _with_evidence(bundle, experiment_type="morpholino knockdown",
                           level="FUNCTIONAL_VALIDATION").claims[-1]
    assert classify(claim) is GeneBasis.INFERRED


def test_a_variant_knock_in_is_direct(bundle):
    claim = _with_evidence(bundle, experiment_type="variant knock-in",
                           level="CAUSAL_VARIANT").claims[-1]
    assert classify(claim) is GeneBasis.DIRECT


def test_table_keys_are_normalised():
    assert all(k == k.strip().lower() and " and " not in k for k in EXPERIMENT_CEILINGS)
