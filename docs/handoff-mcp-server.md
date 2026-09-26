# Handoff: putting this ontology in front of a model

Written 2026-09-26, at the end of the session that built the anatomy rung. The
next session can start from this file alone.

## The question this answers

Can a chatbot be attached, or is it enough to hand the repository to Claude as
RAG material, so that breeding takes less work?

**Both are possible, and the recommended shape is neither.** Build an MCP server
over a static export. The reasoning is below; it is not obvious and it is worth
reading before writing code.

## What already exists, so it is not rebuilt

| asset | what it is |
|---|---|
| `data/dossier/*.md` | 42 files, one per trait, already RAG-shaped: evidence level, source URL and finding text inline. Regenerate with `cli dossier-all` |
| `cli export` | dumps the whole graph to JSONL; a vintage is in `data/export/` |
| `cli` commands | `traits`, `dossier`, `shared-genes`, `search`, `disputed`, `proposed-genes`, `candidates`, `validate` — the useful queries already exist as code |
| `.claude/skills/trait-literature-search/` | the method: convergence rule, positional veto, the anatomy rung and its measurements |

Export shape, so no spelunking is needed:

```jsonl
{"labels": ["Paper"], "properties": {"year": 2026, "notes": "...", ...}}
{"start": "claim:749438147f838989", "type": "SUBJECT", "end": "trait:kurobuchi", "props": {}}
```

Node ids are readable and stable (`trait:kurobuchi`, `paper:doi:...`,
`claim:<hash>`, `ev:<hash>`).

## Why not a chatbot

The user already works inside Claude clients. A chatbot means owning a UI, a
retrieval layer and a model integration in order to arrive at something they
have. Build it only if the MCP server turns out to be insufficient in use.

## Why not plain RAG either

Dossiers search well, and uploading them to a Claude Project is genuinely worth
doing on day one — zero code, and it kills the cost of re-confirming what the
repository already knows.

But the questions that actually shorten breeding are computations, not text
lookups:

| question | RAG | needs |
|---|---|---|
| "what was the evidence for kagamirin again" | yes | — |
| "do these two traits share a gene" (i.e. is this combination blocked by pleiotropy) | no | graph traversal, `shared-genes` |
| "is this gene even on the trait's chromosome" | no | the positional veto, a comparison |
| "is my tank observation already in the literature" | no | compare against 30 phenotypes, then search |

The third is the most valuable one, because it is where this project has an
advantage over the literature: the *edar* candidate for kagamirin exists only
because a breeding observation was recorded as a phenotype before searching.

## The two constraints that are not negotiable

1. **PRD §8 must survive the interface.** Dossiers carry evidence badges, but a
   model summarising them will happily produce "kagamirin is caused by *edar*".
   It is a candidate resting on two converging phenotypes, not a cause. The
   evidence level must come back **inside the tool's structured response**, so
   it is mechanically present rather than requested in a prompt. A tool that
   returns prose has already lost this.

2. **PRD §14 forbids cross prediction.** "Shorten breeding" must not be
   implemented as "what do I get if I cross X with Y". What may legitimately be
   shortened: re-confirmation cost, judging which combinations pleiotropy makes
   inseparable, and telling a new observation from a known one.

## Suggested tool surface

Thin wrappers over what the CLI already does. Every response carries the
evidence level and the source, and says "candidate" where the graph says
candidate.

- `trait(name)` — the dossier for one trait, structured rather than rendered
- `search(text)` — full-text over entity names and aliases
- `shared_genes()` — traits reaching the same gene, with the level on each edge
- `check_position(trait, gene)` — the positional veto, stated with its own
  limitation (locations are chromosome-level, so two loci on one chromosome
  cannot be separated)
- `phenotypes_of(trait)` / `traits_with_phenotype(phenotype)` — the axis the
  anatomy rung expands through
- `disputed()` — claims with evidence on both sides, which is where a naive
  reader is most likely to be misled

Run it against the **static export**, not Neo4j. The graph currently lives only
in a dev container on one machine; a file-backed server needs no Docker and
works from the work PC too. Re-export is one command when the seed changes.

## Repository state as of this handoff

- Branch `phenotype-backfill`, commits `65f4474` and `3cc591e` pushed. Full
  suite **117 passed, 0 skipped** with Docker up; `ruff` clean; `validate` reports
  27 papers / 157 entities / 179 claims and 5 contradicting claims that
  pre-date this work.
- **PR #4 is blocked by a repository ruleset on `main` requiring signed
  commits** — not a merge conflict. Nothing in the stack lands until that is
  decided: bypass with `--admin`, set up SSH signing, or drop the rule. PR #5
  is `CLEAN` because its base is not `main`.
- The commit that was meant to carry the anatomy *vocabulary* rationale did not
  form; its files were swept into `3cc591e`, whose message describes only the
  rung. Nothing was lost — the reasoning is in
  `.claude/skills/trait-literature-search/SKILL.md` — but history is coarser
  than intended. Not worth rewriting a pushed branch to fix.
- Unrelated and still open: the plain-language orochi blog draft was never
  saved to `content/blog/ko/orochi-easy.md`.

## First move

Upload `data/dossier/*.md` to a Claude Project. It costs nothing and it will
show, in use, which of the tools above are actually wanted before any of them
are written.
