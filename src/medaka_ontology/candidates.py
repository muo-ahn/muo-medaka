"""Staging for extracted proposals, and the acceptance path into the ontology.

Issue #1 §7 and §8. Candidates live in the graph as `:Candidate` nodes but are
not part of it: nothing queries them as knowledge, no dossier renders them, and
`shared-genes` cannot see them. They become knowledge only when a person accepts
one.

Acceptance deliberately routes through `models.Claim` and `ingest.ingest_claim`
rather than writing Cypher of its own. That is the whole point: the closed
vocabulary, the required provenance and the comparative-evidence ceiling are
enforced on the way in, so an accepted candidate cannot enter the graph in a
shape that a hand-written seed file would have been rejected for. A second write
path would be a second set of rules, and the weaker one always wins eventually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neo4j import Session

from .extraction import CandidateClaim
from .ingest import ingest_claim
from .models import Claim, EntityRef, Evidence
from .resolution import ProposedGene, resolve
from .vocabulary import (
    CandidateStatus,
    EvidenceLevel,
    NodeLabel,
    Predicate,
    ReviewReason,
    Stance,
)

_STORE_CANDIDATE = """
MATCH (p:Paper {id: $paper_id})
MERGE (c:Candidate {id: $props.id})
ON CREATE SET c += $props,
              c.status = $pending,
              c.created_at = $now
ON MATCH SET  c.last_seen_at = $now
MERGE (c)-[:FROM_PAPER]->(p)
RETURN c.status AS status, c.created_at = $now AS created
"""

_STORE_PROPOSED_GENE = """
MATCH (p:Paper {id: $paper_id})
MERGE (g:ProposedEntity {id: $id})
ON CREATE SET g.symbol = $symbol,
              g.label = $label,
              g.quote = $quote,
              g.section = $section,
              g.near_entities = $near,
              g.status = $pending,
              g.created_at = $now
ON MATCH SET  g.last_seen_at = $now
MERGE (g)-[:FROM_PAPER]->(p)
RETURN g.created_at = $now AS created
"""

_PENDING = """
MATCH (c:Candidate)-[:FROM_PAPER]->(p:Paper)
WHERE c.status = $pending
RETURN c.id AS id, c.predicate AS predicate,
       c.subject_name AS subject, c.subject_label AS subject_label,
       c.object_name AS object, c.object_label AS object_label,
       c.suggested_level AS suggested_level, c.level_cue AS level_cue,
       c.species AS species, c.negated AS negated,
       c.quote AS quote, c.section AS section,
       c.review_reasons AS review_reasons,
       p.id AS paper_id, p.title AS paper_title, p.doi AS paper_doi
ORDER BY c.suggested_level, c.subject_name
"""

_GET_CANDIDATE = """
MATCH (c:Candidate {id: $id})-[:FROM_PAPER]->(p:Paper)
RETURN c AS c, p.id AS paper_id
"""

_SET_STATUS = """
MATCH (c:Candidate {id: $id})
SET c.status = $status, c.decided_at = $now, c.decision_note = $note
RETURN c.id AS id
"""


@dataclass
class CandidateReport:
    stored: int = 0
    already_present: int = 0
    proposed_genes: int = 0
    by_paper: dict[str, int] = field(default_factory=dict)


def store_candidates(
    session: Session, candidates: list[CandidateClaim]
) -> CandidateReport:
    report = CandidateReport()
    now = datetime.now(UTC)
    for candidate in candidates:
        record = session.run(
            _STORE_CANDIDATE,
            paper_id=candidate.paper_id,
            props=candidate.as_properties(),
            pending=CandidateStatus.PENDING.value,
            now=now,
        ).single()
        if record is None:
            continue
        if record["created"]:
            report.stored += 1
            report.by_paper[candidate.paper_id] = (
                report.by_paper.get(candidate.paper_id, 0) + 1
            )
        else:
            report.already_present += 1
    return report


def store_proposed_genes(session: Session, proposals: list[ProposedGene]) -> int:
    now = datetime.now(UTC)
    stored = 0
    for proposal in proposals:
        record = session.run(
            _STORE_PROPOSED_GENE,
            paper_id=proposal.paper_id,
            id=proposal.id,
            symbol=proposal.symbol,
            label=NodeLabel.GENE.value,
            quote=proposal.quote,
            section=proposal.section,
            near=proposal.near_entities,
            pending=CandidateStatus.PENDING.value,
            now=now,
        ).single()
        if record and record["created"]:
            stored += 1
    return stored


def pending_candidates(session: Session, limit: int | None = None) -> list[dict[str, Any]]:
    rows = [dict(r) for r in session.run(_PENDING, pending=CandidateStatus.PENDING.value)]
    return rows[:limit] if limit else rows


def pending_proposed_genes(session: Session) -> list[dict[str, Any]]:
    """Proposed gene symbols, each checked against the existing ontology.

    The resolution check is what stops a proposal being read as new when it is
    not. A symbol can already exist under a different label, or match an alias on
    an entity nobody expected -- and adding it as a fresh `Gene` would split one
    concept across two nodes, which PRD §8 exists to prevent. `AMBIGUOUS` here
    means "look before you add", not "reject".
    """
    rows = [
        dict(r)
        for r in session.run(
            "MATCH (g:ProposedEntity)-[:FROM_PAPER]->(p:Paper) WHERE g.status = $pending "
            "RETURN g.id AS id, g.symbol AS symbol, g.quote AS quote, "
            "       g.near_entities AS near_entities, p.title AS paper_title, "
            "       p.doi AS paper_doi ORDER BY g.symbol",
            pending=CandidateStatus.PENDING.value,
        )
    ]
    for row in rows:
        resolution = resolve(session, NodeLabel.GENE, row["symbol"])
        row["resolution"] = resolution.status.value
        row["collides_with"] = resolution.alternatives
    return rows


def candidate_counts(session: Session) -> dict[str, int]:
    return {
        r["status"]: r["n"]
        for r in session.run(
            "MATCH (c:Candidate) RETURN c.status AS status, count(*) AS n ORDER BY status"
        )
    }


class AcceptanceError(RuntimeError):
    """Raised when a candidate cannot become a claim."""


def accept_candidate(
    session: Session,
    candidate_id: str,
    level: EvidenceLevel,
    stance: Stance = Stance.SUPPORTS,
    note: str | None = None,
) -> str:
    """Turn one candidate into a real claim with evidence.

    The evidence level is supplied by the reviewer, not read off the candidate's
    suggestion. That is the point at which a human takes responsibility for the
    grade, and it is why `suggested_level` is never silently promoted.
    """
    record = session.run(_GET_CANDIDATE, id=candidate_id).single()
    if record is None:
        raise AcceptanceError(f"no candidate {candidate_id!r}")
    node = dict(record["c"])
    if node.get("status") != CandidateStatus.PENDING.value:
        raise AcceptanceError(
            f"candidate {candidate_id!r} is already {node.get('status')}"
        )

    paper_id = record["paper_id"]
    section = node.get("section")

    # The subject's species, so the comparative ceiling applies here exactly as
    # it does to a seed file. Without it a zebrafish or corn-snake result about a
    # medaka gene could be accepted at FUNCTIONAL_VALIDATION, which is the whole
    # thing the ceiling exists to stop.
    species_row = session.run(
        "MATCH (n {id: $id}) RETURN n.species AS species", id=node["subject_id"]
    ).single()
    subject_species = species_row["species"] if species_row else None

    # Built as a validated model, so the vocabulary shape check and the
    # comparative ceiling both apply before anything is written.
    try:
        claim = Claim(
            predicate=Predicate(node["predicate"]),
            subject=EntityRef(
                label=NodeLabel(node["subject_label"]), name=node["subject_name"]
            ),
            object=EntityRef(
                label=NodeLabel(node["object_label"]), name=node["object_name"]
            ),
            interpretation=note,
            subject_species=subject_species,
            evidence=[
                Evidence(
                    paper=paper_id,
                    experiment_type="co-mention extraction, reviewed",
                    finding=node["quote"],
                    quote=node["quote"],
                    section=section,
                    level=level,
                    stance=stance,
                    species=node.get("species") or "Oryzias latipes",
                    review_reasons=[ReviewReason.EVIDENCE_LEVEL_UNCLEAR]
                    if level is EvidenceLevel.UNKNOWN
                    else [],
                )
            ],
        )
    except ValueError as exc:
        raise AcceptanceError(str(exc)) from exc

    ingest_claim(session, claim, {paper_id: paper_id}, datetime.now(UTC))
    session.run(
        _SET_STATUS,
        id=candidate_id,
        status=CandidateStatus.ACCEPTED.value,
        now=datetime.now(UTC),
        note=note,
    )
    return claim.id


def reject_candidate(session: Session, candidate_id: str, note: str | None = None) -> None:
    record = session.run(
        _SET_STATUS,
        id=candidate_id,
        status=CandidateStatus.REJECTED.value,
        now=datetime.now(UTC),
        note=note,
    ).single()
    if record is None:
        raise AcceptanceError(f"no candidate {candidate_id!r}")
