# Medaka Ornamental Trait Ontology

An evidence-backed knowledge base of ornamental medaka (*Oryzias latipes*) traits
and their genetic background. Built to answer, with sources attached:

- which gene, locus or variant is associated with a given ornamental trait
- **how well** that association is actually established
- which traits share a gene, pathway or developmental mechanism
- how breeder terminology maps onto laboratory mutant names

It is a knowledge layer, not a breeding tool. Mating recommendation, cross
simulation, pedigree management and phenotype prediction are explicit non-goals
(see [the PRD](Medaka%20Ornamental%20Trait%20Ontology%20%E2%80%94%20Rough%20PRD.md), §14).
The one exception is a validation query over the genetic layer, described
[below](#the-genetic-layer), which exists to test the data and lifts nothing.

**The ontology has no language restriction.** Names may be English, Japanese,
Korean or any other language, mixed freely in one graph and on one entity. For
strains and traits from the trade the Japanese original is the reference, and
renderings in other languages sit beside it as synonyms
([ADR 0005](docs/decisions/0005-multilingual-labels.md)).

## The shape of the graph

The design question that drives everything: one claim must be able to carry
evidence for *and* against it, with nothing overwritten. Neo4j relationships
cannot be the target of another relationship, so relations are reified as
`:Claim` nodes.

```
(:OrnamentalTrait {name:"panda"})
        <-[:SUBJECT]- (:Claim {predicate:"associated_with_gene"}) -[:OBJECT]-> (:Gene {name:"slc24a5"})
                             ↑                        ↑
              [:SUPPORTS]-(:Evidence)      (:Evidence)-[:CONTRADICTS]
                                 └─[:FROM_PAPER]→ (:Paper {doi:…})
```

A `:Claim` carries no truth value. Its standing is whatever the attached evidence
adds up to, which is what lets a contradicting paper be recorded as an extra edge
rather than an edit. See [ADR 0001](docs/decisions/0001-storage-neo4j.md).

Two further rules are enforced in code rather than left to discipline:

- **The relation vocabulary is closed**, with a declared domain and range per
  predicate ([`vocabulary.py`](src/medaka_ontology/vocabulary.py)). A human
  phenotype cannot be attached to a medaka gene, because no predicate accepts
  that shape.
- **Comparative evidence is capped.** A zebrafish knockout is functional
  validation of the zebrafish gene; on a medaka trait-gene claim it is an
  argument from homology, and the loader refuses to record it above
  `OBSERVATIONAL`.

## Quick start

```bash
docker compose up -d
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env
```

```bash
.venv/Scripts/python -m medaka_ontology.cli validate
```

```bash
.venv/Scripts/python -m medaka_ontology.cli load
```

```bash
.venv/Scripts/python -m medaka_ontology.cli dossier hikari
```

| Command | What it does |
|---|---|
| `validate` | Parse and cross-check the seed YAML. No database needed. |
| `init` | Create Neo4j constraints and indexes. Idempotent. |
| `load` | Validate and ingest. Safe to re-run; never overwrites a human review decision. |
| `status` | Node counts and the unprocessed-paper backlog. |
| `traits` | Every ornamental trait with its claim count. |
| `dossier <name>` | The human-readable trait dossier (PRD §13). |
| `dossier-all` | One dossier per trait, into `data/dossier/`. |
| `review` | The human-review queue (PRD §12). |
| `disputed` | Claims with evidence on both sides (PRD §9). |
| `shared-genes` | Trait pairs sharing a gene, excluding pairs related by subsumption. |
| `search <q>` | Full-text over entity names and aliases. |
| `export` | Dump the whole graph to JSONL under `data/export/`. |
| `queries` | The literature queries the current ontology generates. |
| `pipeline` | One discovery cycle: search, acquire, extract, stage for review. |
| `papers` | The paper registry, by processing state. |
| `candidates` | Staged proposals awaiting a decision. |
| `accept <id> --level X` / `reject <id>` | Decide one candidate. |
| `proposed-genes` | Gene symbols seen but not in the ontology. |
| `cross --mother "b/b r/r" --father "b/b r/R"` | Offspring of a cross from the genetic layer, by sex, with the weakest evidence under each trait. No database needed. |

The Neo4j browser is at <http://localhost:7474> (user `neo4j`, password from
`.env`).

## The discovery loop

```bash
.venv/Scripts/python -m medaka_ontology.cli pipeline --max-queries 10 --max-papers 12
```

The queries are built from the graph, so the ontology expands its own search as
it grows. Each trait produces a ladder — trait names and aliases, the laboratory
mutants it is identified with, the genes those claims point at, the mechanisms
those genes participate in — and the mechanism rung is deliberately *not* scoped
to medaka, because the papers that settle a trait's genetics are often not
ornamental-medaka papers at all. Expanding `hikari → Da mutant → zic1 →
dorsoventral patterning` is what reaches the original Da linkage-mapping paper
and the zic1 somite literature, none of which the seed contains.

**A run writes nothing into the ontology.** Everything lands in a candidate
queue:

```bash
.venv/Scripts/python -m medaka_ontology.cli candidates
.venv/Scripts/python -m medaka_ontology.cli accept cand:abc123 --level OBSERVATIONAL
```

Extraction finds sentences where two known entities are named together and
offers the verbatim quote. It does not read the sentence, and the evidence level
it suggests from cue phrases carries no authority — you assign the real one when
you accept. [ADR 0002](docs/decisions/0002-extraction-proposes-never-asserts.md)
explains why it stops there, and what that costs.

Papers carry a processing state (`medaka papers`) so a scheduled run never
rediscovers or reprocesses what it already handled, and so a paywalled paper is
recorded as `INACCESSIBLE` with a reason rather than silently missing.

### Following citations instead of keywords

```bash
# measure first: no Neo4j, nothing written, counts after each filter step
.venv/Scripts/python -m medaka_ontology.cli pipeline --from-citations --seed-pmid 24803434 --dry-run
# then run it: register, acquire, extract, stage, as a keyword run does
.venv/Scripts/python -m medaka_ontology.cli pipeline --from-citations --direction both --limit 20
```

`--from-citations` replaces the keyword queries with Europe PMC citation links
from seed papers (every seed paper with a PMID, unless `--seed-pmid` names some).
`forward` is papers citing the seed, `backward` the seed's own references. The
screen deduplicates (a preprint and its published record are one paper), drops
what the seed or registry already holds, and keeps only papers whose title *or
abstract* names medaka or Oryzias. Everything after is the ordinary pipeline, and
each paper's `discovered_via` reads `citation:<direction>:<seed pmid>`.

Use it when a trait's literature is already anchored by a paper someone has read
and you want what built on it: sibling loci from the same lab, and follow-up
functional work that the ontology's own vocabulary would not search for.
Keyword discovery stays the tool for traits that have no anchoring paper yet.
Expect a low yield — [the measurement](docs/research/enrich-yield-2026-09.md)
found 4 claim-changing papers in 106 citers of three seeds — so run the dry run
first and read its counts.

## Who owns what

Getting this boundary wrong loses someone's work, so it is enforced in `ingest`
and asserted in the integration tests:

- **The seed files own claim content.** `interpretation`, `predicate`, evidence
  and every entity property are rewritten from YAML on each `load`. Editing them
  in the Neo4j browser is editing a cache.
- **The graph owns review state.** `review_status` and `review_note` are written
  only on creation, so a reviewer's decision and notes survive every reload.

Anything that must outlive a reload and is not review state belongs in
`data/seed/`.

## Tests

```bash
.venv/Scripts/python -m pytest
```

The unit suite runs anywhere. `tests/test_graph_integration.py` needs a live
Neo4j and skips without one; it wipes and rebuilds the graph, so point `.env` at
a scratch instance if that is not what you want. It covers the properties that
only exist at the graph level: reload idempotency, that a reload does not trample
a human review decision, that contradictions survive as edges, and that a refuted
association never comes back out of a query looking settled.

## What is in the seed data

Phase 1 of the PRD: the ornamental traits and candidate loci defined by

> Kon T. *et al.* (2026) Genomic consequences of domestication and the
> diversification of body coloration and morphology in ornamental medaka strains.
> *Mol Biol Evol* 43(2):msag021. doi:10.1093/molbev/msag021

plus the prior literature each trait traces back to. The extraction, with every
identifier and the caveats that came with it, is in
[docs/research/seed-gwas-kon-2026.md](docs/research/seed-gwas-kon-2026.md).

**Read this before using the genetics.** Of the seed paper's 26 trait-gene
assignments, exactly one is functionally validated (*adcy5* / orochi, by an
edited phenocopy). *zic1/zic4* / hikari is causal only by way of the Da mutant:
the earlier work was done in Da, and hikari links to it through
`putatively_same_as` (ADR 0003).
Everything else is a candidate gene inside a GWAS interval holding 30-318 genes,
and several rest on four to eight mutants. The dossiers say so on every trait;
the ontology is built to stop that caveat from getting lost.

Three source-level conflicts are preserved rather than resolved:

| Conflict | What happened |
|---|---|
| **panda** | The paper nominates *slc24a5*, then concludes in the same discussion that the real gene is an uncharacterised one in the interval. Its Table 1 cites *pnp4a*, which its own Results reject. A 2024 preprint names a *different* lab mutant "panda", caused by *mpv17*. Three genes, one name, no agreement. |
| **daruma → wnt4b** | Table 1 and Results of the same paper disagree. *wnt4b* is on chr16; the daruma peak is on chr4. The *wnt4b* work is about the *fused centrum* mutant, recorded here on that entity instead. |
| **albino → oca2** | Table 1 attributes this to a paper that does not appear in its own reference list. Kept at `UNKNOWN` with the defect stated. The documented medaka albino gene is *tyr*. |

## Naming

Trait identifiers are the **romanized** names, because that is what the source
prints. They are identifiers, not anybody's spelling.

Names are written as `labels`, in **any language, mixed freely** (English,
Japanese, Korean ...). Each label carries a BCP 47 language tag, a kind
(preferred, synonym, romanisation, variant), an optional kana reading, and its
source: a paper key and/or a row of the breeder-vocabulary survey in
`docs/research/`. The trade's Japanese name is the reference for a strain or trait
and other languages' renderings sit beside it as synonyms. A label with no source
is kept but marked `UNVERIFIED`, and its entity carries `UNVERIFIED_LABEL`, so
unsourced text never reads as sourced. `japanese_name`, `aliases` and
`unverified_labels` are derived from the labels for the read paths that predate
them ([ADR 0005](docs/decisions/0005-multilingual-labels.md)).

Breeder traits and laboratory mutants are separate entities joined by
`putatively_same_as`, never merged. `hikari` and the `Da mutant` share a lesion;
that they share a genetic background is a claim with evidence, not a naming fact
(PRD §8).

## The genetic layer

Beyond *which gene*, the seed records *how a trait is inherited*
([ADR 0006](docs/decisions/0006-genetic-layer.md)): the mode (recessive, dominant,
incompletely dominant, multilocus, sex-linked), the alleles of the classical loci
(b, r, i ...) and which is dominant, the alleles a trait requires, what is
sex-linked, what masks what, and which strains are combinations of which traits.
Each claim carries its paper and level. A conclusion we drew ourselves is marked
`INFERRED`, the lowest level, with the reasoning on the claim.

`cross` reads those claims and computes the offspring of two genotypes, or of two
parents known only by what they show (a range over the genotypes consistent with
it):

```bash
.venv/Scripts/python -m medaka_ontology.cli cross --symbols
.venv/Scripts/python -m medaka_ontology.cli cross --mother "b/b r/r" --father "b/b r/R"
.venv/Scripts/python -m medaka_ontology.cli cross --mother-shows yellow --father-shows blue
```

At the sex-linked r locus a male's two alleles are written X first, so `r/R` is
X^r Y^R. The output is exact fractions per sex, the weakest-evidence claim under
each predicted trait, every assumption made, and what it refuses to predict
(`orochi`: multilocus). **This is a validation query, not a breeding tool**: it
reproduces published crosses to show the layer is honest enough
([docs/research/cross-validation-2026-10.md](docs/research/cross-validation-2026-10.md)).
It recommends nothing, and whether to lift the PRD §14 non-goal is the owner's
decision.

## Layout

```
data/seed/        YAML source records, loaded into the graph
docs/research/    Literature extraction with full provenance
docs/decisions/   Architecture decision records
src/medaka_ontology/
  vocabulary.py   Closed enums: predicates, evidence levels, review reasons
  models.py       Typed records; invariants enforced once, here
  loader.py       Parse and cross-validate seed files before any write
  ingest.py       Idempotent upserts; human review decisions survive re-runs
  queries.py      Read paths over the graph
  dossier.py      Trait dossier rendering
  genetics.py     The cross query: offspring from the genetic layer, no database
tests/            Includes assertions about the seed data's honesty
```

## Status

Phase 1 (ontology bootstrap) and the discovery pipeline of PRD §7/§11 are in
place. What is not built: automatic entity resolution for genuinely new traits
(ADR 0002 explains why that is deliberate), and Phase 4 refinement — merging
duplicate entities, detecting contradictions across newly accepted evidence, and
correcting evidence levels in bulk.
