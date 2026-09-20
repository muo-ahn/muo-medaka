"""One discovery run, end to end, and the report it leaves behind.

Issue #1 §8. A run is bounded on purpose: caps on queries, on papers fetched and
on candidates per paper. An unbounded crawl would be easy to write and useless
to operate -- it would take hours, hammer a public API, and produce a review
queue too large for anyone to read, which amounts to discovering nothing.

The run is also resumable rather than transactional. Each paper advances through
its own states and is committed as it goes, so an interrupted run loses only the
paper in flight; the next run picks up from the registry instead of starting
over.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neo4j import Session

from .acquisition import EuropePmcFullTextBackend, FullTextBackend, acquire
from .candidates import store_candidates, store_proposed_genes
from .config import REPO_ROOT
from .discovery import EuropePmcBackend, SearchBackend, all_queries, run_queries
from .extraction import (
    detect_paper_species,
    extract_from_abstract,
    extract_from_fulltext,
)
from .lexicon import build_lexicon
from .registry import (
    actionable_papers,
    adopt_seed_papers,
    advance_state,
    papers_in_states,
    register_discovered,
    state_counts,
)
from .resolution import propose_new_genes
from .vocabulary import PaperState

RUN_DIR = REPO_ROOT / "data" / "runs"


@dataclass
class RunLimits:
    """What one run is allowed to do.

    Defaults are sized for a run someone will actually sit through and read the
    output of, not for maximum coverage.
    """

    max_traits: int | None = None
    max_queries: int = 12
    page_size: int = 25
    max_papers_to_acquire: int = 15
    max_candidates_per_paper: int = 40
    include_abstract_only: bool = True


@dataclass
class RunReport:
    """PRD §11 and issue #1 §8: what this run added, skipped and flagged."""

    started_at: str = ""
    finished_at: str = ""
    queries_run: int = 0
    hits: int = 0
    papers_new: int = 0
    papers_already_known: int = 0
    papers_rediscovered_via_new_route: int = 0
    fulltext_acquired: int = 0
    fulltext_failed: int = 0
    abstract_only: int = 0
    candidates_new: int = 0
    candidates_duplicate: int = 0
    proposed_genes: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)
    new_paper_titles: list[str] = field(default_factory=list)
    paper_states: dict[str, int] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def write(self, out_dir: Path | None = None) -> Path:
        out_dir = out_dir or RUN_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = (self.started_at or datetime.now(UTC).isoformat()).replace(":", "").replace(
            "-", ""
        )[:15]
        path = out_dir / f"run-{stamp}.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path


def discover(
    session: Session,
    backend: SearchBackend,
    limits: RunLimits,
    report: RunReport,
) -> None:
    """Query the literature from the graph, and register what comes back."""
    specs = all_queries(session, limit_traits=limits.max_traits)[: limits.max_queries]
    report.queries_run = len(specs)
    papers = list(run_queries(backend, specs, page_size=limits.page_size))
    report.hits = len(papers)

    registry_report = register_discovered(session, papers)
    report.papers_new = registry_report.added
    report.papers_already_known = registry_report.already_known
    report.papers_rediscovered_via_new_route = registry_report.new_via_recorded

    titles = {p.identifier: p.title for p in papers}
    for pid in registry_report.added_papers:
        for identifier, title in titles.items():
            if identifier and identifier.lower() in pid:
                report.new_paper_titles.append(title)
                break


def acquire_and_extract(
    session: Session,
    backend: FullTextBackend,
    limits: RunLimits,
    report: RunReport,
) -> None:
    """Fetch full text for actionable papers and stage candidates from it."""
    lexicon = build_lexicon(session)
    queue = actionable_papers(session, limit=limits.max_papers_to_acquire)

    for paper in queue:
        # The organism the paper is about, used as the default for every
        # sentence in it. Without this a comparative result in a sentence that
        # names no species is recorded as a medaka finding.
        paper_species = detect_paper_species(paper.get("title"), paper.get("abstract"))
        result = acquire(paper, backend)

        if result.ok and result.fulltext is not None:
            advance_state(session, paper["id"], PaperState.FULLTEXT_AVAILABLE)
            report.fulltext_acquired += 1
            candidates = extract_from_fulltext(
                result.fulltext,
                lexicon,
                max_candidates=limits.max_candidates_per_paper,
                default_species=paper_species,
            )
            proposals = propose_new_genes(
                paper["id"], result.fulltext.mineable_text, lexicon
            )
        else:
            advance_state(
                session, paper["id"], PaperState.INACCESSIBLE, reason=result.reason
            )
            report.fulltext_failed += 1
            report.failures.append({"paper": paper["id"], "reason": result.reason or ""})

            abstract = paper.get("abstract")
            if not (limits.include_abstract_only and abstract):
                continue
            # An abstract is thin evidence, but a paper with no open full text is
            # otherwise invisible to the ontology forever. The candidates it
            # produces are marked with the section they came from so nobody
            # mistakes them for a reading of the Results.
            report.abstract_only += 1
            candidates = extract_from_abstract(
                paper["id"], abstract, lexicon, default_species=paper_species
            )
            proposals = propose_new_genes(paper["id"], abstract, lexicon)

        candidate_report = store_candidates(session, candidates)
        report.candidates_new += candidate_report.stored
        report.candidates_duplicate += candidate_report.already_present
        report.proposed_genes += store_proposed_genes(session, proposals)

        # REVIEW_REQUIRED only when the run actually produced something to look
        # at; a paper that yielded nothing is EXTRACTED and stops being picked up.
        advance_state(
            session,
            paper["id"],
            PaperState.REVIEW_REQUIRED if candidate_report.stored else PaperState.EXTRACTED,
            force=True,
        )


def run(
    session: Session,
    limits: RunLimits | None = None,
    search_backend: SearchBackend | None = None,
    fulltext_backend: FullTextBackend | None = None,
    skip_discovery: bool = False,
) -> RunReport:
    """Execute one full cycle."""
    limits = limits or RunLimits()
    report = RunReport(started_at=datetime.now(UTC).isoformat())
    report.limits = asdict(limits)

    adopt_seed_papers(session)

    if not skip_discovery:
        backend = search_backend or EuropePmcBackend()
        try:
            discover(session, backend, limits, report)
        finally:
            if search_backend is None and isinstance(backend, EuropePmcBackend):
                backend.close()

    ft_backend = fulltext_backend or EuropePmcFullTextBackend()
    try:
        acquire_and_extract(session, ft_backend, limits, report)
    finally:
        if fulltext_backend is None and isinstance(ft_backend, EuropePmcFullTextBackend):
            ft_backend.close()

    report.paper_states = state_counts(session)
    report.finished_at = datetime.now(UTC).isoformat()
    return report


def backlog(session: Session) -> dict[str, list[dict[str, Any]]]:
    """What is waiting, grouped by the reason it is waiting."""
    return {
        "actionable": actionable_papers(session),
        "review_required": papers_in_states(session, [PaperState.REVIEW_REQUIRED]),
        "inaccessible": papers_in_states(session, [PaperState.INACCESSIBLE]),
    }
