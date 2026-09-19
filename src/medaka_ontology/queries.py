"""Read paths over the graph.

Kept apart from `dossier` so the Cypher is reusable and testable on its own: the
same `claims_about` result backs the markdown dossier, the review queue and any
future API.
"""

from __future__ import annotations

from typing import Any

from neo4j import Session

from .models import entity_id
from .vocabulary import EVIDENCE_RANK, EvidenceLevel, NodeLabel, ReviewStatus

#: Claims where the entity is the subject, with all evidence and its provenance.
_OUTBOUND = """
MATCH (c:Claim)-[:SUBJECT]->(n {id: $id})
MATCH (c)-[:OBJECT]->(o)
OPTIONAL MATCH (e:Evidence)-[r:SUPPORTS|CONTRADICTS]->(c)
OPTIONAL MATCH (e)-[:FROM_PAPER]->(p:Paper)
RETURN c.id             AS claim_id,
       c.predicate      AS predicate,
       c.interpretation AS interpretation,
       c.review_status  AS review_status,
       c.review_reasons AS review_reasons,
       head(labels(o))  AS object_label,
       o.name           AS object_name,
       o.chromosome     AS object_chromosome,
       o.start          AS object_start,
       o.end            AS object_end,
       o.n_cases        AS object_n_cases,
       o.best_p_value   AS object_best_p,
       o.n_genes_in_interval AS object_n_genes,
       collect(DISTINCT {
         stance:     type(r),
         level:      e.level,
         experiment: e.experiment_type,
         finding:    e.finding,
         quote:      e.quote,
         section:    e.section,
         paper_title: p.title,
         paper_doi:   p.doi,
         paper_pmid:  p.pmid,
         paper_year:  p.year
       }) AS evidence
ORDER BY predicate, object_name
"""

#: Claims where the entity is the object -- how the rest of the graph points at it.
_INBOUND = """
MATCH (c:Claim)-[:OBJECT]->(n {id: $id})
MATCH (c)-[:SUBJECT]->(s)
RETURN c.predicate     AS predicate,
       head(labels(s)) AS subject_label,
       s.name          AS subject_name,
       c.review_status AS review_status
ORDER BY predicate, subject_name
"""

_TRAIT = """
MATCH (t:OrnamentalTrait {id: $id})
RETURN t.id AS id, t.name AS name, t.japanese_name AS japanese_name,
       t.aliases AS aliases, t.unverified_labels AS unverified_labels,
       t.description AS description, t.category AS category,
       t.is_composite AS is_composite,
       t.review_status AS review_status, t.review_reasons AS review_reasons
"""

_LIST_TRAITS = """
MATCH (t:OrnamentalTrait)
OPTIONAL MATCH (c:Claim)-[:SUBJECT]->(t)
RETURN t.name AS name, t.category AS category, t.is_composite AS is_composite,
       count(DISTINCT c) AS claims
ORDER BY category, name
"""

#: PRD §12. Everything a human still has to look at, worst first.
_REVIEW_QUEUE = """
MATCH (c:Claim)
WHERE c.review_status = $status
MATCH (c)-[:SUBJECT]->(s)
MATCH (c)-[:OBJECT]->(o)
OPTIONAL MATCH (:Evidence)-[r:SUPPORTS|CONTRADICTS]->(c)
WITH c, s, o,
     count(CASE type(r) WHEN 'SUPPORTS' THEN 1 END)    AS supports,
     count(CASE type(r) WHEN 'CONTRADICTS' THEN 1 END) AS contradicts
RETURN c.id AS claim_id, c.predicate AS predicate,
       s.name AS subject, o.name AS object,
       c.review_reasons AS reasons,
       c.review_note AS note,
       supports, contradicts
ORDER BY contradicts DESC, size(c.review_reasons) DESC, subject
"""

#: Claims with evidence on both sides. PRD §9 -- these are kept, never resolved
#: by deletion.
_DISPUTED = """
MATCH (c:Claim)
MATCH (c)-[:SUBJECT]->(s)
MATCH (c)-[:OBJECT]->(o)
MATCH (:Evidence)-[:SUPPORTS]->(c)
MATCH (:Evidence)-[:CONTRADICTS]->(c)
RETURN DISTINCT c.id AS claim_id, c.predicate AS predicate,
       s.name AS subject, o.name AS object, c.review_reasons AS reasons
ORDER BY subject, predicate
"""

#: PRD §1: "서로 다른 관상 형질이 동일한 gene / pathway를 공유하는가?"
#:
#: Two filters, both load-bearing:
#:
#: 1. Pairs linked by subsumption are excluded. An umbrella class and its member
#:    share a locus by construction, not by biology.
#: 2. Both links must have at least one SUPPORTS edge. Without this, a *refuted*
#:    association still reads as a shared gene -- daruma and fused centrum would
#:    appear to share wnt4b, and panda and guanineless to share pnp4a, when in
#:    both cases the seed paper's own data reject the medaka side of the pair.
#:
#: Links that are merely *disputed* (support and contradiction both present) are
#: kept and flagged rather than dropped, since PRD §9 forbids resolving a conflict
#: by hiding it.
_SHARED_GENES = """
MATCH (c1:Claim)-[:SUBJECT]->(t1:OrnamentalTrait)
MATCH (c1)-[:OBJECT]->(g:Gene)<-[:OBJECT]-(c2:Claim)
MATCH (c2)-[:SUBJECT]->(t2:OrnamentalTrait)
WHERE t1.name < t2.name
  AND c1.predicate IN $gene_predicates
  AND c2.predicate IN $gene_predicates
  AND EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(c1) }
  AND EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(c2) }
  AND NOT EXISTS {
        MATCH (sub:Claim {predicate: 'subsumes'})-[:SUBJECT]->(a:OrnamentalTrait)
        MATCH (sub)-[:OBJECT]->(b:OrnamentalTrait)
        WHERE (a = t1 AND b = t2) OR (a = t2 AND b = t1)
      }
WITH t1, t2, g,
     EXISTS { MATCH (:Evidence)-[:CONTRADICTS]->(c1) }
       OR EXISTS { MATCH (:Evidence)-[:CONTRADICTS]->(c2) } AS contested
RETURN t1.name AS trait_a, t2.name AS trait_b,
       collect(DISTINCT g.name) AS shared_genes,
       any(x IN collect(contested) WHERE x) AS contested
ORDER BY trait_a, trait_b
"""

# PRD §13 puts "Mechanism" on the trait dossier, but a mechanism is two hops out:
# a trait associates with a gene, and the gene participates in the mechanism. The
# strength of the trait->gene hop is carried along, because a mechanism reached
# through a positional candidate is a guess about a guess and must not read the
# same as one reached through a causal variant.
_MECHANISMS_VIA_GENES = """
MATCH (tc:Claim)-[:SUBJECT]->(t {id: $id})
MATCH (tc)-[:OBJECT]->(g:Gene)
WHERE tc.predicate IN $gene_predicates
OPTIONAL MATCH (:Evidence)-[sup:SUPPORTS]->(tc)
WITH g, tc, collect(sup.level) AS trait_gene_levels
MATCH (mc:Claim {predicate: 'participates_in'})-[:SUBJECT]->(g)
MATCH (mc)-[:OBJECT]->(m:BiologicalMechanism)
WITH m, g.name AS gene, trait_gene_levels
RETURN m.name AS mechanism,
       collect(DISTINCT gene) AS via_genes,
       collect(trait_gene_levels) AS link_levels
ORDER BY mechanism
"""

_SEARCH = """
CALL db.index.fulltext.queryNodes('entity_search', $q) YIELD node, score
RETURN head(labels(node)) AS label, node.name AS name, node.id AS id, score
ORDER BY score DESC
LIMIT $limit
"""

GENE_PREDICATES = ["associated_with_gene", "caused_by_variant", "modified_by"]


def _rows(session: Session, cypher: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(record) for record in session.run(cypher, **params)]


def get_trait(session: Session, name: str) -> dict[str, Any] | None:
    rows = _rows(session, _TRAIT, id=entity_id(NodeLabel.ORNAMENTAL_TRAIT, name))
    return rows[0] if rows else None


def claims_about(session: Session, node_id: str) -> list[dict[str, Any]]:
    rows = _rows(session, _OUTBOUND, id=node_id)
    for row in rows:
        # A claim with no evidence rows still collects one all-null map; drop it so
        # callers can treat an empty list as "no evidence" without special cases.
        row["evidence"] = [e for e in row["evidence"] if e.get("stance")]
        row["evidence"].sort(
            key=lambda e: EVIDENCE_RANK.get(EvidenceLevel(e["level"]), 0), reverse=True
        )
    return rows


def claims_targeting(session: Session, node_id: str) -> list[dict[str, Any]]:
    return _rows(session, _INBOUND, id=node_id)


def list_traits(session: Session) -> list[dict[str, Any]]:
    return _rows(session, _LIST_TRAITS)


def mechanisms_via_genes(session: Session, node_id: str) -> list[dict[str, Any]]:
    """Mechanisms reachable through the entity's associated genes.

    Each row reports the strongest trait-gene evidence behind it, flattened from
    the per-claim lists the query returns, so the caller can say how much the
    mechanism link is worth.
    """
    rows = _rows(session, _MECHANISMS_VIA_GENES, id=node_id, gene_predicates=GENE_PREDICATES)
    for row in rows:
        levels = [lvl for group in row.pop("link_levels") for lvl in group if lvl]
        row["strongest_link"] = (
            max(levels, key=lambda x: EVIDENCE_RANK.get(EvidenceLevel(x), 0))
            if levels
            else EvidenceLevel.UNKNOWN.value
        )
    return rows


def review_queue(
    session: Session, status: ReviewStatus = ReviewStatus.PENDING
) -> list[dict[str, Any]]:
    return _rows(session, _REVIEW_QUEUE, status=status.value)


def disputed_claims(session: Session) -> list[dict[str, Any]]:
    return _rows(session, _DISPUTED)


def shared_genes(session: Session) -> list[dict[str, Any]]:
    return _rows(session, _SHARED_GENES, gene_predicates=GENE_PREDICATES)


def search(session: Session, q: str, limit: int = 20) -> list[dict[str, Any]]:
    return _rows(session, _SEARCH, q=q, limit=limit)
