"""Neo4j connection handling and schema installation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from neo4j import Driver, GraphDatabase, NotificationDisabledClassification, Session

from .config import Settings, get_settings
from .vocabulary import ENTITY_LABELS, NodeLabel

#: Uniqueness constraints. Each also creates a backing index, so these double as
#: the lookup path for every MERGE in `ingest`.
CONSTRAINTS: tuple[str, ...] = tuple(
    f"CREATE CONSTRAINT {label.value.lower()}_id IF NOT EXISTS "
    f"FOR (n:{label.value}) REQUIRE n.id IS UNIQUE"
    for label in (
        *sorted(ENTITY_LABELS, key=lambda x: x.value),
        NodeLabel.PAPER,
        NodeLabel.EVIDENCE,
        NodeLabel.CLAIM,
    )
) + (
    # A DOI identifies a paper globally; two seed files must not be able to create
    # two nodes for it. PRD §11 relies on this to avoid reprocessing.
    "CREATE CONSTRAINT paper_doi IF NOT EXISTS "
    "FOR (n:Paper) REQUIRE n.doi IS UNIQUE",
)

#: Lookup indexes for the query paths the dossier and review commands actually use.
INDEXES: tuple[str, ...] = (
    "CREATE INDEX trait_name IF NOT EXISTS FOR (n:OrnamentalTrait) ON (n.name)",
    "CREATE INDEX gene_name IF NOT EXISTS FOR (n:Gene) ON (n.name)",
    "CREATE INDEX claim_predicate IF NOT EXISTS FOR (n:Claim) ON (n.predicate)",
    "CREATE INDEX claim_review IF NOT EXISTS FOR (n:Claim) ON (n.review_status)",
    "CREATE INDEX evidence_level IF NOT EXISTS FOR (n:Evidence) ON (n.level)",
    "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS "
    "FOR (n:OrnamentalTrait|Phenotype|Gene|Strain) ON EACH [n.name, n.aliases]",
)


class Neo4jUnavailableError(RuntimeError):
    """Raised with an actionable message when the database cannot be reached."""


def make_driver(settings: Settings | None = None) -> Driver:
    settings = settings or get_settings()
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        # Several read paths ask for optional properties -- `japanese_name` is
        # set only when a source actually attests one, so on a fresh graph no
        # node carries it. Neo4j reports each such read as an UNRECOGNIZED
        # notification, which buries real output under warnings about a field
        # that is *designed* to be usually absent. Other classifications
        # (deprecation, performance, security) are left on.
        notifications_disabled_classifications=[
            NotificationDisabledClassification.UNRECOGNIZED
        ],
    )


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    """Yield a session, converting connection failures into a message that says
    what to do about them."""
    settings = settings or get_settings()
    driver = make_driver(settings)
    try:
        driver.verify_connectivity()
    except Exception as exc:
        driver.close()
        raise Neo4jUnavailableError(
            f"cannot reach Neo4j at {settings.neo4j_uri}: {exc}\n"
            "Start it with:  docker compose up -d"
        ) from exc
    try:
        with driver.session(database=settings.neo4j_database) as session:
            yield session
    finally:
        driver.close()


def install_schema(session: Session) -> list[str]:
    """Create constraints and indexes. Idempotent."""
    applied: list[str] = []
    for statement in (*CONSTRAINTS, *INDEXES):
        session.run(statement)
        applied.append(statement.split(" IF NOT EXISTS")[0])
    return applied


def graph_counts(session: Session) -> dict[str, int]:
    """Node counts per label, for run reports. PRD §11."""
    labels = [
        *sorted(x.value for x in ENTITY_LABELS),
        NodeLabel.PAPER.value,
        NodeLabel.EVIDENCE.value,
        NodeLabel.CLAIM.value,
    ]
    counts: dict[str, int] = {}
    for label in labels:
        record = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
        if record and record["c"]:
            counts[label] = record["c"]
    return counts

