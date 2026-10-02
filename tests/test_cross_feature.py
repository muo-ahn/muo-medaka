"""The cross query as a feature: input contract, output contract, display rules and
refusals. ADR 0007, spec AC-1..AC-7.

tests/test_genetics.py keeps the published-cross reproductions (Hayasaka 2019,
Sasano 2012, the sex-linked F2) and the numbers in
docs/research/cross-validation-2026-10.md. This file pins what a user of the
command can rely on: what input it accepts and rejects, the shape of the JSON,
what is always printed, and what it will not predict.

No Neo4j: the model is built from the seed files or from a small synthetic bundle.
"""

from __future__ import annotations

import json
from fractions import Fraction

import pytest
from typer.testing import CliRunner

from medaka_ontology.cli import app
from medaka_ontology.genetics import (
    NO_TRAIT,
    OPEN_DECISIONS,
    REFUSALS,
    SCHEMA_VERSION,
    Assumption,
    GeneticModel,
    InputError,
    LinkedLoci,
    ModelError,
    NotPredictable,
    Sex,
    cross_to_json,
    error_to_json,
    format_cross,
    format_range,
    range_to_json,
    weak_basis,
)
from medaka_ontology.loader import load_dir
from medaka_ontology.models import Claim, Entity, EntityRef, Evidence, SeedBundle
from medaka_ontology.vocabulary import EvidenceLevel, NodeLabel, Predicate, Stance

F = Fraction
runner = CliRunner()


@pytest.fixture(scope="module")
def model():
    return GeneticModel(load_dir())


def cli_json(*args: str) -> tuple[int, dict]:
    result = runner.invoke(app, ["cross", *args, "--json"])
    return result.exit_code, json.loads(result.output)


# ----------------------------------------------------- synthetic seeds for refusals


def _claim(pred, sl, sn, ol, on, *stances: Stance, level=EvidenceLevel.INFERRED) -> Claim:
    evidence = [
        Evidence(
            paper=f"p{i}", experiment_type="inference", finding="f", level=level, stance=stance
        )
        for i, stance in enumerate(stances or (Stance.SUPPORTS,))
    ]
    return Claim(
        predicate=pred,
        subject=EntityRef(label=sl, name=sn),
        object=EntityRef(label=ol, name=on),
        evidence=evidence,
    )


def _bundle(
    *,
    linked: bool = False,
    disputed_dominance: bool = False,
    disputed_requires: bool = False,
    dominance: bool = True,
) -> SeedBundle:
    """Two loci, L1 (A wild type, a) and L2 (B wild type, b); trait T1 needs a, T2 needs b.

    `linked` joins the loci with a `linked_to` claim and no recombination fraction;
    `disputed_*` adds a contradicting item to that claim."""
    gv, lc, ot = NodeLabel.GENETIC_VARIANT, NodeLabel.LOCUS, NodeLabel.ORNAMENTAL_TRAIT
    entities = [Entity(label=ot, name="T1"), Entity(label=ot, name="T2")]
    claims = []
    for locus, wild, mut, trait in (("L1", "A", "a", "T1"), ("L2", "B", "b", "T2")):
        entities += [
            Entity(label=lc, name=locus),
            Entity(label=gv, name=f"{locus}: {wild}", symbol=wild, variant_type="wild type"),
            Entity(label=gv, name=f"{locus}: {mut}", symbol=mut),
        ]
        claims += [
            _claim(Predicate.ALLELE_OF, gv, f"{locus}: {wild}", lc, locus),
            _claim(Predicate.ALLELE_OF, gv, f"{locus}: {mut}", lc, locus),
        ]
        requires = [Stance.SUPPORTS] + ([Stance.CONTRADICTS] if disputed_requires else [])
        claims.append(
            _claim(Predicate.REQUIRES_ALLELE, ot, trait, gv, f"{locus}: {mut}", *requires)
        )
        if dominance:
            stances = [Stance.SUPPORTS] + ([Stance.CONTRADICTS] if disputed_dominance else [])
            claims.append(
                _claim(
                    Predicate.DOMINANT_OVER, gv, f"{locus}: {wild}", gv, f"{locus}: {mut}", *stances
                )
            )
    if linked:
        claims.append(_claim(Predicate.LINKED_TO, lc, "L1", lc, "L2"))
    return SeedBundle(entities=entities, claims=claims)


# ------------------------------------------------------------------- AC-1 input


def test_every_input_error_is_an_input_error_with_the_fix_in_the_message(model):
    cases = [
        ("x/x", "unknown allele 'x'"),
        ("b/r", "allele of"),
        ("b/b b/B", "given twice"),
        ("b", "write each locus as two alleles"),
        ("b/b/b", "write each locus as two alleles"),
        ("r", "sex-linked"),
    ]
    for text, fragment in cases:
        with pytest.raises(InputError, match=fragment):
            model.parse(text, Sex.FEMALE)


def test_unknown_symbol_lists_the_symbols_that_exist(model):
    with pytest.raises(InputError) as exc:
        model.parse("q/q", Sex.MALE)
    for symbol in ("B", "b", "R", "r", "I", "i"):
        assert symbol in str(exc.value)


def test_a_male_at_the_sex_linked_locus_is_written_x_first_and_that_order_matters(model):
    """`r/R` is X^r Y^R, `R/r` is X^R Y^r. The same two alleles in the other order
    are a different father and give different sons."""
    xr_yR = model.parse("r/R", Sex.MALE)
    xR_yr = model.parse("R/r", Sex.MALE)
    assert model.show(xr_yR, ["r locus"]) == "X^r Y^R"
    assert model.show(xR_yr, ["r locus"]) == "X^R Y^r"
    assert xr_yR != xR_yr
    mother = model.parse("r/r", Sex.FEMALE)
    sons_a = model.class_shares(mother, xr_yR, Sex.MALE)
    sons_b = model.class_shares(mother, xR_yr, Sex.MALE)
    assert sons_a != sons_b
    # A female's order carries no meaning: R/r and r/R are one genotype.
    assert model.parse("R/r", Sex.FEMALE) == model.parse("r/R", Sex.FEMALE)


def test_loci_not_given_are_wild_type_and_the_wild_type_allele_is_listed(model):
    g = model.parse("i/i", Sex.FEMALE)
    for name, locus in model.loci.items():
        if name != "tyr":
            assert g.at(name) == (locus.wild.symbol,) * 2
    listing = runner.invoke(app, ["cross", "--symbols"]).output
    for locus in model.loci.values():
        assert f"{locus.wild.symbol} [wild type]" in listing
    assert "traits for --*-shows:" in listing and "yellow" in listing
    assert "orochi" not in listing.split("traits for --*-shows:")[1]


def test_the_parents_must_be_a_female_then_a_male(model):
    with pytest.raises(InputError, match="female"):
        model.cross(model.parse("b/b", Sex.MALE), model.parse("b/b", Sex.MALE))
    with pytest.raises(InputError, match="female"):
        model.cross(model.parse("b/b", Sex.FEMALE), model.parse("b/b", Sex.FEMALE))


def test_phenotype_input_rejects_unknown_empty_and_impossible_traits(model):
    with pytest.raises(InputError, match="unknown trait 'yelow'.*yellow"):
        model.hypotheses(["yelow"], Sex.FEMALE)
    with pytest.raises(InputError, match="at least one trait"):
        model.hypotheses([], Sex.FEMALE)
    # White needs b/b with no R; yellow needs b/b with R: no fish shows both.
    with pytest.raises(InputError, match="no genotype shows exactly"):
        model.hypotheses(["white", "yellow"], Sex.FEMALE)
    with pytest.raises(InputError, match="homozygous"):
        # A fixed strain cannot be a carrier: albino alone needs i/i, but blue
        # alone is only reachable as B/B or B/b, and none is both blue and albino.
        model.hypotheses(["blue", "albino"], Sex.FEMALE, true_breeding=True)


def test_cli_rejects_bad_option_combinations_with_exit_1():
    bad = [
        ["--mother", "b/b"],
        ["--mother", "b/b", "--father", "b/b", "--mother-shows", "white"],
        ["--mother", "b/b", "--father", "b/b", "--true-breeding"],
        ["--mother-shows", "white"],
        [],
    ]
    for args in bad:
        out = runner.invoke(app, ["cross", *args])
        assert out.exit_code == 1, args
    for args in bad:
        code, doc = cli_json(*args)
        assert code == 1 and doc["error"]["code"] == "invalid_input", args


# ---------------------------------------------------------------- AC-2 JSON shape


TOP_LEVEL = [
    "schema_version",
    "kind",
    "loci_in_play",
    "parents",
    "offspring",
    "evidence",
    "inferred_steps",
    "assumptions",
    "not_predictable",
    "warnings",
]
CLASS_KEYS = ["label", "traits", "probability", "hidden"]
TRAIT_KEYS = ["trait", "state", "weakest_level", "weak_basis"]
EVIDENCE_KEYS = ["trait", "weakest_level", "weakest_claim", "weak_basis", "claims_used"]
CLAIM_KEYS = ["id", "statement", "level", "papers", "disputed"]
ASSUMPTION_KEYS = ["id", "text", "open_decision"]
REFUSAL_KEYS = ["trait", "code", "reason"]
OPEN_IDS = ["strain_scope", "source_authority", "r_sex_recombination", "albino_allele"]


def _check_shape(doc: dict, *, kind: str) -> None:
    assert list(doc) == TOP_LEVEL if kind == "genotype_cross" else True
    assert doc["schema_version"] == SCHEMA_VERSION == 1
    assert doc["kind"] == kind
    for name in ("female", "male", "overall"):
        for cls in doc["offspring"][name]["classes"]:
            assert list(cls) == CLASS_KEYS
            for trait in cls["traits"]:
                assert list(trait) == TRAIT_KEYS
                assert trait["state"] in {"expressed", "partial", "unresolved"}
    for ev in doc["evidence"]:
        assert list(ev) == EVIDENCE_KEYS
        assert ev["claims_used"], "a prediction lists the claims it used"
        for claim in ev["claims_used"]:
            assert list(claim) == CLAIM_KEYS
        levels = [c["level"] for c in ev["claims_used"]]
        assert ev["weakest_level"] in levels, "the weakest level is one of the claims used"
    for a in doc["assumptions"]:
        assert list(a) == ASSUMPTION_KEYS
    for r in doc["not_predictable"]:
        assert list(r) == REFUSAL_KEYS
        assert r["code"] in REFUSALS


def test_json_contract_of_a_genotype_cross_is_pinned(model):
    """Hd-rRII1 maintenance cross: every key, its order, and the exact values a
    consumer parses. Changing any of it is a schema_version bump (ADR 0007)."""
    code, doc = cli_json("--mother", "b/b r/r", "--father", "b/b r/R")
    assert code == 0
    _check_shape(doc, kind="genotype_cross")
    assert doc["loci_in_play"] == ["r locus", "slc45a2"]
    assert doc["parents"] == {
        "mother": {
            "genotype": "X^r X^r b/b",
            "alleles": {"r locus": ["r", "r"], "slc45a2": ["b", "b"]},
        },
        "father": {
            "genotype": "X^r Y^R b/b",
            "alleles": {"r locus": ["r", "R"], "slc45a2": ["b", "b"]},
        },
    }
    female = doc["offspring"]["female"]["classes"]
    male = doc["offspring"]["male"]["classes"]
    overall = doc["offspring"]["overall"]["classes"]
    assert [(c["label"], c["probability"]) for c in female] == [("white", "1/1")]
    assert [(c["label"], c["probability"]) for c in male] == [("yellow", "1/1")]
    assert [(c["label"], c["probability"]) for c in overall] == [
        ("white", "1/2"),
        ("yellow", "1/2"),
    ]
    assert female[0]["traits"] == [
        {
            "trait": "white",
            "state": "expressed",
            "weakest_level": "OBSERVATIONAL",
            "weak_basis": False,
        }
    ]
    assert doc["offspring"]["genotypes"] == {
        "female": [{"genotype": "X^r X^r b/b", "probability": "1/1"}],
        "male": [{"genotype": "X^r Y^R b/b", "probability": "1/1"}],
    }
    assert [e["trait"] for e in doc["evidence"]] == ["white", "yellow"]
    assert doc["evidence"][0]["weakest_claim"] == "requires_allele white -> b locus: b"
    assert [a["id"] for a in doc["assumptions"]] == [
        "sex_ratio",
        "independent_assortment",
        "wild_type_default",
        *OPEN_IDS,
    ]
    assert doc["warnings"] == []
    # What the command prints is exactly what the library function returns.
    assert doc == json.loads(json.dumps(cross_to_json(model.cross("b/b r/r", "b/b r/R"))))


def test_json_contract_of_a_phenotype_cross_is_pinned(model):
    code, doc = cli_json("--mother-shows", "yellow", "--father-shows", "blue", "--true-breeding")
    assert code == 0
    _check_shape(doc, kind="phenotype_cross")
    assert list(doc) == [
        "schema_version",
        "kind",
        "true_breeding",
        "parents",
        "offspring",
        "evidence",
        "inferred_steps",
        "assumptions",
        "not_predictable",
        "warnings",
    ]
    assert doc["true_breeding"] is True
    assert doc["parents"]["mother"] == {
        "shows": ["yellow"],
        "hypothesis_count": 1,
        "hypotheses": ["b/b"],  # R/R is wild type, and wild-type loci are not printed
    }
    assert doc["parents"]["father"]["shows"] == ["blue"]
    assert doc["parents"]["father"]["hypothesis_count"] == 1
    overall = doc["offspring"]["overall"]["classes"]
    assert [(c["label"], c["probability"]) for c in overall] == [
        (NO_TRAIT, {"min": "1/1", "max": "1/1"})
    ]
    ranged = model.cross_from_phenotypes(["yellow"], ["blue"], true_breeding=True)
    assert doc == json.loads(json.dumps(range_to_json(ranged)))


def test_a_refusal_is_json_too_with_a_stable_code(model):
    code, doc = cli_json("--mother-shows", "orochi", "--father-shows", "blue")
    assert code == 1
    assert doc == {
        "schema_version": 1,
        "error": {"code": "not_predictable", "message": doc["error"]["message"]},
    }
    assert "multilocus" in doc["error"]["message"]
    assert error_to_json(NotPredictable("x"))["error"]["code"] == "not_predictable"
    assert error_to_json(InputError("x"))["error"]["code"] == "invalid_input"
    linked = error_to_json(LinkedLoci("x"))
    assert linked["error"]["code"] == "linked_loci_no_recombination_fraction"
    assert error_to_json(ModelError("x"))["error"]["code"] == "seed_inconsistent"


def test_exact_fractions_per_sex_and_overall_in_the_sex_linked_f2(model):
    _, doc = cli_json("--mother", "B/b R/r", "--father", "B/b R/r")
    shares = {
        sex: {c["label"]: c["probability"] for c in doc["offspring"][sex]["classes"]}
        for sex in ("female", "male", "overall")
    }
    assert shares["female"] == {NO_TRAIT: "3/4", "yellow": "1/4"}
    assert shares["male"] == {NO_TRAIT: "3/8", "blue": "3/8", "yellow": "1/8", "white": "1/8"}
    assert shares["overall"] == {
        NO_TRAIT: "9/16",
        "blue": "3/16",
        "yellow": "3/16",
        "white": "1/16",
    }
    assert "independent_assortment" in [a["id"] for a in doc["assumptions"]]


def test_masked_traits_are_reported_with_the_masker_and_how_much_of_the_class(model):
    """An albino hides blue. i/i x I/i, B/b x B/b, r/r x r/r: of the offspring, 3/8
    show albino only (the i/i fish with B, every one of which would have been blue)
    and 3/8 are blue; the albinos that are b/b show white beside albino."""
    args = ("--mother", "i/i B/b r/r", "--father", "I/i B/b r/r")
    _, doc = cli_json(*args)
    overall = {c["label"]: c for c in doc["offspring"]["overall"]["classes"]}
    assert overall["albino"]["probability"] == "3/8"
    assert overall["albino"]["hidden"] == [{"trait": "blue", "hidden_by": ["albino"]}]
    assert overall["blue"]["probability"] == "3/8" and overall["blue"]["hidden"] == []
    female = {c["label"]: c for c in doc["offspring"]["female"]["classes"]}
    assert female["albino"]["hidden"] == [
        {"trait": "blue", "hidden_by": ["albino"], "fraction_of_class": "1/1"}
    ]
    text = runner.invoke(app, ["cross", *args]).output
    assert "hides blue (masked by albino) in all of it" in text


def test_a_class_that_hides_a_trait_in_only_part_of_it_says_how_much(model):
    """Males of i/i B/b R/r x I/i B/b r/r: the albino-only class is B-carrying fish,
    and only those that are also r/r (half of them) would have shown blue."""
    _, doc = cli_json("--mother", "i/i B/b R/r", "--father", "I/i B/b r/r")
    male = {c["label"]: c for c in doc["offspring"]["male"]["classes"]}
    assert male["albino"]["probability"] == "3/8"
    assert male["albino"]["hidden"] == [
        {"trait": "blue", "hidden_by": ["albino"], "fraction_of_class": "1/2"}
    ]


def test_composite_strains_are_reported_as_such(model):
    _, doc = cli_json("--mother", "I/i pd/pd+", "--father", "I/i pd/pd+")
    overall = {c["label"]: c for c in doc["offspring"]["overall"]["classes"]}
    assert overall["seethrough"]["probability"] == "1/16"
    assert [t["trait"] for t in overall["seethrough"]["traits"]] == ["seethrough"]
    # The parts are absorbed, not reported as hidden.
    assert overall["seethrough"]["hidden"] == []
    assert "albino" in {c["label"] for c in doc["offspring"]["overall"]["classes"]}


def test_the_range_output_names_the_genotype_hypotheses_and_bounds_every_class(model):
    code, doc = cli_json("--mother-shows", "yellow", "--father-shows", "blue")
    assert code == 0
    mother = doc["parents"]["mother"]
    assert mother["hypothesis_count"] == len(mother["hypotheses"]) > 1
    assert "b/b" in mother["hypotheses"] and "X^R X^r b/b" in mother["hypotheses"]
    for sex in ("female", "male", "overall"):
        classes = doc["offspring"][sex]["classes"]
        lows = [Fraction(c["probability"]["min"]) for c in classes]
        highs = [Fraction(c["probability"]["max"]) for c in classes]
        assert all(lo <= hi for lo, hi in zip(lows, highs, strict=True))
        # Each hypothesis cross sums to 1, so the bounds must straddle 1.
        assert sum(lows) <= 1 <= sum(highs)
    classes = {c["label"]: c for c in doc["offspring"]["overall"]["classes"]}
    assert Fraction(classes[NO_TRAIT]["probability"]["max"]) == 1
    assert Fraction(classes["white"]["probability"]["min"]) == 0


def test_the_range_output_reports_what_an_albino_class_may_hide(model):
    """Two blue parents may both carry i: their albino sons hide the blue they would
    have shown."""
    _, doc = cli_json("--mother-shows", "blue", "--father-shows", "blue")
    classes = {c["label"]: c for c in doc["offspring"]["male"]["classes"]}
    assert classes["albino"]["hidden"] == [{"trait": "blue", "hidden_by": ["albino"]}]


def test_a_fixed_strain_input_narrows_the_range_to_one_cross(model):
    wide = model.cross_from_phenotypes(["yellow"], ["blue"])
    fixed = model.cross_from_phenotypes(["yellow"], ["blue"], true_breeding=True)
    assert wide.n_mother * wide.n_father > 1
    assert (fixed.n_mother, fixed.n_father) == (1, 1)
    assert fixed.mother_hypotheses == ["b/b"]


# --------------------------------------------------------------- AC-3 display rules


def test_weak_basis_is_marked_next_to_the_trait_not_only_in_the_evidence_section(model):
    text = format_cross(model.cross("I/i pd/pd+", "I/i pd/pd+"))
    assert "seethrough [INFERRED]" in text and "albino [INFERRED]" in text
    assert "! seethrough: INFERRED" in text
    assert "a conclusion this project drew" in text
    doc = cross_to_json(model.cross("I/i pd/pd+", "I/i pd/pd+"))
    for cls in doc["offspring"]["overall"]["classes"]:
        for trait in cls["traits"]:
            assert trait["weak_basis"] is True
    assert {w["code"] for w in doc["warnings"]} == {"weak_basis"}


def test_a_stated_level_is_not_marked_and_a_trade_level_is(model):
    plain = format_cross(model.cross("b/b r/r", "b/b r/R"))
    assert "white [" not in plain and "yellow [" not in plain
    trade = format_cross(model.cross("RLF/RLF", "rlf+/rlf+"))
    assert "reallongfin [BREEDER_OBSERVATION]" in trade
    assert "trade or breeder description only" in trade
    assert not weak_basis(EvidenceLevel.OBSERVATIONAL)
    for level in (EvidenceLevel.BREEDER_OBSERVATION, EvidenceLevel.INFERRED, EvidenceLevel.UNKNOWN):
        assert weak_basis(level)


def _masks_claims(support):
    return [c for c in support.used if c.predicate is Predicate.MASKS]


@pytest.mark.parametrize(
    ("mother", "father"),
    [("b/b r/r", "b/b r/R"), ("B/b R/r", "B/b R/r"), ("B/B r/r", "B/B r/r")],
)
def test_a_masks_claim_is_not_blue_s_basis_when_no_class_hides_blue(model, mother, father):
    """R-78. No i allele in the cross, so nothing can be albino and nothing hides blue:
    the `masks albino -> blue` trade description is not a claim blue rests on."""
    result = model.cross(mother, father)
    assert all(not victims for by_class in result.hidden.values() for victims in by_class.values())
    for support in result.support.values():
        assert not _masks_claims(support)
    if "blue" in result.support:
        assert result.support["blue"].level is EvidenceLevel.OBSERVATIONAL
        assert "blue [" not in format_cross(result)
        evidence = {e["trait"]: e for e in cross_to_json(result)["evidence"]}["blue"]
        assert evidence["weak_basis"] is False
        assert "masks" not in " ".join(c["statement"] for c in evidence["claims_used"])


def test_a_masks_claim_is_blue_s_basis_when_a_class_hides_blue(model):
    """R-78. i/i x I/i hides blue in the albino class: the masks claim is used and it
    is the weakest link, so blue is a weak basis."""
    result = model.cross("i/i B/b r/r", "I/i B/b r/r")
    assert any(
        "blue" in victims for by_class in result.hidden.values() for victims in by_class.values()
    )
    blue = result.support["blue"]
    assert [c.subject.name for c in _masks_claims(blue)] == ["albino"]
    assert blue.level is EvidenceLevel.BREEDER_OBSERVATION
    assert "blue [BREEDER_OBSERVATION]" in format_cross(result)
    evidence = {e["trait"]: e for e in cross_to_json(result)["evidence"]}["blue"]
    assert evidence["weak_basis"] is True
    assert any("masks albino" in c["statement"] for c in evidence["claims_used"])


def test_a_range_result_counts_the_masks_claim_when_any_hypothesis_hides_blue(model):
    """R-78. A yellow x blue range includes i/i hypotheses that hide blue."""
    result = model.cross_from_phenotypes(["yellow"], ["blue"])
    assert _masks_claims(result.support["blue"])
    assert result.support["blue"].level is EvidenceLevel.BREEDER_OBSERVATION


def test_every_inferred_claim_a_prediction_leans_on_prints_its_reasoning(model):
    result = model.cross("I/i pd/pd+", "I/i pd/pd+")
    texts = {a.id: a.text for a in result.assumptions}
    seen_reasoning = set()
    for support in result.support.values():
        for claim in support.used:
            if claim.strongest_support is EvidenceLevel.INFERRED:
                reasoning = " ".join(claim.interpretation.split())
                # Claims with identical reasoning are printed once.
                assert reasoning in seen_reasoning or any(reasoning in t for t in texts.values())
                seen_reasoning.add(reasoning)
    assert seen_reasoning


@pytest.mark.parametrize(
    "args",
    [
        ["--mother", "b/b r/r", "--father", "b/b r/R"],
        ["--mother", "b/b", "--father", "b/b"],
        ["--mother-shows", "yellow", "--father-shows", "blue"],
    ],
)
def test_the_four_open_decisions_are_stated_on_every_result(args):
    """Strain scope, source authority, the r-sex recombination fraction and albino
    heterogeneity are the owner's to decide. Whatever the cross touches, the
    result says they are assumed, in both views."""
    code, doc = cli_json(*args)
    by_id = {a["id"]: a for a in doc["assumptions"]}
    for open_id in OPEN_IDS:
        assert by_id[open_id]["open_decision"] is True
    text = runner.invoke(app, ["cross", *args]).output
    assert text.count("[open decision]") == 4
    assert "356 strain names" in by_id["strain_scope"]["text"]
    assert "recombination fraction 0" in by_id["r_sex_recombination"]["text"]
    assert "tyr vs oca2" in by_id["albino_allele"]["text"]
    assert "provisional and undecided" in by_id["source_authority"]["text"]


def test_a_result_without_its_open_decisions_is_not_rendered(model):
    result = model.cross("b/b r/r", "b/b r/R")
    result.assumptions = [a for a in result.assumptions if a.id != "albino_allele"]
    with pytest.raises(ModelError, match="albino_allele"):
        format_cross(result)
    with pytest.raises(ModelError, match="albino_allele"):
        cross_to_json(result)
    ranged = model.cross_from_phenotypes(["yellow"], ["blue"])
    ranged.assumptions = []
    with pytest.raises(ModelError, match="not rendered"):
        format_range(ranged)
    with pytest.raises(ModelError, match="not rendered"):
        range_to_json(ranged)
    assert {a.id for a in OPEN_DECISIONS} == set(OPEN_IDS)
    assert all(isinstance(a, Assumption) and a.open_decision for a in OPEN_DECISIONS)


def test_unresolved_heterozygotes_carry_a_warning():
    model = GeneticModel(_bundle(dominance=False))
    doc = cross_to_json(model.cross("A/a", "A/A"))
    assert {c["label"] for c in doc["offspring"]["overall"]["classes"]} == {"T1?", NO_TRAIT}
    unresolved = [
        t
        for c in doc["offspring"]["overall"]["classes"]
        for t in c["traits"]
        if t["state"] == "unresolved"
    ]
    assert unresolved
    assert "dominance_unrecorded" in [w["code"] for w in doc["warnings"]]
    assert "no dominance claim" in format_cross(model.cross("A/a", "A/A"))


# ------------------------------------------------------------------ AC-4 refusals


def test_refusal_multilocus_is_an_error_when_asked_and_listed_when_not(model):
    with pytest.raises(NotPredictable, match="multilocus"):
        model.hypotheses(["miyuki"], Sex.MALE)
    _, doc = cli_json("--mother", "b/b", "--father", "b/b")
    codes = {r["trait"]: r["code"] for r in doc["not_predictable"]}
    assert codes["orochi"] == codes["miyuki"] == "multilocus"


def test_refusal_no_inheritance_data_is_listed_by_name_with_its_code(model):
    with pytest.raises(NotPredictable, match="no inheritance data"):
        model.hypotheses(["aurora"], Sex.FEMALE)
    _, doc = cli_json("--mother", "b/b", "--father", "b/b")
    codes = {r["trait"]: r["code"] for r in doc["not_predictable"]}
    assert codes["aurora"] == "no_inheritance_data"
    count = sum(1 for c in codes.values() if c == "no_inheritance_data")
    text = runner.invoke(app, ["cross", "--mother", "b/b", "--father", "b/b"]).output
    assert f"{count} further traits have no inheritance data" in text


def test_refusal_a_mode_without_an_allele_model_says_so(model):
    reasons = {r.trait: r for r in model.refusals()}
    assert reasons["YWKo"].code == "no_allele_model"
    assert "recessive" in reasons["YWKo"].reason
    # Hitomi is a composite of two traits that have no allele model.
    assert reasons["Hitomi"].code == "no_allele_model"
    assert "bigeye" in reasons["Hitomi"].reason
    with pytest.raises(NotPredictable, match="no allele model"):
        model.hypotheses(["YWKo"], Sex.FEMALE)


def test_every_refusal_code_in_use_is_documented(model):
    assert {r.code for r in model.refusals()} <= set(REFUSALS)


def test_refusal_a_disputed_dominance_claim_is_not_predicted_through():
    model = GeneticModel(_bundle(disputed_dominance=True))
    assert not model.predictable("T1") and not model.predictable("T2")
    reasons = {r.trait: r for r in model.refusals()}
    assert reasons["T1"].code == "disputed"
    assert "dominant_over" in reasons["T1"].reason
    with pytest.raises(NotPredictable, match="disputed"):
        model.hypotheses(["T1"], Sex.FEMALE)
    result = model.cross("A/a", "A/a")
    assert result.overall == {(NO_TRAIT,): F(1)}, "a disputed trait is not predicted"
    assert {r.code for r in result.refusals} == {"disputed"}


def test_refusal_a_disputed_trait_requirement_is_not_predicted_through():
    model = GeneticModel(_bundle(disputed_requires=True))
    assert {r.trait for r in model.refusals() if r.code == "disputed"} == {"T1", "T2"}
    with pytest.raises(NotPredictable, match="disputed"):
        model.hypotheses(["T2"], Sex.MALE)


def test_an_undisputed_synthetic_bundle_predicts():
    model = GeneticModel(_bundle())
    assert model.predictable("T1") and not model.refusals()
    assert model.cross("A/a", "A/a").overall[("T1",)] == F(1, 4)


def test_the_real_seed_has_no_disputed_trait_claim(model):
    """If this starts failing a source now contradicts a claim the cross reads; the
    trait will be refused with code `disputed`, which is the intended behaviour."""
    assert not [r for r in model.refusals() if r.code == "disputed"]


def test_refusal_two_linked_loci_with_no_recombination_fraction():
    model = GeneticModel(_bundle(linked=True))
    with pytest.raises(LinkedLoci, match="no recombination fraction"):
        model.cross("A/a B/b", "A/a B/b")
    with pytest.raises(LinkedLoci):
        model.cross_from_phenotypes(["T1", "T2"], ["T1"])
    # One of the pair at a time is fine: nothing assorts against anything.
    assert model.cross("A/a", "A/a").overall[("T1",)] == F(1, 4)
    assert model.cross("A/a", "a/a").overall[("T1",)] == F(1, 2)


def test_refusal_linked_loci_is_json_with_its_own_code():
    model = GeneticModel(_bundle(linked=True))
    with pytest.raises(LinkedLoci) as exc:
        model.cross("A/a B/b", "A/a B/b")
    doc = error_to_json(exc.value)
    assert doc["error"]["code"] == "linked_loci_no_recombination_fraction"
    assert "L1 and L2" in doc["error"]["message"]


def test_the_r_locus_and_sex_determining_gene_are_the_stated_assumption_not_a_refusal(model):
    """The seed does hold a `linked_to` claim between the r locus and dmy. dmy has
    no alleles in the model, so the pair is never two loci in a cross; the r-sex rate
    of 0 is the open decision stated on every result, and the cross runs."""
    assert any(c.subject.name == "r locus" and c.object.name == "dmy" for c in model.linked)
    result = model.cross("b/b R/r", "b/b R/r")
    assert result.overall
    assert any(a.id == "r_sex_recombination" for a in result.assumptions)


def test_the_validated_crosses_do_not_move(model):
    """Spec constraint: the four open decisions are surfaced, not resolved. The
    numbers of the validated crosses do not move."""
    result = model.cross("b/b r/r", "b/b r/R")
    assert result.by_sex[Sex.FEMALE] == {("white",): F(1)}
    assert result.by_sex[Sex.MALE] == {("yellow",): F(1)}
    hd = model.parse("B/b R/r", Sex.FEMALE)
    assert model.class_shares(hd, model.parse("b/b r/r", Sex.MALE), Sex.MALE) == {
        ("white",): F(1, 4),
        ("blue",): F(1, 4),
        ("yellow",): F(1, 4),
        (NO_TRAIT,): F(1, 4),
    }
