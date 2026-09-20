"""The discovery pipeline against a live Neo4j, with the network stubbed out.

Skipped when no database is reachable. The search and full-text backends are
fakes on purpose: a test that hit Europe PMC would fail when the service is slow
and change meaning whenever the literature does, and the properties under test
here are about *our* bookkeeping, not about what is published.

These tests ingest into whatever `.env` points at and rebuild the graph from the
seed files first. Point it at a scratch instance if that is not what you want.
"""

from __future__ import annotations

import pytest

from medaka_ontology.candidates import (
    AcceptanceError,
    accept_candidate,
    pending_candidates,
    reject_candidate,
    store_candidates,
)
from medaka_ontology.db import Neo4jUnavailableError, install_schema, session_scope
from medaka_ontology.discovery import DiscoveredPaper
from medaka_ontology.ingest import ingest_bundle
from medaka_ontology.lexicon import build_lexicon
from medaka_ontology.loader import load_dir
from medaka_ontology.pipeline import RunLimits, run
from medaka_ontology.registry import (
    adopt_seed_papers,
    current_state,
    register_discovered,
)
from medaka_ontology.vocabulary import CandidateStatus, EvidenceLevel, PaperState

SEED_PAPER_ID = "paper:doi:10.1093/molbev/msag021"

#: A fabricated full text, so the assertions below are about the pipeline rather
#: than about what a real article happens to say this month.
FAKE_JATS = """<article>
<abstract><p>We studied ornamental medaka strains.</p></abstract>
<body>
<sec><title>Results</title>
<p>Genome editing of adcy5 produced hyper-melanism in orochi individuals.</p>
<p>No association was detected between hikari and adcy5 in this cohort.</p>
</sec>
<sec><title>References</title>
<p>zic1 orochi hikari adcy5 melanogenesis kcnq5a hirenaga swallow</p>
</sec>
</body></article>"""

ZEBRAFISH_JATS = """<article>
<abstract><p>Fin size control in zebrafish.</p></abstract>
<body><sec><title>Results</title>
<p>CRISPR knockout of kcnq5a altered fin ray elongation in zebrafish.</p>
</sec></body></article>"""


class FakeSearch:
    def __init__(self, results: list[dict]):
        self._results = results
        self.calls: list[str] = []

    def search(self, query: str, page_size: int = 25) -> list[dict]:
        self.calls.append(query)
        return self._results


class FakeFullText:
    def __init__(self, by_pmcid: dict[str, str]):
        self._by_pmcid = by_pmcid
        self.calls: list[str] = []

    def fetch_xml(self, pmcid: str) -> str:
        self.calls.append(pmcid)
        if pmcid not in self._by_pmcid:
            raise RuntimeError("not in corpus")
        return self._by_pmcid[pmcid]


@pytest.fixture(scope="module")
def session():
    try:
        with session_scope() as s:
            yield s
    except Neo4jUnavailableError as exc:
        pytest.skip(f"no Neo4j: {exc}")


@pytest.fixture(scope="module")
def graph(session):
    session.run("MATCH (n) DETACH DELETE n")
    install_schema(session)
    ingest_bundle(session, load_dir())
    adopt_seed_papers(session)
    return session


@pytest.fixture
def clean_candidates(graph):
    graph.run("MATCH (c:Candidate) DETACH DELETE c")
    graph.run("MATCH (g:ProposedEntity) DETACH DELETE g")
    return graph


# --- the registry ----------------------------------------------------------


def test_curated_papers_start_accepted(graph):
    """Otherwise the first discovery run drags them back to DISCOVERED - the
    queries are built from the very claims they support, so it finds them
    immediately."""
    assert current_state(graph, SEED_PAPER_ID) is PaperState.ACCEPTED


def test_rediscovering_a_curated_paper_does_not_reset_it(graph):
    register_discovered(
        graph,
        [
            DiscoveredPaper(
                title="Genomic consequences of domestication",
                doi="10.1093/molbev/msag021",
                discovered_via="trait:trait-orochi",
            )
        ],
    )
    assert current_state(graph, SEED_PAPER_ID) is PaperState.ACCEPTED


def test_a_paper_found_twice_records_both_routes(graph):
    paper = DiscoveredPaper(
        title="Zic genes in teleosts", doi="10.1/zic", discovered_via="gene:trait-hikari"
    )
    register_discovered(graph, [paper])
    paper.discovered_via = "mechanism:trait-hikari"
    register_discovered(graph, [paper])

    via = graph.run(
        "MATCH (p:Paper {id:'paper:doi:10.1/zic'}) RETURN p.discovered_via AS v"
    ).single()["v"]
    assert set(via) == {"gene:trait-hikari", "mechanism:trait-hikari"}


def test_registering_the_same_paper_twice_creates_one_node(graph):
    before = graph.run("MATCH (p:Paper) RETURN count(p) AS n").single()["n"]
    paper = DiscoveredPaper(title="dup", doi="10.1/dup", discovered_via="trait:x")
    register_discovered(graph, [paper])
    register_discovered(graph, [paper])
    after = graph.run("MATCH (p:Paper) RETURN count(p) AS n").single()["n"]
    assert after == before + 1


def test_curated_metadata_is_never_overwritten_by_a_search_hit(graph):
    """The curated entry is the one somebody checked."""
    register_discovered(
        graph,
        [
            DiscoveredPaper(
                title="WRONG TITLE FROM SEARCH",
                doi="10.1093/molbev/msag021",
                discovered_via="trait:x",
            )
        ],
    )
    title = graph.run(
        "MATCH (p:Paper {id:$id}) RETURN p.title AS t", id=SEED_PAPER_ID
    ).single()["t"]
    assert "WRONG TITLE" not in title


# --- a full run ------------------------------------------------------------


def test_run_stages_candidates_without_touching_the_ontology(clean_candidates):
    graph = clean_candidates
    claims_before = graph.run("MATCH (c:Claim) RETURN count(c) AS n").single()["n"]

    search = FakeSearch(
        [
            {
                "title": "Fake ornamental medaka study",
                "doi": "10.1/fake-run",
                "pmcid": "PMCFAKE1",
                "pubYear": "2026",
                "isOpenAccess": "Y",
                "inEPMC": "Y",
            }
        ]
    )
    report = run(
        graph,
        limits=RunLimits(max_queries=1, max_papers_to_acquire=3),
        search_backend=search,
        fulltext_backend=FakeFullText({"PMCFAKE1": FAKE_JATS}),
    )

    assert report.papers_new >= 1
    assert report.candidates_new >= 1
    claims_after = graph.run("MATCH (c:Claim) RETURN count(c) AS n").single()["n"]
    assert claims_after == claims_before, "a run must not write claims"


def test_rerunning_does_not_duplicate_candidates(clean_candidates):
    graph = clean_candidates
    search = FakeSearch(
        [
            {
                "title": "Fake ornamental medaka study",
                "doi": "10.1/fake-idem",
                "pmcid": "PMCFAKE2",
                "isOpenAccess": "Y",
                "inEPMC": "Y",
            }
        ]
    )
    limits = RunLimits(max_queries=1, max_papers_to_acquire=3)
    backend = FakeFullText({"PMCFAKE2": FAKE_JATS})

    first = run(graph, limits=limits, search_backend=search, fulltext_backend=backend)
    count_after_first = graph.run(
        "MATCH (c:Candidate) RETURN count(c) AS n"
    ).single()["n"]

    # Re-processing the same paper: reset its state as a rerun of an earlier
    # pipeline version would.
    graph.run(
        "MATCH (p:Paper {id:'paper:doi:10.1/fake-idem'}) "
        "SET p.processing_state = $s",
        s=PaperState.DISCOVERED.value,
    )
    second = run(graph, limits=limits, search_backend=search, fulltext_backend=backend)

    count_after_second = graph.run(
        "MATCH (c:Candidate) RETURN count(c) AS n"
    ).single()["n"]
    assert count_after_second == count_after_first
    assert second.candidates_new == 0
    assert second.candidates_duplicate >= first.candidates_new


def test_reference_sections_do_not_become_candidates(clean_candidates):
    """The fake article's reference list names every entity. If it were mined,
    every pair in it would be a candidate."""
    graph = clean_candidates
    run(
        graph,
        limits=RunLimits(max_queries=1, max_papers_to_acquire=2),
        search_backend=FakeSearch(
            [{"title": "refs", "doi": "10.1/refs", "pmcid": "PMCREF", "inEPMC": "Y"}]
        ),
        fulltext_backend=FakeFullText({"PMCREF": FAKE_JATS}),
    )
    quotes = [r["quote"] for r in pending_candidates(graph)]
    assert all("kcnq5a hirenaga swallow" not in (q or "") for q in quotes)


def test_negated_sentences_are_staged_but_marked(clean_candidates):
    graph = clean_candidates
    run(
        graph,
        limits=RunLimits(max_queries=1, max_papers_to_acquire=2),
        search_backend=FakeSearch(
            [{"title": "neg", "doi": "10.1/neg", "pmcid": "PMCNEG", "inEPMC": "Y"}]
        ),
        fulltext_backend=FakeFullText({"PMCNEG": FAKE_JATS}),
    )
    rows = pending_candidates(graph)
    negated = [r for r in rows if r["negated"]]
    assert negated, "the 'No association was detected' sentence should be flagged"


# --- acceptance ------------------------------------------------------------


def _stage_one(graph, lexicon, text: str, species: str):
    from medaka_ontology.extraction import extract_from_text

    graph.run(
        "MERGE (p:Paper {id:'paper:doi:10.1/accept-test'}) "
        "ON CREATE SET p.title='acceptance fixture', p.doi='10.1/accept-test'"
    )
    candidates = extract_from_text(
        "paper:doi:10.1/accept-test", text, lexicon, default_species=species
    )
    assert candidates, "fixture text produced no candidate"
    store_candidates(graph, candidates)
    return candidates[0]


def test_accepting_a_candidate_creates_a_real_claim(clean_candidates):
    graph = clean_candidates
    lexicon = build_lexicon(graph)
    candidate = _stage_one(
        graph,
        lexicon,
        "Genome editing of adcy5 produced hyper-melanism in orochi.",
        "Oryzias latipes",
    )
    claim_id = accept_candidate(
        graph, candidate.id, EvidenceLevel.FUNCTIONAL_VALIDATION, note="reviewed"
    )
    levels = [
        r["level"]
        for r in graph.run(
            "MATCH (c:Claim {id:$id})<-[:SUPPORTS]-(e:Evidence) RETURN e.level AS level",
            id=claim_id,
        )
    ]
    assert EvidenceLevel.FUNCTIONAL_VALIDATION.value in levels


def test_the_comparative_ceiling_applies_to_acceptance(clean_candidates):
    """The bug this test exists for: the ceiling lived on the Claim model for
    trait subjects and in the seed loader for gene subjects, so the acceptance
    path - which used neither - let zebrafish evidence onto a medaka gene at
    FUNCTIONAL_VALIDATION."""
    graph = clean_candidates
    lexicon = build_lexicon(graph)
    candidate = _stage_one(
        graph,
        lexicon,
        "CRISPR knockout of adcy5 altered melanogenesis in zebrafish.",
        "Danio rerio",
    )
    with pytest.raises(AcceptanceError) as exc:
        accept_candidate(graph, candidate.id, EvidenceLevel.FUNCTIONAL_VALIDATION)
    assert "Danio rerio" in str(exc.value)

    claim_id = accept_candidate(graph, candidate.id, EvidenceLevel.OBSERVATIONAL)
    assert claim_id


def test_a_decided_candidate_cannot_be_decided_twice(clean_candidates):
    graph = clean_candidates
    lexicon = build_lexicon(graph)
    candidate = _stage_one(
        graph,
        lexicon,
        "Genome editing of adcy5 produced hyper-melanism in orochi.",
        "Oryzias latipes",
    )
    reject_candidate(graph, candidate.id, note="co-mention only")
    with pytest.raises(AcceptanceError):
        accept_candidate(graph, candidate.id, EvidenceLevel.OBSERVATIONAL)


def test_proposed_genes_are_checked_against_the_existing_ontology(clean_candidates):
    """Issue #1 §6. A proposal is only news if the symbol is actually unknown.
    One that already exists under another label must say so, because adding it
    again splits one concept across two nodes."""
    from medaka_ontology.candidates import pending_proposed_genes, store_proposed_genes
    from medaka_ontology.resolution import ProposedGene
    from medaka_ontology.vocabulary import ResolutionStatus

    graph = clean_candidates
    graph.run(
        "MERGE (p:Paper {id:'paper:doi:10.1/resolve-test'}) "
        "ON CREATE SET p.title='resolution fixture', p.doi='10.1/resolve-test'"
    )
    store_proposed_genes(
        graph,
        [
            # Genuinely absent from the ontology.
            ProposedGene("hoxa9b", "quote", "paper:doi:10.1/resolve-test", "Results"),
            # Already a Gene in the seed data; must not read as new.
            ProposedGene("adcy5", "quote", "paper:doi:10.1/resolve-test", "Results"),
        ],
    )
    by_symbol = {r["symbol"]: r for r in pending_proposed_genes(graph)}
    assert by_symbol["hoxa9b"]["resolution"] == ResolutionStatus.NEW.value
    assert by_symbol["adcy5"]["resolution"] == ResolutionStatus.RESOLVED_EXACT.value


def test_rejected_candidates_stay_recorded(clean_candidates):
    """So the same call is not re-proposed as new on the next run."""
    graph = clean_candidates
    lexicon = build_lexicon(graph)
    candidate = _stage_one(
        graph,
        lexicon,
        "Genome editing of adcy5 produced hyper-melanism in orochi.",
        "Oryzias latipes",
    )
    reject_candidate(graph, candidate.id, note="not a claim")
    status = graph.run(
        "MATCH (c:Candidate {id:$id}) RETURN c.status AS s", id=candidate.id
    ).single()["s"]
    assert status == CandidateStatus.REJECTED.value
    assert candidate.id not in {r["id"] for r in pending_candidates(graph)}
