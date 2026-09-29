"""Checks over the committed seed data itself.

These are not unit tests of the loader; they are assertions about the knowledge
base's honesty. A seed file that quietly upgrades a GWAS nomination to causal, or
that drops one side of a contradiction, would pass every other test in this suite.
"""

from __future__ import annotations

import pytest

from medaka_ontology.loader import load_dir
from medaka_ontology.vocabulary import EvidenceLevel, Predicate, ReviewReason, Stance

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
    """`aliases` reads as sourced, so no Japanese string may sit there. The
    literature romanizes throughout, which makes every kanji form derived from it
    our reconstruction; `unverified_labels` is where reconstruction goes."""
    for entity in bundle.entities:
        for alias in entity.aliases:
            assert alias.isascii(), f"{entity.name}: {alias!r} claims a source it lacks"


def test_japanese_name_requires_breeder_academic_link(bundle):
    """This field used to be banned outright, and the ban was right for as long as
    every source romanized. The breeder sources do not, so the rule becomes
    conditional rather than disappearing.

    2026-09 breeder-vocabulary spec: this field now covers two shapes. One is a
    NEW_ORNAMENTAL_TRAIT the trade introduced (kagamirin, fusahire), which also
    carries its own has_phenotype/affects_anatomy claims citing a Japanese-titled
    breeder source -- there, "a claim about this entity cites Japanese evidence"
    was a fair proxy for "sourced". The other is an existing Kon et al. 2026
    Table 1 trait (orochi, hikari, ...) whose biology is already fully claimed
    against `kon2026`; the trade source contributes only the string, not a new
    biological claim, so it would never pick up a claim of its own to satisfy
    that proxy. The field's actual contract does not change: `japanese_name` is
    only ever set once 01-sources-breeder.yaml's CSV survey traces the string to
    a real source with a matching definition (docs/research/breeder-vocabulary-2026-09.md,
    spec 승격 기준), and every promotion carries `BREEDER_ACADEMIC_LINK` in
    `review_reasons` precisely because that identity claim -- "Kon's X is the
    trade's X" -- is ours, not the source's. That reason is what this test can
    still check without re-deriving the CSV survey by hand.
    """
    japanese_sources = {p.key for p in bundle.papers if not p.title.isascii()}
    assert japanese_sources, "vacuous while no source prints Japanese"

    for entity in bundle.entities:
        if entity.japanese_name is None:
            continue
        assert not entity.japanese_name.isascii(), entity.name
        assert ReviewReason.BREEDER_ACADEMIC_LINK in entity.review_reasons, (
            f"{entity.name}: japanese_name is set without BREEDER_ACADEMIC_LINK"
        )


def test_breeder_sources_can_never_outrank_the_literature(bundle):
    """A trade page is the entire record for the scale and fin traits, which is
    exactly why the level is the containment rather than anyone's restraint.
    BREEDER_OBSERVATION is rank 10, below the OBSERVATIONAL rung a published
    phenotype table sits on."""
    trade = {p.key for p in bundle.papers if not (p.doi or p.pmid or p.pmcid)}
    assert trade, "vacuous while every source has a formal identifier"

    for claim in bundle.claims:
        for ev in claim.evidence:
            if ev.paper in trade:
                assert ev.level is EvidenceLevel.BREEDER_OBSERVATION, (
                    f"{claim.predicate.value} on {claim.subject.name} cites "
                    f"{ev.paper} at {ev.level.value}"
                )


def test_breeder_sources_stay_out_of_the_acquisition_pipeline(bundle):
    """`register_discovered` skips a paper it cannot key by DOI/PMID/PMCID, and
    seed ingest never writes `processing_state`, so a shop page is invisible to
    `pipeline` as long as it carries no formal identifier. A URL is still required
    -- PRD §2.4 wants a locator, just not one that makes the paper fetchable."""
    for paper in bundle.papers:
        if paper.doi or paper.pmid or paper.pmcid:
            continue
        assert paper.url, f"{paper.key}: no identifier of any kind"


def test_new_traits_from_outside_the_literature_are_routed_to_a_human(bundle):
    """PRD §12. Nothing enters the trait vocabulary on a breeder's say-so without
    somebody seeing it first.

    2026-09: `BREEDER_ACADEMIC_LINK` used to imply `NEW_ORNAMENTAL_TRAIT`, back
    when the only entities carrying it (kagamirin, fusahire) were both. The
    breeder-vocabulary spec now also puts it on existing Kon et al. 2026 traits
    that merely picked up an attested trade name (orochi's オロチ and so on) --
    those are not new to the ontology, so the old direction of the implication
    no longer holds. What still has to hold, checked here, is the direction PRD
    §12 actually cares about: a trait the trade introduced, not the literature,
    must be flagged for human review, which for this seed means carrying
    `BREEDER_ACADEMIC_LINK` alongside `NEW_ORNAMENTAL_TRAIT`.
    """
    for entity in bundle.entities:
        if ReviewReason.NEW_ORNAMENTAL_TRAIT not in entity.review_reasons:
            continue
        assert ReviewReason.BREEDER_ACADEMIC_LINK in entity.review_reasons, entity.name


def test_unverified_labels_are_flagged_for_review(bundle):
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
    "leucophore free-2",
    "white leucophore",
    "many leucophores-3",
    "fused centrum",
    "panda (pa) lab mutant",
}

#: The only breeder-facing ornamental traits whose genetics reach causal or
#: functionally validated level in the current evidence base. hikari is not one:
#: its causal evidence was done in the Da mutant and sits there (ADR 0003, own
#: subject). hikari reaches it only through `putatively_same_as`.
CAUSAL_ORNAMENTAL_TRAITS = {"orochi", "albino", "yellow"}


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
