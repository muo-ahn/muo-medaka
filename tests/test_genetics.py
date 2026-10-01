"""The cross query against published crosses. ADR 0006, spec AC-7 and AC-8.

These are the tests that say the genetic layer is worth having: if the claims in
24-claims-inheritance.yaml were wrong, or the query misread them, one of the
three published results below would not come out. The worked numbers are written
up in docs/research/cross-validation-2026-10.md.

Nothing here touches Neo4j; the model is built from the seed files.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest
from typer.testing import CliRunner

from medaka_ontology.cli import app
from medaka_ontology.genetics import (
    NO_TRAIT,
    GeneticModel,
    ModelError,
    NotPredictable,
    Sex,
    State,
)
from medaka_ontology.loader import load_dir
from medaka_ontology.models import Claim, Entity, EntityRef, Evidence, SeedBundle
from medaka_ontology.vocabulary import EvidenceLevel, NodeLabel, Predicate

F = Fraction


@pytest.fixture(scope="module")
def bundle():
    return load_dir()


@pytest.fixture(scope="module")
def model(bundle):
    return GeneticModel(bundle)


def chi_square_1_to_1(a: int, b: int) -> tuple[float, float]:
    """Chi-square of a:b against 1:1, one degree of freedom, and its P value."""
    expected = (a + b) / 2
    chi2 = ((a - expected) ** 2 + (b - expected) ** 2) / expected
    return chi2, math.erfc(math.sqrt(chi2 / 2))


# ------------------------------------------------------------ AC-8 (a) Hayasaka


def test_hd_rrii1_maintenance_cross_gives_white_daughters_and_yellow_sons(model):
    """Hayasaka et al. 2019: in the Hd-rRII1 strain 'X r X r females have a white
    body color, whereas X r Y R males have an orange-red body color'. Crossing
    the two is how the strain is kept, so every daughter must be white and every
    son orange (Kon's yellow: b/b with R expressed).

    This is the one result that needs the R allele on the Y: with R autosomal a
    X^r X^r mother and an r/R father could not make all sons orange and all
    daughters white."""
    result = model.cross("b/b r/r", "b/b r/R")
    assert result.by_sex[Sex.FEMALE] == {("white",): F(1)}
    assert result.by_sex[Sex.MALE] == {("yellow",): F(1)}
    assert result.overall == {("white",): F(1, 2), ("yellow",): F(1, 2)}
    # AC-7: the weakest claim under each prediction is reported, not hidden.
    assert result.support["yellow"].level is EvidenceLevel.OBSERVATIONAL
    assert result.support["white"].level is EvidenceLevel.OBSERVATIONAL


def test_the_same_cross_with_the_r_allele_off_the_y_would_not_reproduce_it(model):
    """The negative control for the test above: treat the locus as autosomal and
    the maintenance cross gives a different answer, so the sex-linked claim is
    doing work and the result is not an accident of the notation."""
    autosomal = _without_sex_linkage(model)
    result = autosomal.cross("b/b r/r", "b/b r/R")
    assert result.by_sex[Sex.FEMALE] != {("white",): F(1)}


def _without_sex_linkage(model: GeneticModel) -> GeneticModel:
    """The same model with every locus autosomal, for contrast."""
    clone = GeneticModel.__new__(GeneticModel)
    clone.__dict__.update(model.__dict__)
    clone.loci = {
        n: type(loc)(loc.name, dict(loc.alleles), False, list(loc.claims))
        for n, loc in model.loci.items()
    }
    return clone


# ---------------------------------------------------- AC-8 (b) Sasano Cross I


def test_sasano_cross_i_predicts_even_b_and_r_and_four_classes(model):
    """Sasano et al. 2012, Cross I, (Actb-SLa:GFP x Hd-rr) x Hd-rr: the backcross
    of an F1 female (B/b, X^R X^r) to the Hd-rr male (b/b, X^r Y^r). Half of the
    offspring should carry B and half should carry R, in each sex, and the four
    b/r classes should each be a quarter."""
    mother = model.parse("B/b R/r", Sex.FEMALE)
    father = model.parse("b/b r/r", Sex.MALE)
    for sex in Sex:
        genotypes = model.offspring(mother, father, sex)
        b_present = sum(p for g, p in genotypes.items() if "B" in g.at("slc45a2"))
        r_present = sum(p for g, p in genotypes.items() if "R" in g.at("r locus"))
        assert b_present == F(1, 2) and r_present == F(1, 2), sex
        classes = model.class_shares(mother, father, sex)
        assert classes == {
            ("white",): F(1, 4),
            ("blue",): F(1, 4),
            ("yellow",): F(1, 4),
            (NO_TRAIT,): F(1, 4),
        }


def test_sasano_table_4_fits_the_predicted_ratios_except_for_the_sex_ratio():
    """Table 4 counts the 78 F2 fish of Cross I. The model's 1:1 predictions for
    B and R are met at P > 0.05 overall and in each sex. The sex ratio, 55 males
    to 23 females, is not: 1:1 is what dmy-determined sex gives, and the b and r
    loci cannot explain a departure, because neither is linked to sex in the way
    that would matter here (r is sex-linked, but its alleles do not change sex).
    The deviation is reported, not explained away: sasano2012 says nothing about
    it, and this ontology has no claim that could."""
    observed = {
        "B allele, males": (32, 23),
        "B allele, females": (15, 8),
        "B allele, all": (47, 31),
        "R allele, males": (25, 19),
        "R allele, females": (12, 8),
        "R allele, all": (37, 27),  # 'not determined' (14 fish) left out
    }
    for name, (present, absent) in observed.items():
        chi2, p = chi_square_1_to_1(present, absent)
        assert p > 0.05, (name, chi2, p)
    chi2, p = chi_square_1_to_1(47, 31)
    assert round(chi2, 2) == 3.28 and round(p, 3) == 0.070
    chi2, p = chi_square_1_to_1(37, 27)
    assert round(chi2, 2) == 1.56 and round(p, 3) == 0.211

    chi2, p = chi_square_1_to_1(55, 23)
    assert round(chi2, 2) == 13.13
    assert p < 0.001, "the sex ratio departs from the 1:1 the model predicts"


# --------------------------------------------------- AC-8 (c) sex linkage F2


def test_sex_linkage_breaks_the_9_3_3_1_in_the_f2(model):
    """yellow female (b/b, X^R X^R) x blue male (B/B, X^r Y^r). The F1 is all
    wild type. Autosomal b and r would give 9:3:3:1 in both sexes of the F2; with
    r on the sex chromosomes the F2 females cannot be blue or white (every one
    gets an X^R from her father) and the sons split 3:3:1:1."""
    f1 = model.cross("b/b R/R", "B/B r/r")
    assert f1.overall == {(NO_TRAIT,): F(1)}

    mother = model.parse("B/b R/r", Sex.FEMALE)  # an F1 daughter
    father = model.parse("B/b R/r", Sex.MALE)  # an F1 son: X^R Y^r
    # R/r for a male is X^R Y^r: written X first.
    assert model.show(father, ["r locus"]) == "X^R Y^r"

    females = model.class_shares(mother, father, Sex.FEMALE)
    males = model.class_shares(mother, father, Sex.MALE)
    assert females == {(NO_TRAIT,): F(3, 4), ("yellow",): F(1, 4)}
    assert males == {
        (NO_TRAIT,): F(3, 8),
        ("blue",): F(3, 8),
        ("yellow",): F(1, 8),
        ("white",): F(1, 8),
    }
    assert ("blue",) not in females and ("white",) not in females

    # What autosomal inheritance would predict, for contrast: 9:3:3:1.
    autosomal = _without_sex_linkage(model)
    for sex in Sex:
        shares = autosomal.class_shares(
            autosomal.parse("B/b R/r", Sex.FEMALE), autosomal.parse("B/b R/r", Sex.MALE), sex
        )
        assert shares[(NO_TRAIT,)] == F(9, 16)
        assert shares[("blue",)] == F(3, 16)
        assert shares[("yellow",)] == F(3, 16)
        assert shares[("white",)] == F(1, 16)


# ----------------------------------------------------- epistasis and composites


def test_seethrough_is_one_sixteenth_of_a_double_heterozygote_intercross(model):
    """JMA §3.8.10: seethrough is albino with panda's missing iridophores. F1 of an
    albino (i/i) and a panda (pd/pd) is I/i pd+/pd; its intercross gives 9:3:3:1 on
    two autosomal recessives, and the double recessive is the seethrough."""
    result = model.cross("I/i pd/pd+", "I/i pd/pd+")
    assert result.overall == {
        (NO_TRAIT,): F(9, 16),
        ("albino",): F(3, 16),
        ("panda",): F(3, 16),
        ("seethrough",): F(1, 16),
    }
    # AC-7: the weakest link is the INFERRED dominance of I over i and pd+ over pd.
    assert result.support["seethrough"].level is EvidenceLevel.INFERRED


def test_albino_masks_blue_and_panda_but_the_composite_absorbs_its_parts(model):
    albino_blue = model.phenotype(model.parse("i/i B/B r/r", Sex.MALE))
    assert albino_blue.visible == ("albino",)
    assert albino_blue.masked == {"blue"}
    assert albino_blue.states["blue"] is State.EXPRESSED  # the genotype says blue

    both = model.phenotype(model.parse("i/i pd/pd", Sex.FEMALE))
    assert both.visible == ("seethrough",)
    assert both.absorbed["seethrough"] == ("albino", "panda")
    assert not both.masked, "panda is absorbed by the composite, not reported as hidden"


def test_a_dominant_trait_shows_in_the_f1(model):
    """himemedaka_rlf: RLF is 顕性; crossed to a normal-finned fish the F1 shows it."""
    result = model.cross("RLF/RLF", "rlf+/rlf+")
    assert result.overall == {("reallongfin",): F(1)}
    assert result.support["reallongfin"].level is EvidenceLevel.BREEDER_OBSERVATION


# ------------------------------------------------------------- AC-7 refusals


def test_multilocus_traits_are_refused_not_guessed(model):
    refused, none = model.unpredictable_traits()
    assert refused["orochi"] == "not predictable (multilocus, kon2026)"
    assert refused["miyuki"] == "not predictable (multilocus, kon2026)"
    assert "aurora" in none, "no inheritance data for aurora: said so, not guessed"
    with pytest.raises(NotPredictable, match="multilocus"):
        model.hypotheses(["orochi"], Sex.FEMALE)
    with pytest.raises(NotPredictable, match="no inheritance data"):
        model.hypotheses(["aurora"], Sex.FEMALE)
    result = model.cross("b/b", "b/b")
    assert "orochi" in result.unpredictable and result.no_data


def test_a_cross_from_phenotypes_reports_ranges_over_the_hypotheses(model):
    """Two parents known only by what they show. A yellow mother is b/b with R in
    at least one copy and a blue father B- with r/r, so the F1 can be anything
    from all wild type to a mix, and each class is a range."""
    result = model.cross_from_phenotypes(["yellow"], ["blue"])
    assert result.n_mother > 1 and result.n_father > 1
    lo, hi = result.overall[(NO_TRAIT,)]
    assert lo < hi and hi == 1
    assert ("white",) in result.overall, "carriers can give white"
    # Fixed strains: the single answer.
    fixed = model.cross_from_phenotypes(["yellow"], ["blue"], true_breeding=True)
    assert (fixed.n_mother, fixed.n_father) == (1, 1)
    assert fixed.overall == {(NO_TRAIT,): (F(1), F(1))}
    # A blue fish cannot be albino: the masker is part of what the hypothesis fixes.
    for g in model.hypotheses(["blue"], Sex.FEMALE):
        assert g.at("tyr") != ("i", "i"), "a homozygous albino would hide the blue"


def test_probabilities_always_sum_to_one(model):
    for mother, father in [("B/b R/r", "B/b R/r"), ("I/i pd/pd+ d/d+", "i/i pd/pd")]:
        result = model.cross(mother, father)
        assert sum(result.overall.values()) == 1
        for sex in Sex:
            assert sum(result.by_sex[sex].values()) == 1
            assert sum(result.genotypes[sex].values()) == 1


# ------------------------------------------------------------------- input


def test_bad_genotypes_say_what_is_wrong(model):
    with pytest.raises(ModelError, match="unknown allele"):
        model.parse("x/x", Sex.FEMALE)
    with pytest.raises(ModelError, match="allele of"):
        model.parse("b/r", Sex.FEMALE)
    with pytest.raises(ModelError, match="twice"):
        model.parse("b/b b/B", Sex.FEMALE)
    with pytest.raises(ModelError, match="female"):
        model.cross(model.parse("b/b", Sex.MALE), model.parse("b/b", Sex.MALE))


def test_cli_cross_runs_without_a_database():
    runner = CliRunner()
    ok = runner.invoke(app, ["cross", "--mother", "b/b r/r", "--father", "b/b r/R"])
    assert ok.exit_code == 0, ok.output
    assert "white" in ok.output and "yellow" in ok.output and "assumptions" in ok.output
    refused = runner.invoke(app, ["cross", "--mother-shows", "orochi", "--father-shows", "blue"])
    assert refused.exit_code == 1
    assert "multilocus" in refused.output
    listing = runner.invoke(app, ["cross", "--symbols"])
    assert "r locus (sex-linked)" in listing.output


# ------------------------------------------------- the data the query reads


KON_TABLE_1 = {
    # trait: (Reported loci, Hereditary mode), PMC12915790 Table 1 verbatim. All
    # other traits have both cells blank.
    "white": ("slc45a2 (Fukamachi et al. 2001), r locus (Aida 1921)", ["recessive"]),
    "blue": ("r locus (Aida 1921)", ["recessive"]),
    "yellow": ("slc45a2 (Fukamachi et al. 2001)", ["recessive"]),
    "YWKo": ("slc45a2 (Fukamachi et al. 2001)", ["recessive"]),
    "orochi": (None, ["multilocus"]),
    "miyuki": (None, ["multilocus"]),
    "panda": ("pnp4a (Kimura et al. 2017)", ["recessive"]),
    "albino": ("oca2 (Fukamachi et al. 2004)", ["recessive"]),
    "daruma": ("wnt4b (Inohaya et al. 2010)", ["incompletely dominant", "recessive"]),
    "hikari": ("zic1/4 (Moriyama et al. 2012)", ["recessive"]),
    "nodorsalfin": ("lmbr1 (Letelier et al. 2018)", ["recessive"]),
}


def test_every_kon_table_1_hereditary_mode_is_recorded_and_nothing_else_is(bundle):
    """AC-6: Table 1's eleven traits, checked against the paper's own cells. The
    reverse also holds: no other trait gets a kon2026 inheritance claim, because
    the blank cells are blank."""
    from_kon: dict[str, list[str]] = {}
    for c in bundle.claims:
        if c.predicate is Predicate.INHERITED_AS and any(e.paper == "kon2026" for e in c.evidence):
            from_kon.setdefault(c.subject.name, []).append(c.object.name)
    assert {k: sorted(v) for k, v in from_kon.items()} == {
        t: sorted(modes) for t, (_, modes) in KON_TABLE_1.items()
    }
    for c in bundle.claims:
        if c.predicate is Predicate.INHERITED_AS and c.subject.name in KON_TABLE_1:
            for e in c.evidence:
                if e.paper == "kon2026":
                    loci, _ = KON_TABLE_1[c.subject.name]
                    assert (loci in e.finding) if loci else ("no reported locus" in e.finding)
                    assert e.level is EvidenceLevel.OBSERVATIONAL


def test_inferred_evidence_cites_the_literature_and_explains_itself(bundle):
    """ADR 0006. INFERRED is ours, so it must start from a paper in the seed and
    carry the reasoning where PRD §2.3 puts it, on the claim."""
    papers = {p.key: p for p in bundle.papers}
    inferred = [c for c in bundle.claims for e in c.evidence if e.level is EvidenceLevel.INFERRED]
    assert inferred, "vacuous while nothing is inferred"
    for claim in inferred:
        for e in claim.evidence:
            if e.level is not EvidenceLevel.INFERRED:
                continue
            p = papers[e.paper]
            assert p.doi or p.pmid or p.pmcid, f"{claim.id}: INFERRED cites a non-literature source"
            assert e.experiment_type == "inference"
        assert (claim.interpretation or "").strip(), f"{claim.id}: INFERRED, no interpretation"


def test_every_locus_has_two_alleles_and_exactly_one_wild_type(model):
    for locus in model.loci.values():
        assert locus.wild.wild_type
        assert len(locus.alleles) == 2


# --------------------------------------------- partial dominance, synthetic data


def _tiny_bundle(dominance: Predicate | None) -> SeedBundle:
    """One locus L with alleles A (wild type) and a, and a trait T that needs a."""
    ev = Evidence(paper="p", experiment_type="inference", finding="f", level=EvidenceLevel.INFERRED)

    def claim(pred, sl, sn, ol, on):
        return Claim(
            predicate=pred,
            subject=EntityRef(label=sl, name=sn),
            object=EntityRef(label=ol, name=on),
            evidence=[ev],
        )

    gv, lc = NodeLabel.GENETIC_VARIANT, NodeLabel.LOCUS
    claims = [
        claim(Predicate.ALLELE_OF, gv, "L: A", lc, "L"),
        claim(Predicate.ALLELE_OF, gv, "L: a", lc, "L"),
        claim(Predicate.REQUIRES_ALLELE, NodeLabel.ORNAMENTAL_TRAIT, "T", gv, "L: a"),
    ]
    if dominance:
        claims.append(claim(dominance, gv, "L: A", gv, "L: a"))
    return SeedBundle(
        entities=[
            Entity(label=lc, name="L"),
            Entity(label=gv, name="L: A", symbol="A", variant_type="wild type"),
            Entity(label=gv, name="L: a", symbol="a"),
            Entity(label=NodeLabel.ORNAMENTAL_TRAIT, name="T"),
        ],
        claims=claims,
    )


def test_incomplete_dominance_gives_a_1_2_1_with_an_intermediate_class():
    model = GeneticModel(_tiny_bundle(Predicate.INCOMPLETELY_DOMINANT_OVER))
    result = model.cross("A/a", "A/a")
    assert result.overall == {("T",): F(1, 4), ("T (partial)",): F(1, 2), (NO_TRAIT,): F(1, 4)}


def test_a_heterozygote_with_no_dominance_edge_is_unknown_not_guessed():
    model = GeneticModel(_tiny_bundle(None))
    result = model.cross("A/a", "A/a")
    assert result.overall == {("T",): F(1, 4), ("T?",): F(1, 2), (NO_TRAIT,): F(1, 4)}
    assert model.allele_state("a", ("A", "a")) is State.UNKNOWN
