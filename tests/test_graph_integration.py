"""End-to-end checks against a live Neo4j.

Skipped when no database is reachable, so the unit suite still runs anywhere.
Run them with the stack up:

    docker compose up -d
    pytest tests/test_graph_integration.py

These exist because the properties that matter most here are properties of the
*graph*, not of any function: that a reload does not duplicate, that it does not
trample a human's review decision, and that a refuted association does not come
back out of a query looking like a supported one. None of that is observable
without a server.

The module ingests into whatever database `.env` points at and leaves the seed
data loaded. Point it at a scratch instance if that is not what you want.
"""

from __future__ import annotations

import pytest

from medaka_ontology.db import Neo4jUnavailableError, install_schema, session_scope
from medaka_ontology.dossier import render_trait
from medaka_ontology.ingest import ingest_bundle
from medaka_ontology.loader import load_dir
from medaka_ontology.models import entity_id
from medaka_ontology.queries import (
    disputed_claims,
    mechanisms_via_genes,
    review_queue,
    shared_genes,
)
from medaka_ontology.vocabulary import NodeLabel


@pytest.fixture(scope="module")
def session():
    try:
        with session_scope() as s:
            yield s
    except Neo4jUnavailableError as exc:
        pytest.skip(f"no Neo4j: {exc}")


@pytest.fixture(scope="module")
def loaded(session):
    """A graph built from scratch, so counts are deterministic."""
    session.run("MATCH (n) DETACH DELETE n")
    install_schema(session)
    bundle = load_dir()
    report = ingest_bundle(session, bundle)
    return report


def _counts(session) -> tuple[int, int]:
    nodes = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
    rels = session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
    return nodes, rels


def test_ingest_writes_the_whole_bundle(loaded):
    assert (loaded.papers, loaded.entities, loaded.claims) == (27, 146, 152)


def test_evidence_is_deduplicated_across_claims(session, loaded):
    """A finding cited on two claims is one node with two edges, which is what
    makes 'what did this paper contribute?' answerable."""
    nodes = session.run("MATCH (e:Evidence) RETURN count(e) AS n").single()["n"]
    edges = session.run(
        "MATCH (:Evidence)-[r:SUPPORTS|CONTRADICTS]->(:Claim) RETURN count(r) AS n"
    ).single()["n"]
    assert edges == loaded.evidence
    assert nodes < edges, "no evidence was shared; dedup is not being exercised"


def test_reload_is_idempotent(session, loaded):
    before = _counts(session)
    ingest_bundle(session, load_dir())
    assert _counts(session) == before


def test_reload_does_not_trample_a_human_review_decision(session, loaded):
    """PRD §12. The single most damaging regression this code could have: a
    scheduled re-run silently undoing a reviewer's work."""
    claim_id = session.run(
        "MATCH (c:Claim)-[:SUBJECT]->(:OrnamentalTrait {name:'daruma'}) "
        "WHERE c.predicate = 'associated_with_gene' RETURN c.id AS id"
    ).single()["id"]
    session.run(
        "MATCH (c:Claim {id:$id}) SET c.review_status='REJECTED', c.review_note=$n",
        id=claim_id,
        n="checked the printed reference list",
    )

    ingest_bundle(session, load_dir())

    row = session.run(
        "MATCH (c:Claim {id:$id}) RETURN c.review_status AS st, c.review_note AS note",
        id=claim_id,
    ).single()
    assert row["st"] == "REJECTED"
    assert row["note"] == "checked the printed reference list"


def test_seed_content_is_rewritten_on_reload(session, loaded):
    """The other half of the ownership boundary: claim *content* belongs to the
    seed files, so an edit made in the browser is expected to be overwritten.
    Asserted so the asymmetry is deliberate rather than accidental."""
    claim_id = session.run(
        "MATCH (c:Claim)-[:SUBJECT]->(:OrnamentalTrait {name:'orochi'}) "
        "WHERE c.predicate = 'associated_with_gene' RETURN c.id AS id"
    ).single()["id"]
    session.run(
        "MATCH (c:Claim {id:$id}) SET c.interpretation='scribbled in the browser'",
        id=claim_id,
    )
    ingest_bundle(session, load_dir())
    interp = session.run(
        "MATCH (c:Claim {id:$id}) RETURN c.interpretation AS i", id=claim_id
    ).single()["i"]
    assert interp != "scribbled in the browser"


def test_contradictions_are_stored_as_edges_not_resolved(session, loaded):
    """PRD §9. panda carries three mutually incompatible attributions and all of
    them must still be in the graph."""
    rows = {(r["subject"], r["object"]) for r in disputed_claims(session)}
    assert ("panda", "slc24a5") in rows
    assert ("panda", "pnp4a") in rows
    assert ("daruma", "wnt4b") in rows


def test_review_queue_puts_contradicted_claims_first(session, loaded):
    rows = review_queue(session)
    assert rows
    assert rows[0]["contradicts"] >= rows[-1]["contradicts"]


def test_shared_genes_excludes_subsumption_pairs(session, loaded):
    """YWKo subsumes yellow, so their shared slc45a2 is an artefact of overlapping
    case sets, not a biological finding."""
    pairs = {(r["trait_a"], r["trait_b"]) for r in shared_genes(session)}
    assert ("YWKo", "yellow") not in pairs
    assert ("blackrim", "yellow") in pairs, "unrelated pairs should still appear"


def test_shared_genes_flags_contested_links(session, loaded):
    """daruma-wnt4b is refuted by the seed paper's own text; the pair may be
    listed, but never as though it were settled."""
    rows = {(r["trait_a"], r["trait_b"]): r for r in shared_genes(session)}
    assert rows[("daruma", "fused centrum")]["contested"] is True
    assert rows[("hirenaga", "swallow")]["contested"] is False


def test_mechanism_is_reachable_two_hops_out(session, loaded):
    """PRD §13 puts Mechanism on the dossier, but no claim connects a trait to a
    mechanism directly."""
    rows = {
        r["mechanism"]: r
        for r in mechanisms_via_genes(
            session, entity_id(NodeLabel.ORNAMENTAL_TRAIT, "hikari")
        )
    }
    assert "dorsoventral patterning" in rows
    assert rows["dorsoventral patterning"]["strongest_link"] == "CAUSAL_VARIANT"


def test_mechanism_carries_the_weakness_of_the_link_it_came_through(session, loaded):
    """hirenaga reaches the same kind of statement through a candidate gene inside
    a 92-gene interval. The dossier must not present the two alike."""
    rows = mechanisms_via_genes(
        session, entity_id(NodeLabel.ORNAMENTAL_TRAIT, "hirenaga")
    )
    assert rows
    assert all(r["strongest_link"] != "CAUSAL_VARIANT" for r in rows)


def test_panda_dossier_surfaces_every_conflict(session, loaded):
    text = render_trait(session, "panda")
    assert "slc24a5" in text and "pnp4a" in text
    assert text.count("**Contradicted**") >= 3
    assert "No causal or functionally validated variant" in text


def test_hikari_dossier_reports_its_causal_variant(session, loaded):
    text = render_trait(session, "hikari")
    assert "CAUSAL_VARIANT" in text
    assert "zic1" in text and "zic4" in text
    assert "10.1016/j.cub.2012.01.063" in text, "provenance must reach the dossier"


def test_every_trait_renders(session, loaded):
    """A dossier that raises on some trait is a dossier nobody can trust to
    batch-render."""
    names = [
        r["name"]
        for r in session.run("MATCH (t:OrnamentalTrait) RETURN t.name AS name")
    ]
    assert len(names) == 42
    for name in names:
        assert render_trait(session, name).startswith("# ")
