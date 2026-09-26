---
name: trait-literature-search
description: >-
  Find and judge literature for an ornamental medaka trait in this ontology, and
  decide whether a gene may be recorded as its candidate. Use when asked to
  research a trait, look for papers on a trait or phenotype, chase a "this trait
  seems related to gene X" hunch, propose or evaluate a candidate gene, or work
  out why a trait has no gene yet. Also use before writing any
  associated_with_gene claim. Covers Europe PMC querying, the convergence rule,
  the positional veto, and the validation that keeps both honest.
triggers:
  - 논문 탐색
  - 형질 리서치
  - candidate gene
  - 후보 유전자
  - trait literature
  - 어떤 유전자와 연관
---

# Trait literature search and candidate judgement

Repo: `C:\Dev\muo-medaka`. Scripts referenced below live in `scripts/` next to
this file and run against `data/seed/*.yaml` — no database needed.

## What this skill is defending against

The failure this repo exists to prevent (PRD §8) is a gene name becoming folk
knowledge because one word appeared in two sentences. The defence is not
caution in prose. It is three mechanical checks, each measured against traits
whose answer is already known.

**Measured by leave-one-out on the traits with a known gene and at least one
phenotype — 10 eligible, 7 of which produced any nomination at all:**

| check | result |
|---|---|
| a single shared phenotype nominates the right gene | 3 of 12 (25%) |
| two or more phenotypes converge on one gene | never fires — 0 recall |
| positional veto (wrong chromosome) | kills 5 wrong, **0 correct** |

The clean counterexample: `albino` and `yellow` both carry *loss of
melanophores*, so each nominates the other's gene. Both nominations are wrong,
and both look exactly like a finding. **One phenotype is not evidence.**

## Procedure

### 0. Preflight the search backend — never skip

Europe PMC silently returns `hitCount=0` for queries it cannot parse. Several
OR-groups of `TITLE_ABS:"phrase"` AND-ed together is one such shape, and it
looks identical to a real negative result.

Run a known-positive control first:

```
DOI:"10.1093/molbev/msag021"    → must return exactly 1 (Kon et al. 2026)
```

If a query returns 0, re-run it in a simpler form before believing it. During
development, five queries returned 0 purely from syntax and would have been
reported as "no literature exists".

### 1. Decompose the trait into phenotypes

Read `data/dossier/<trait>.md` → `## Phenotypes`.

- **0 phenotypes → stop.** Backfill from the trait description (Table 1) first;
  there is nothing to search on. Three dossiers are deliberately empty
  (guanineless, leucophore free, panda (pa)) because their sources name a gene
  and never state a phenotype.
- **1 phenotype → expect to prove nothing.** Proceed, but a result here cannot
  clear the convergence bar on its own. Look for a second phenotype instead
  (see step 5).

### 2. Measure retrieval before building on a query

**Phenotype names in this ontology are our vocabulary, not the literature's.**
Searched as exact phrases scoped to medaka, **18 of 30 retrieved zero papers**
(measured 2026-09; the counts drift, so re-run the probe rather than trusting
this number), and most of the rest are noise (`hypomelanism` → anemonefish; `small pupil` →
human anophthalmia; `enlarged scale` → an olfactory receptor paper).

Run `scripts/probe_retrieval.py` before trusting a query strategy. What has
actually worked is the anatomical noun inside the phenotype, title-scoped and
paired with the organism:

```
TITLE:(medaka) AND TITLE:(fin)      → found the afl/eda paper
medaka AND (edar OR ectodysplasin)  → found the rs-3 paper
```

**Anatomy nouns retrieve where phenotype names do not** — 0 of 26 anatomy terms
came back empty against 18 of 30 phenotype names. But the fine-grained noun is
not the one to search with. Title-scoped, these retrieve **nothing**: `dorsal
fin`, `iris`, `peritoneum`, `cornea`, `pupil`, `centrum`, `fin membrane`. Their
coarse parents do: `fin` 27, `skin` 13, `muscle` 12, `eye` 10, `scale` 8,
`pigment cell` 8, `melanophore` 6.

That split is why `Anatomy` nodes carry a `query_terms` list. The node keeps the
precise name because the graph needs it — whether the iris is involved is the
discriminator between panda and toumeirin — while `query_terms` holds what the
literature actually titles. Do not collapse the two.

### 3. Search each phenotype independently

Independently means the searches must not share terms. Two queries that both
contain the gene name are one query.

### 4. Apply the positional veto

A candidate on a chromosome other than the trait's own GWAS interval **cannot be
that trait's gene**. This is the only check that has never produced a false
negative, so apply it first and cheaply.

`scripts/converge.py` does this. Limitations to state when you use it:

- Gene locations are recorded to chromosome only, so two loci on one chromosome
  cannot be separated (orochi vs black on chr21 — see `content/blog/ko/black.md`).
- A trait with no GWAS interval (breeder traits) has nothing to veto with.

### 5. Count convergence

Count **distinct phenotypes** of the trait that independently reach the same
gene or pathway.

- **1 → do not record a gene.** This is the §8 failure, measured at 75% wrong.
- **≥2 → record as a candidate**, never as the cause.

The second phenotype frequently does not exist in the literature. In the
kagamirin case it came from the user's own breeding observation (short fins),
and that is what moved *edar* from "one word overlapping" to a candidate worth
recording. **Breeder observation is a first-class phenotype source here** — the
hobby holds phenotype data the literature does not.

Record it as a phenotype **before** searching. A phenotype added after seeing
results is selection, not convergence.

### 6. Record the disagreements too

A candidate is not written up until these are in the same entry:

- **Contradicting detail.** *edar* gives *irregular* scales; kagamirin is
  *orderly*. Say so where the candidate is recorded.
- **Counter-evidence already in the repo.** ryuurin combines kagamirin with
  long fins at a claimed ~100% fixation, which argues against short fins being
  inseparable from kagamirin.
- **A falsifiable prediction.** Both *eda* and *edar* mutants lose teeth, so
  kagamirin fish should show tooth anomalies. A candidate that predicts nothing
  checkable is not worth recording.
- **Comparative work capped at OBSERVATIONAL.** Another species' functional
  experiment is homology-based support, not proof in medaka — and it can point
  the wrong way (zebrafish *adcy5* loss *reduces* melanophores; orochi gains
  them).

## Success criteria

- Every number written into a dossier or blog post appears in some dossier.
- No `associated_with_gene` claim rests on one phenotype.
- Every candidate survives the positional veto, or the write-up says why the
  veto could not be applied.
- `python -m medaka_ontology.cli validate` passes, and
  `scripts/validate_rule.py` still recovers the known answers it recovered
  before your change.

## Pitfalls

- **Trait names that are also surnames.** `medaka AND kagami` returns 25 papers,
  all of them by authors named Kagami. Add such forms to
  `AMBIGUOUS_SURFACE_FORMS` in `src/medaka_ontology/lexicon.py`.
- **Namesakes are not homology.** kagamirin is named after mirror carp, whose
  gene (*fgfr1a1*) is known. That is a naming fact. The repo already refuses the
  same move for the trade's ロングフィン vs Kon et al.'s `longfin`.
- **A house strain is not a trait.** ryuurin is kagamirin + rame + longfin, so
  searching "ryuurin" is the wrong unit. Decompose, then search the parts.
- **Composite classes inflate convergence.** YWKo, kurobuchi and akabuchi share
  phenotypes with their members by construction. Discount any phenotype shared
  across a `subsumes` edge.
- **pytest writes fixtures into the dev Neo4j.** Regenerating dossiers straight
  after a test run bakes `doi:10.1/accept-test` into committed files. Check with
  `grep -rl "10\.1/" data/dossier/` before committing a regeneration.

## Scripts

| script | what it answers |
|---|---|
| `scripts/probe_retrieval.py` | do these query strings retrieve anything real? |
| `scripts/anatomy_recall.py` | does the anatomy rung find the *right* paper, and under which organism scope? |
| `scripts/converge.py` | which genes do a trait's phenotypes reach, and which survive the veto? |
| `scripts/validate_rule.py` | does the rule still recover the answers we already know? |

## The anatomy rung, and why it emits two queries

The ladder in `discovery.py` was trait → mutant → gene → mechanism, which
dead-ends on exactly the traits with no gene yet. It now also expands
trait → phenotype → `Anatomy` → `query_terms`.

**Organism scope is an axis, not a constant.** Measured against the 14 traits
whose causal gene is named by a paper *other than* the GWAS this repo already
holds — the only honest denominator, since an anatomy query cannot be expected
to re-find `kon2026`:

| scope | as the pipeline runs it | as a hand probe runs it |
|---|---|---|
| `TITLE:(medaka) AND TITLE:("<term>")` | 8/14 | 8/14 |
| `TITLE:("<term>") AND (medaka OR zebrafish OR teleost OR fish …)` | 8/14 | 10/14 |
| union | **10/14** | **11/14** |

The two columns are two different questions and it matters which one gets
quoted. `run_queries` asks for 25 results and sends no `sort`, so it reads
Europe PMC's **relevance** order; a hand probe defaults to 50 sorted by
citation. Relevance is not the poor relation — it moved yellow from 33rd to
4th and reallongfin from 40th to 10th, because a 1288-hit pool sorted by
citations puts famous papers first rather than relevant ones. It costs one
trait (orochi). **Do not add a sort parameter to the backend on the strength of
the probe column**; it would move every other rung for no measured gain.

The scopes are not nested either. Under the pipeline's own settings, tight
alone reaches daruma and fused centrum, and wide alone reaches reallongfin and
yellow — the latter's papers are zebrafish papers that `TITLE:(medaka)` excludes
by construction. So the rung emits both: tight first because it is precise and
nearly free, wide because it is the only thing that reaches the comparative
literature.

**The ceiling: black, hirenaga, orochi and sanshoku are reached by neither**,
because yang2018 is mammalian and tatarakis2021 is a single-cell atlas that
never names the gene in its title or abstract. No query shape fixes that. Say it
out loud rather than treating a trait as unstudied.

`scripts/anatomy_recall.py` reproduces both columns from `data/seed`; pass
`--as-pipeline` for the left one.

**`scale` is the one term that pays a polysemy tax.** Run live against the real
backend, `TITLE:(medaka) AND (TITLE:"scale")` returns both *edar* papers — the
2001 rs-3 locus paper and the 2010 scale-and-tooth paper — inside the first
eight hits, but four of those eight are `large-scale` and `time scale` papers
about heartbeat detection and ESTs. Expect roughly half a page of noise on that
term specifically, and do not read it as a failed query.

**Two phenotypes deliberately have no anatomy edge.** `hypomelanism`'s only
source describes colour ("brighter than wild type, with decreased blackness")
and `orange spotting`'s three sources all say "orange spots" without ever naming
a cell. Writing melanophore or xanthophore there would be inferring the cell
from the colour, which is the §8 move this repo exists to refuse — and the
contrast is instructive, because `black spotting` *does* have its edge, on the
strength of kuroaka's entry saying "black spots formed by melanophores". Those
two traits do not expand through this rung until a source states the cell.

### Still unresolved

`query_terms` is hand-curated, so it drifts as the literature moves and nothing
currently fails when it does. The cheap check is to re-run `anatomy_recall.py`
and watch the union fall. And pigment cell types (melanophore, xanthophore,
iridophore) are recorded under `Anatomy` deliberately — ZFA does the same — but
if a `CellType` label is ever added, those nodes and their `affects_anatomy`
claims are what moves. Do not repurpose `aliases` for query terms: it is
contracted to sourced naming variants and feeds the matcher.
