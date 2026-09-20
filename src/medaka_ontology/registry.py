"""Persistent processing state for every paper the pipeline has ever seen.

Issue #1 §2. Without this a scheduled run rediscovers the same literature every
time, re-fetches it, re-extracts it and re-queues it for review. The registry is
what makes the loop terminate.

Two rules govern every write here:

- **State never goes backwards.** A paper already ACCEPTED, REJECTED or
  EXTRACTED stays there when a later query rediscovers it. This is what protects
  the hand-curated seed papers from being reset to DISCOVERED the first time the
  expansion finds them again -- which it will, immediately, since the queries are
  built from the very claims those papers support.
- **Failure is a state, not an absence.** A paper whose full text cannot be had
  becomes INACCESSIBLE with a recorded reason, so the next run skips it and a
  human can see the size of the gap rather than wondering why coverage stalled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neo4j import Session

from .discovery import DiscoveredPaper
from .models import slugify
from .vocabulary import ACTIONABLE_PAPER_STATES, PaperState

#: Ordering used to decide whether an incoming state is an advance. Anything at
#: or below the paper's current position is ignored.
_STATE_RANK: dict[PaperState, int] = {
    PaperState.DISCOVERED: 0,
    PaperState.METADATA_RESOLVED: 1,
    PaperState.INACCESSIBLE: 2,
    PaperState.FULLTEXT_AVAILABLE: 3,
    PaperState.EXTRACTION_PENDING: 4,
    PaperState.EXTRACTED: 5,
    PaperState.REVIEW_REQUIRED: 6,
    PaperState.REJECTED: 7,
    PaperState.ACCEPTED: 8,
}


def paper_id_for(doi: str | None, pmid: str | None, pmcid: str | None) -> str:
    """The same identity rule the seed loader uses, so a discovered paper and a
    curated one collapse onto one node instead of racing each other."""
    if doi:
        return f"paper:doi:{doi.lower()}"
    if pmid:
        return f"paper:pmid:{pmid}"
    if pmcid:
        return f"paper:pmcid:{pmcid.lower()}"
    raise ValueError("a paper needs at least one identifier")


@dataclass
class RegistryReport:
    added: int = 0
    already_known: int = 0
    new_via_recorded: int = 0
    skipped_unidentifiable: int = 0
    added_papers: list[str] = field(default_factory=list)


_REGISTER = """
MERGE (p:Paper {id: $id})
ON CREATE SET p.created_at        = $now,
              p.processing_state  = $initial_state,
              p.discovered_at     = $now,
              // A list from the outset. Seeded as a bare string, the ON MATCH
              // append below concatenates characters instead of adding a route,
              // and the paper ends up claiming it was found via 'c', 'h', 'r'...
              p.discovered_via    = [$via],
              p.review_reasons    = [],
              p.title             = $title,
              p.doi               = $doi,
              p.pmid              = $pmid,
              p.pmcid             = $pmcid,
              p.year              = $year,
              p.journal           = $journal,
              p.authors           = $authors,
              p.abstract          = $abstract,
              p.open_access       = $open_access,
              p.has_fulltext_xml  = $has_fulltext_xml
ON MATCH SET  p.discovered_via    = CASE
                  WHEN $via IN coalesce(p.discovered_via, [])
                  THEN p.discovered_via
                  ELSE coalesce(p.discovered_via, []) + [$via] END,
              p.updated_at        = $now
RETURN p.id AS id,
       p.processing_state AS state,
       p.created_at = $now AS created,
       size(coalesce(p.discovered_via, [])) AS via_count
"""

#: Fill in metadata a curated seed record left blank, without ever clobbering a
#: value that is already there. Search results are convenient but the curated
#: entry is the one someone checked.
_BACKFILL = """
MATCH (p:Paper {id: $id})
SET p.title            = coalesce(p.title, $title),
    p.year             = coalesce(p.year, $year),
    p.journal          = coalesce(p.journal, $journal),
    p.abstract         = coalesce(p.abstract, $abstract),
    p.pmid             = coalesce(p.pmid, $pmid),
    p.pmcid            = coalesce(p.pmcid, $pmcid),
    p.open_access      = coalesce(p.open_access, $open_access),
    p.has_fulltext_xml = coalesce(p.has_fulltext_xml, $has_fulltext_xml),
    p.authors          = CASE WHEN size(coalesce(p.authors, [])) = 0
                              THEN $authors ELSE p.authors END
"""


def register_discovered(
    session: Session, papers: list[DiscoveredPaper]
) -> RegistryReport:
    """Record search hits, advancing nothing that is already further along."""
    report = RegistryReport()
    now = datetime.now(UTC)
    for paper in papers:
        try:
            pid = paper_id_for(paper.doi, paper.pmid, paper.pmcid)
        except ValueError:
            report.skipped_unidentifiable += 1
            continue

        record = session.run(
            _REGISTER,
            id=pid,
            now=now,
            initial_state=PaperState.DISCOVERED.value,
            via=paper.discovered_via,
            title=paper.title,
            doi=paper.doi,
            pmid=paper.pmid,
            pmcid=paper.pmcid,
            year=paper.year,
            journal=paper.journal,
            authors=paper.authors,
            abstract=paper.abstract,
            open_access=paper.is_open_access,
            has_fulltext_xml=paper.has_fulltext_xml,
        ).single()

        if record["created"]:
            report.added += 1
            report.added_papers.append(pid)
        else:
            report.already_known += 1
            session.run(
                _BACKFILL,
                id=pid,
                title=paper.title,
                year=paper.year,
                journal=paper.journal,
                abstract=paper.abstract,
                pmid=paper.pmid,
                pmcid=paper.pmcid,
                open_access=paper.is_open_access,
                has_fulltext_xml=paper.has_fulltext_xml,
                authors=paper.authors,
            )
            if record["via_count"] > 1:
                report.new_via_recorded += 1
    return report


def current_state(session: Session, paper_id: str) -> PaperState | None:
    record = session.run(
        "MATCH (p:Paper {id:$id}) RETURN p.processing_state AS s", id=paper_id
    ).single()
    if record is None or record["s"] is None:
        return None
    return PaperState(record["s"])


def advance_state(
    session: Session,
    paper_id: str,
    state: PaperState,
    reason: str | None = None,
    force: bool = False,
) -> bool:
    """Move a paper forward. Returns whether the write happened.

    Backwards moves are refused unless `force` is set, which exists for the one
    legitimate case: a paper that was INACCESSIBLE becoming open access later.
    """
    existing = current_state(session, paper_id)
    if existing is not None and not force:
        if _STATE_RANK[state] <= _STATE_RANK[existing]:
            return False
    session.run(
        "MATCH (p:Paper {id:$id}) "
        "SET p.processing_state = $state, p.state_reason = $reason, "
        "    p.state_changed_at = $now",
        id=paper_id,
        state=state.value,
        reason=reason,
        now=datetime.now(UTC),
    )
    return True


def papers_in_states(
    session: Session, states: list[PaperState], limit: int | None = None
) -> list[dict[str, Any]]:
    cypher = (
        "MATCH (p:Paper) WHERE p.processing_state IN $states "
        "RETURN p.id AS id, p.title AS title, p.doi AS doi, p.pmid AS pmid, "
        "       p.pmcid AS pmcid, p.processing_state AS state, "
        "       p.open_access AS open_access, p.has_fulltext_xml AS has_fulltext_xml, "
        "       p.abstract AS abstract, p.discovered_via AS discovered_via "
        "ORDER BY coalesce(p.year, 0) DESC"
    )
    if limit:
        cypher += f" LIMIT {int(limit)}"
    return [dict(r) for r in session.run(cypher, states=[s.value for s in states])]


def actionable_papers(session: Session, limit: int | None = None) -> list[dict[str, Any]]:
    return papers_in_states(session, sorted(ACTIONABLE_PAPER_STATES), limit=limit)


def state_counts(session: Session) -> dict[str, int]:
    return {
        r["state"]: r["n"]
        for r in session.run(
            "MATCH (p:Paper) "
            "RETURN coalesce(p.processing_state, 'UNTRACKED') AS state, count(*) AS n "
            "ORDER BY state"
        )
    }


def adopt_seed_papers(session: Session) -> int:
    """Give curated papers a state so discovery cannot reset them.

    Papers loaded from `data/seed/` were read and checked by a person, which is
    exactly what ACCEPTED means. Marking them is not bookkeeping: without it the
    first discovery run finds them again -- the queries are built from the claims
    they support -- and drags them back to DISCOVERED.
    """
    record = session.run(
        "MATCH (p:Paper) WHERE p.processing_state IS NULL "
        "SET p.processing_state = $state, p.state_reason = $reason, "
        "    p.state_changed_at = $now "
        "RETURN count(p) AS n",
        state=PaperState.ACCEPTED.value,
        reason="curated in data/seed",
        now=datetime.now(UTC),
    ).single()
    return record["n"] if record else 0


def fulltext_cache_name(paper_id: str) -> str:
    return f"{slugify(paper_id)}.xml"
