"""Offline tests for citation-following discovery.

The screen is four filters in a row, and each one has a way to be wrong that
the measurement in `docs/research/enrich-yield-2026-09.md` ran into by hand: a
preprint counted as a second paper, a seed paper rediscovered as new, and a
medaka paper whose title never says medaka. A fake backend stands in for Europe
PMC, so nothing here touches the network or a database.
"""

from __future__ import annotations

import re

import httpx
from typer.testing import CliRunner

from medaka_ontology import cli
from medaka_ontology.citations import mentions_medaka, normalise_title, screen_citations
from medaka_ontology.discovery import DiscoveryTier, EuropePmcBackend

SEED = "11111111"
OTHER_SEED = "22222222"


def _link(id_: str, title: str, source: str = "MED") -> dict:
    return {"id": id_, "source": source, "title": title, "pubYear": 2024}


def _core(id_: str, title: str, abstract: str = "", source: str = "MED", **extra) -> dict:
    record = {"id": id_, "source": source, "title": title, "abstractText": abstract}
    if source == "MED":
        record["pmid"] = id_
    return {**record, **extra}


class FakeCitations:
    """Link rows per (pmid, direction), and `core` records answered by EXT_ID."""

    def __init__(self, links: dict[tuple[str, str], list[dict]], core: list[dict]):
        self._links = links
        self._core = {r["id"]: r for r in core}
        self.searches: list[str] = []

    def links(self, pmid: str, direction: str) -> list[dict]:
        return self._links.get((pmid, direction), [])

    def search(self, query: str, page_size: int = 25) -> list[dict]:
        self.searches.append(query)
        ids = re.findall(r"EXT_ID:(\S+)", query)
        return [self._core[i] for i in ids if i in self._core]


def _backend() -> FakeCitations:
    """Six link rows: a preprint of a MED paper, a seed paper, a paper known by
    DOI only, a medaka paper that says so only in its abstract, a medaka-titled
    paper found from two seeds, and a zebrafish paper."""
    return FakeCitations(
        links={
            (SEED, "forward"): [
                _link("100", "Pigment cells in medaka fish."),
                _link("PPR9", "Pigment cells in Medaka fish", source="PPR"),
                _link(OTHER_SEED, "A seed paper citing another"),
                _link("300", "A paper the seed holds by DOI"),
                _link("400", "Leucophore fate in the teleost trunk"),
                _link("500", "Fin regeneration in zebrafish"),
            ],
            (OTHER_SEED, "forward"): [_link("100", "Pigment cells in medaka fish.")],
        },
        core=[
            _core("100", "Pigment cells in medaka fish", "We studied fish.", pmcid="PMC100"),
            _core("PPR9", "Pigment cells in Medaka fish", "Preprint.", source="PPR"),
            _core("300", "A paper the seed holds by DOI", "Medaka.", doi="10.1/SEEDED"),
            _core("400", "Leucophore fate in the teleost trunk", "In Oryzias latipes, ..."),
            _core("500", "Fin regeneration in zebrafish", "Danio rerio fins regrow."),
        ],
    )


def _screen(backend=None, **kwargs):
    return screen_citations(
        backend or _backend(),
        [SEED],
        known_pmids={SEED, OTHER_SEED},
        known_dois={"10.1/seeded"},
        **kwargs,
    )


def test_a_preprint_and_its_published_record_are_one_paper():
    screen = _screen()
    pigment = [k.paper for k in screen.kept if "pigment" in k.paper.title.lower()]
    assert [p.pmid for p in pigment] == ["100"]
    assert screen.deduped == 5, "six rows, one of them a preprint duplicate"


def test_the_published_record_wins_whichever_comes_first():
    backend = _backend()
    rows = backend._links[(SEED, "forward")]
    rows.insert(0, rows.pop(1))  # preprint first
    kept = {k.paper.pmid for k in _screen(backend).kept}
    assert "100" in kept


def test_titles_are_compared_without_case_markup_or_punctuation():
    assert normalise_title("<i>Pigment</i> cells in Medaka fish.") == normalise_title(
        "Pigment cells in medaka fish"
    )


def test_papers_the_seed_or_registry_holds_are_dropped():
    screen = _screen()
    kept = {k.paper.pmid for k in screen.kept}
    assert OTHER_SEED not in kept, "known by PMID"
    assert "300" not in kept, "known by DOI, which only the core record carries"
    assert screen.not_yet_known == 3


def test_known_papers_are_not_fetched():
    backend = _backend()
    _screen(backend)
    assert all(f"EXT_ID:{OTHER_SEED}" not in q for q in backend.searches)


def test_a_paper_naming_medaka_only_in_its_abstract_is_kept():
    kept = {k.paper.pmid for k in _screen().kept}
    assert "400" in kept


def test_a_paper_that_never_names_medaka_is_dropped():
    kept = {k.paper.pmid for k in _screen().kept}
    assert "500" not in kept
    assert not mentions_medaka("Fin regeneration in zebrafish", "Danio rerio fins regrow.")


def test_every_route_to_a_paper_is_recorded_as_provenance():
    screen = screen_citations(
        _backend(), [SEED, OTHER_SEED], known_pmids=set(), known_dois=set()
    )
    records = [r for r in screen.discovered() if r.pmid == "100"]
    assert {r.discovered_via for r in records} == {
        f"citation:forward:{SEED}",
        f"citation:forward:{OTHER_SEED}",
    }
    assert {r.discovery_tier for r in records} == {DiscoveryTier.CITATION}
    assert records[0].pmcid == "PMC100", "core metadata travels with the paper"


def test_abstracts_are_fetched_in_batches_of_twenty():
    links = [_link(str(1000 + i), f"medaka paper {i}") for i in range(45)]
    backend = FakeCitations({(SEED, "forward"): links}, core=[])
    screen = screen_citations(backend, [SEED])
    assert len(backend.searches) == 3
    assert screen.medaka == 45, "no core record: judged on the link row's title"
    assert screen.no_abstract == 45


def test_links_page_until_hit_count():
    pages = {
        "1": {"hitCount": 3, "citationList": {"citation": [{"id": "1"}, {"id": "2"}]}},
        "2": {"hitCount": 3, "citationList": {"citation": [{"id": "3"}]}},
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(f"/MED/{SEED}/citations")
        seen.append(request.url.params["page"])
        return httpx.Response(200, json=pages[request.url.params["page"]])

    backend = EuropePmcBackend(httpx.Client(transport=httpx.MockTransport(handler)), interval=0)
    assert [r["id"] for r in backend.links(SEED, "forward")] == ["1", "2", "3"]
    assert seen == ["1", "2"]


def test_backward_links_read_the_reference_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/references")
        return httpx.Response(
            200, json={"hitCount": 1, "referenceList": {"reference": [{"id": "9"}]}}
        )

    backend = EuropePmcBackend(httpx.Client(transport=httpx.MockTransport(handler)), interval=0)
    assert backend.links(SEED, "backward") == [{"id": "9"}]


def test_dry_run_prints_counts_per_step_without_neo4j(monkeypatch):
    backend = _backend()
    backend.close = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "EuropePmcBackend", lambda: backend)
    monkeypatch.setattr(
        cli, "seed_identifiers", lambda: ([SEED], {SEED, OTHER_SEED}, {"10.1/seeded"})
    )

    def no_database():
        raise AssertionError("the dry run must not open Neo4j")

    monkeypatch.setattr(cli, "session_scope", no_database)

    result = CliRunner().invoke(cli.app, ["pipeline", "--from-citations", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "raw 6 -> deduped 5 -> not yet known 3 -> medaka-mentioning 2" in result.output


def test_dry_run_needs_from_citations():
    result = CliRunner().invoke(cli.app, ["pipeline", "--dry-run"])
    assert result.exit_code == 1
