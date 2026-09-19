"""Write a seed bundle into Neo4j, idempotently.

Two rules shape everything here.

PRD §9 -- nothing is overwritten. Re-ingesting a paper adds evidence edges; it
never mutates or removes a claim. A contradicting finding becomes a
`CONTRADICTS` edge alongside the existing `SUPPORTS` edges.

PRD §12 -- a human decision outranks the loader. Once someone sets a claim's
`review_status` to ACCEPTED or REJECTED, later runs leave it alone. Only
`ON CREATE` touches review state.

Which follows from a boundary worth stating plainly, because getting it wrong
loses someone's work:

- **The seed files own claim content.** `interpretation`, `predicate`, evidence
  and every entity property are rewritten from YAML on each run. Editing them in
  the Neo4j browser is editing a cache; the next `load` overwrites it.
- **The graph owns review state.** `review_status` and `review_note` are never
  written here after creation, so annotations made while reviewing survive
  reloading. `review_note` exists for exactly that: somewhere to write
  "checked the printed reference list, the citation really is broken" without
  it being clobbered.

Anything that should outlive a reload and is *not* review state belongs in the
seed files, not in the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from neo4j import Session

from .models import PIPELINE_VERSION, Claim, Entity, Paper, SeedBundle
from .vocabulary import NodeLabel, ReviewStatus, Stance

#: Fields handled explicitly by the Cypher below rather than copied as properties.
_ENTITY_SKIP = {"label", "review_status", "review_reasons"}
_PAPER_SKIP = {"key", "review_reasons"}


def _scalar(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_scalar(v) for v in value]
    return value


def _props(model: Any, skip: set[str]) -> dict[str, Any]:
    """Pydantic model to Neo4j property map.

    `None` is dropped rather than written: in Neo4j setting a property to null
    deletes it, so a later partial record would silently erase a field an earlier,
    richer record had filled in.
    """
    out: dict[str, Any] = {}
    for name, value in model.model_dump().items():
        if name in skip or value is None:
            continue
        out[name] = _scalar(value)
    return out


@dataclass
class IngestReport:
    """What one run did. PRD §11 calls for a run report."""

    papers: int = 0
    entities: int = 0
    claims: int = 0
    evidence: int = 0
    disputed_claims: list[str] = field(default_factory=list)
    pending_review: int = 0

_MERGE_PAPER = """
MERGE (p:Paper {id: $id})
ON CREATE SET p.created_at = $now, p.review_reasons = $review_reasons
SET p += $props, p.updated_at = $now
RETURN p.id AS id
"""

_MERGE_ENTITY = """
MERGE (n:%(label)s {id: $id})
ON CREATE SET n.created_at = $now,
              n.review_status = $review_status,
              n.review_reasons = $review_reasons
SET n += $props, n.updated_at = $now
RETURN n.id AS id
"""

# The claim itself plus its two endpoint edges. `review_status` is written only
# ON CREATE so a human ACCEPT survives every later run.
_MERGE_CLAIM = """
MATCH (s:%(subject_label)s {id: $subject_id})
MATCH (o:%(object_label)s {id: $object_id})
MERGE (c:Claim {id: $id})
ON CREATE SET c.created_at = $now, c.review_status = $review_status
SET c.predicate = $predicate,
    c.subject_id = $subject_id,
    c.object_id = $object_id,
    c.review_reasons = $review_reasons,
    c.updated_at = $now
%(interpretation)s
MERGE (c)-[:SUBJECT]->(s)
MERGE (c)-[:OBJECT]->(o)
RETURN c.id AS id
"""

_MERGE_EVIDENCE = """
MATCH (c:Claim {id: $claim_id})
MATCH (p:Paper {id: $paper_id})
MERGE (e:Evidence {id: $id})
ON CREATE SET e.created_at = $now
SET e += $props, e.updated_at = $now
MERGE (e)-[:FROM_PAPER]->(p)
MERGE (e)-[r:%(stance)s]->(c)
SET r.level = $level
RETURN e.id AS id
"""

# Strain is created on demand: seed files name the population a finding came from
# without necessarily defining it as a first-class entity yet.
_LINK_STRAIN = """
MATCH (e:Evidence {id: $evidence_id})
MERGE (s:Strain {id: $strain_id})
ON CREATE SET s.name = $strain_name,
              s.created_at = $now,
              s.review_status = $review_status
MERGE (e)-[:STUDIED_IN]->(s)
"""


def _now() -> datetime:
    return datetime.now(UTC)


def ingest_paper(session: Session, paper: Paper, now: datetime) -> str:
    session.run(
        _MERGE_PAPER,
        id=paper.id,
        props=_props(paper, _PAPER_SKIP),
        review_reasons=[r.value for r in paper.review_reasons],
        now=now,
    )
    return paper.id


def ingest_entity(session: Session, entity: Entity, now: datetime) -> str:
    session.run(
        _MERGE_ENTITY % {"label": entity.label.value},
        id=entity.id,
        props=_props(entity, _ENTITY_SKIP),
        review_status=entity.review_status.value,
        review_reasons=[r.value for r in entity.review_reasons],
        now=now,
    )
    return entity.id


def ingest_claim(
    session: Session, claim: Claim, paper_ids: dict[str, str], now: datetime
) -> int:
    """Write one claim and all of its evidence. Returns the evidence count."""
    # Only set interpretation when we have one, so re-ingesting a bare claim does
    # not blank an interpretation written by a richer earlier record.
    interpretation_clause = (
        "SET c.interpretation = $interpretation" if claim.interpretation else ""
    )
    session.run(
        _MERGE_CLAIM
        % {
            "subject_label": claim.subject.label.value,
            "object_label": claim.object.label.value,
            "interpretation": interpretation_clause,
        },
        id=claim.id,
        subject_id=claim.subject.id,
        object_id=claim.object.id,
        predicate=claim.predicate.value,
        interpretation=claim.interpretation,
        review_status=claim.review_status.value,
        review_reasons=[r.value for r in claim.derived_review_reasons()],
        now=now,
    )

    written = 0
    for ev in claim.evidence:
        paper_id = paper_ids[ev.paper]
        ev_id = ev.id_for(paper_id)
        props = _props(ev, skip={"paper", "stance", "review_reasons"})
        props["review_reasons"] = [r.value for r in ev.review_reasons]
        session.run(
            _MERGE_EVIDENCE % {"stance": ev.stance.value},
            id=ev_id,
            claim_id=claim.id,
            paper_id=paper_id,
            props=props,
            level=ev.level.value,
            now=now,
        )
        if ev.strain:
            from .models import entity_id  # local import keeps module import cheap

            session.run(
                _LINK_STRAIN,
                evidence_id=ev_id,
                strain_id=entity_id(NodeLabel.STRAIN, ev.strain),
                strain_name=ev.strain,
                review_status=ReviewStatus.PENDING.value,
                now=now,
            )
        written += 1
    return written


def ingest_bundle(session: Session, bundle: SeedBundle) -> IngestReport:
    now = _now()
    report = IngestReport()

    paper_ids: dict[str, str] = {}
    for paper in bundle.papers:
        paper_ids[paper.key] = ingest_paper(session, paper, now)
        report.papers += 1

    for entity in bundle.entities:
        ingest_entity(session, entity, now)
        report.entities += 1

    for claim in bundle.claims:
        report.evidence += ingest_claim(session, claim, paper_ids, now)
        report.claims += 1
        if claim.is_disputed:
            report.disputed_claims.append(
                f"{claim.subject.name} --{claim.predicate.value}--> {claim.object.name}"
            )

    record = session.run(
        "MATCH (c:Claim) WHERE c.review_status = $pending RETURN count(c) AS c",
        pending=ReviewStatus.PENDING.value,
    ).single()
    report.pending_review = record["c"] if record else 0
    return report


def mark_paper_processed(session: Session, paper_id: str) -> None:
    """PRD §11: do not reprocess the same paper.

    `pipeline_version` is stored alongside the timestamp so that bumping
    `PIPELINE_VERSION` re-opens every paper for extraction without anyone having
    to clear the field by hand.
    """
    session.run(
        "MATCH (p:Paper {id: $id}) "
        "SET p.processed_at = $now, p.pipeline_version = $version",
        id=paper_id,
        now=_now(),
        version=PIPELINE_VERSION,
    )


def unprocessed_papers(session: Session) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in session.run(
            "MATCH (p:Paper) "
            "WHERE p.processed_at IS NULL OR coalesce(p.pipeline_version, -1) < $version "
            "RETURN p.id AS id, p.title AS title, p.doi AS doi "
            "ORDER BY p.year DESC",
            version=PIPELINE_VERSION,
        )
    ]


__all__ = [
    "IngestReport",
    "Stance",
    "ingest_bundle",
    "mark_paper_processed",
    "unprocessed_papers",
]
