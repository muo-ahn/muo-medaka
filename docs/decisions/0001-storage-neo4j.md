# ADR 0001 — Neo4j as the source of truth

- **Status**: Accepted
- **Date**: 2026-09-19
- **Resolves**: PRD §13, "구체적인 storage technology는 초기 구현 전에 결정한다"

## Decision

The ontology is stored in a local **Neo4j 5 (community)** database, run via
`docker compose`. It is the single source of truth. YAML files under `data/seed/`
are *inputs* to an idempotent loader, not a parallel copy of the graph.

## Why

The PRD's central questions (§1) are all multi-hop traversals:
"다른 관상 형질이 동일한 gene / pathway / developmental mechanism을 공유하는가?"
is `trait → gene → mechanism ← gene ← trait` — a path query, not a join.
Entity resolution (§8) and query expansion from the existing graph (§15 Phase 3)
are likewise graph-shaped.

## The consequence we have to engineer around

Neo4j relationships **cannot be the target of another relationship**. But PRD §9
requires exactly that: one claim, supported by some papers and contradicted by
others, with nothing overwritten.

So relations are **reified as `:Claim` nodes**:

```text
(:OrnamentalTrait {name:"Hikari"})
        <-[:SUBJECT]- (:Claim {predicate:"caused_by_variant"}) -[:OBJECT]->
                                                     (:GeneticVariant {...})
                            ^                    ^
            [:SUPPORTS]-(:Evidence)   (:Evidence)-[:CONTRADICTS]
                             |
                      [:FROM_PAPER]->(:Paper {doi:...})
```

A `:Claim` is an *assertion someone could make*. It carries no truth value of its
own — its standing is the aggregate of the `:Evidence` attached to it. Adding a
contradicting paper adds an edge; it never mutates or deletes the claim.

This is the price of the graph model and it is paid deliberately: direct
`(:Trait)-[:CAUSED_BY]->(:Variant)` edges would be shorter to query and would
make §9 unimplementable.

## Rejected alternatives

- **Git + YAML as source of truth** — human review would be `git diff`, which fits
  §12 well, but every §1 question becomes an application-level graph walk over
  parsed files. Rejected for query shape, not for review ergonomics.
- **SQLite** — the reified-claim model is expressible (it is just tables), but the
  recursive traversals would be hand-written CTEs.
- **RDF/OWL** — best interoperability with GO/PATO/ZFA and the most correct answer
  in the long run. Rejected for now as too slow to iterate on while the trait
  vocabulary is still unstable. Revisit at PRD Phase 4; the reified-claim model
  maps onto RDF reification without a redesign, which is part of why it was chosen.

## Costs accepted

- Requires Docker running locally; there is no zero-infra path.
- Review is not `git diff`. `medaka review` (CLI) over `review_status` is the
  substitute, and it must be built, not assumed.
- Backups are a deliberate step: `medaka export` writes the whole graph to
  versioned JSONL under `data/export/` so the knowledge is not trapped in a
  container volume.
