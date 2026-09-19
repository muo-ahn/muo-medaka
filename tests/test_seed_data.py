"""Checks over the committed seed data itself.

These are not unit tests of the loader; they are assertions about the knowledge
base's honesty. A seed file that quietly upgrades a GWAS nomination to causal, or
that drops one side of a contradiction, would pass every other test in this suite.
"""

from __future__ import annotations

import pytest

from medaka_ontology.loader import load_dir
from medaka_ontology.vocabulary import EvidenceLevel, Predicate, Stance

STRONG = {EvidenceLevel.CAUSAL_VARIANT, EvidenceLevel.FUNCTIONAL_VALIDATION}


@pytest.fixture(scope="module")
def bundle():
    return load_dir()


def test_seed_files_load_and_cross_reference(bundle):
    assert bundle.papers and bundle.entities and bundle.claims


def test_every_claim_cites_a_paper_that_exists(bundle):
    keys = {p.key for p in bundle.papers}
    for claim in bundle.claims:
        for ev in claim.evidence:
            assert ev.paper in keys


def test_every_paper_is_traceable(bundle):
    """PRD §2.4."""
    for paper in bundle.papers:
        assert paper.doi or paper.pmid or paper.pmcid or paper.url


def test_japanese_labels_are_never_recorded_as_sourced(bundle):
    """The seed paper romanizes throughout, so any Japanese-script string in the
    ontology is our reconstruction and must sit in `unverified_labels`."""
    for entity in bundle.entities:
        for alias in entity.aliases:
            assert alias.isascii(), f"{entity.name}: {alias!r} claims a source it lacks"
        assert entity.japanese_name is None, entity.name


def test_unverified_labels_are_flagged_for_review(bundle):
    from medaka_ontology.vocabulary import ReviewReason

    for entity in bundle.entities:
        if entity.unverified_labels:
            assert ReviewReason.UNVERIFIED_LABEL in entity.review_reasons, entity.name


def test_the_known_contradictions_survived_ingestion(bundle):
    """The three source-level conflicts this dataset is built around. If a future
    edit resolves one by deletion, PRD §9 has been violated and this fails."""
    disputed = {
        (c.subject.name, c.predicate, c.object.name) for c in bundle.claims if c.is_disputed
    }
    assert ("panda", Predicate.ASSOCIATED_WITH_GENE, "slc24a5") in disputed
    assert ("panda", Predicate.ASSOCIATED_WITH_GENE, "pnp4a") in disputed
    assert ("daruma", Predicate.ASSOCIATED_WITH_GENE, "wnt4b") in disputed


# Laboratory mutants, where a causal gene is exactly what the literature
# established. Kept apart from the breeder traits so the assertion below is about
# ornamental traits specifically.
LAB_MUTANTS = {
    "Da mutant",
    "guanineless",
    "few melanophore",
    "leucophore free",
    "fused centrum",
    "panda (pa) lab mutant",
}

#: The only breeder-facing ornamental traits whose genetics reach causal or
#: functionally validated level in the current evidence base.
CAUSAL_ORNAMENTAL_TRAITS = {"orochi", "hikari", "albino", "yellow"}


def test_causal_level_genetics_stays_on_the_traits_that_earned_it(bundle):
    """Promoting a GWAS nomination to CAUSAL_VARIANT is the specific error the
    PRD's evidence ladder exists to prevent, and it is an easy one to make while
    editing seed files. Twenty-two of the paper's twenty-six trait-gene
    assignments must stay below this line.
    """
    offenders = set()
    for claim in bundle.claims:
        if claim.subject.label.value != "OrnamentalTrait":
            continue
        if claim.subject.name in LAB_MUTANTS:
            continue
        if claim.predicate not in {
            Predicate.ASSOCIATED_WITH_GENE,
            Predicate.CAUSED_BY_VARIANT,
        }:
            continue
        for ev in claim.evidence:
            if ev.stance is Stance.SUPPORTS and ev.level in STRONG:
                if claim.subject.name not in CAUSAL_ORNAMENTAL_TRAITS:
                    offenders.add((claim.subject.name, claim.object.name, ev.level.value))
    assert not offenders, f"causal-level evidence on undocumented traits: {offenders}"


def test_comparative_evidence_never_outranks_the_ceiling_on_a_medaka_claim(bundle):
    """PRD §10. A zebrafish knockout validates the zebrafish gene; on a medaka
    trait it is an argument from homology. The loader enforces this, so a failure
    here means the rule was weakened rather than that the data drifted."""
    from medaka_ontology.models import COMPARATIVE_CEILING
    from medaka_ontology.vocabulary import EVIDENCE_RANK

    genes = {e.name: e for e in bundle.entities if e.label.value == "Gene"}
    ceiling = EVIDENCE_RANK[COMPARATIVE_CEILING]
    for claim in bundle.claims:
        subject_species = (genes[claim.subject.name].species
                           if claim.subject.name in genes else "Oryzias latipes")
        if claim.subject.label.value in {"HumanGene", "HumanPhenotype"}:
            continue
        if not subject_species.lower().startswith("oryzias"):
            continue
        for ev in claim.evidence:
            if ev.is_comparative:
                assert ev.rank <= ceiling, (
                    f"{claim.subject.name} -> {claim.object.name}: "
                    f"{ev.species} evidence at {ev.level.value}"
                )


def test_at_least_one_comparative_finding_is_present(bundle):
    """Guards the test above from passing vacuously if species labelling is ever
    dropped from the seed files."""
    assert any(ev.is_comparative for c in bundle.claims for ev in c.evidence)


def test_comparative_evidence_names_its_species(bundle):
    """A zebrafish result standing in for a medaka one is the quiet failure mode
    of every cross-species knowledge base."""
    for entity in bundle.entities:
        if entity.label.value == "Gene":
            assert entity.species, entity.name


def test_composite_traits_declare_what_they_subsume(bundle):
    """Otherwise an umbrella class sharing a locus with its member reads as
    independent replication."""
    composites = {e.name for e in bundle.entities if e.is_composite}
    subsuming = {
        c.subject.name for c in bundle.claims if c.predicate is Predicate.SUBSUMES
    }
    assert composites <= subsuming, composites - subsuming


def test_every_gwas_locus_records_what_the_hit_rests_on(bundle):
    """n and interval width are what tell a reader whether a P-value means
    anything. A locus without them can be quoted misleadingly."""
    for entity in bundle.entities:
        if entity.label.value != "Locus":
            continue
        assert entity.n_cases, entity.name
        assert entity.best_p_value, entity.name
        assert entity.n_genes_in_interval, entity.name
