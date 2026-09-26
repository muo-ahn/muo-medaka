---
name: trait-literature-search
description: >-
  Find and judge literature for an ornamental medaka trait in this ontology, and
  decide whether a gene may be recorded as its candidate. Use when asked to
  research a trait, look for papers on a trait or phenotype, chase a "this trait
  seems related to gene X" hunch, propose or evaluate a candidate gene, or work
  out why a trait has no gene yet. Also use before writing any
  associated_with_gene claim. Covers Europe PMC querying, the convergence rule,
  the positional veto, and the validation that keeps both honest. Also triggers
  on 논문 탐색, 형질 리서치, 후보 유전자, 어떤 유전자와 연관.
---

# Trait literature search and candidate judgement

Scripts referenced below live in `scripts/` next to this file and run against
the checkout's own `data/seed/*.yaml` — no database needed, and any working
directory will do: every path is resolved from the script's location.

**Worktrees.** The venv's editable install points at the main checkout's `src/`.
The scripts put their own checkout's `src/` first on `sys.path`, so they are
safe; the CLI and pytest are not. In a worktree run them with `PYTHONPATH=src`
(PowerShell: `$env:PYTHONPATH="src"`), or you are validating the main
checkout's code against your seed files.

## What this skill is defending against

The failure this repo exists to prevent (PRD §8) is a gene name becoming folk
knowledge because one word appeared in two sentences. The defence is not
caution in prose. It is three mechanical checks, each measured against traits
whose answer is already known.

**Measured by leave-one-out on the traits with a known gene and at least one
phenotype — 10 eligible, 7 of which produced any nomination at all:**

| check | result |
|---|---|
| a gene arriving from one neighbour trait | 3 of 12 correct (25%) |
| ≥2 neighbour traits **and** ≥2 papers converge on one gene | never fires — recall 0, **precision unmeasured** |
| positional veto (wrong chromosome) | kills 5 wrong, **0 correct** |

The ≥2 branch has never fired on a known answer, so nothing here says it is
right when it does fire. It is a bar the single-neighbour case demonstrably
fails, not a validated detector. `scripts/validate_rule.py` reproduces the
table and diffs it against `scripts/validate_rule.baseline.json`, and
`tests/test_convergence.py` makes the same comparison.

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

### 4. Decide which path the gene is on

Not every gene claim needs convergence. `medaka_ontology.convergence` sorts each
`associated_with_gene` claim by how the gene was reached, and `validate`
enforces the result:

| basis | what it takes | needs convergence? |
|---|---|---|
| **DIRECT** | a SUPPORTS finding at `CAUSAL_VARIANT` or `FUNCTIONAL_VALIDATION`, with `species: Oryzias latipes` **written out**, and `experiment_type` one of `positional cloning`, `mutant mapping`, `mutant rescue`, `transgenic rescue`, `genome editing`, `somatic reversion analysis` | no |
| **MAPPED** | a SUPPORTS finding at `FINE_MAPPING` or `QTL_GWAS_ASSOCIATION`, species written out as medaka | no, but the positional veto applies |
| **UNASSERTED** | nothing above `UNKNOWN` supports it (a Table 1 attribution nobody tested) | exempt; it asserts nothing |
| **INFERRED** | anything else | **yes**, plus a consistent position |

The experiment list is closed on purpose. `mutant characterization` and
`expression analysis` describe a gene already assumed to be the right one. If a
paper really did clone or rescue the gene, record that experiment by its name:
fused centrum → *wnt4b* is DIRECT because inohaya2010 made transgenic rescue
lines, not because it characterised the mutant.

**Species is never left to the default.** `Evidence.species` defaults to medaka,
which is exactly how a zebrafish knockout whose author forgot the field would
pass as medaka functional validation. The loader rejects any finding above
`OBSERVATIONAL` on a medaka claim that does not state its species, and a
finding in any other species is capped at `OBSERVATIONAL` and can never make a
claim DIRECT. Read the methods for the organism: a title about "the teleost
trunk" may be medaka (kawanishi2013) or may not.

**Known violations.** `convergence.KNOWN_VIOLATIONS` holds claims that fail the
rule while a data fix is pending. It is empty. Its one entry, `leucophore free
→ sox5`, was a misattribution: nagao2014 cloned *sox5* from *ml-3*, and
kimura2014 cloned *lf* as *slc2a15b*. The test pins the list in both
directions, so it cannot grow quietly and cannot outlive a fix. Do not add to it
to make `validate` pass.

### 5. Count convergence (INFERRED only)

A gene reaches the trait when another trait shares one of its phenotypes and
holds that gene on DIRECT or MAPPED evidence. An inferred gene never seeds
further inference. It **converges** only when both hold:

- **≥2 distinct neighbour traits.** Traits linked by `subsumes` count once:
  yellow, white, kouhaku and YWKo share phenotypes by construction.
- **≥2 distinct papers** behind those neighbours' gene claims. Two neighbours
  that both got their gene from kon2026 are one line of evidence, not two.

Counting phenotypes, as this skill used to, is not convergence: several
phenotypes can all lead back to one neighbour through one paper.

- **Not convergent → do not record a gene.** This is the §8 failure, measured
  at 75% wrong.
- **Convergent → record as a candidate**, never as the cause, and only if the
  positional check below also passes.

### 6. Apply the positional check

A candidate on a chromosome other than the trait's own GWAS interval **cannot be
that trait's gene**. It has never removed a correct nomination.

`scripts/converge.py` decides convergence first and only then the position, so
its verdict says *why* a gene is out. The trait's chromosomes come from its
`associated_with_locus` claims' `Locus.chromosome`, not from parsing finding
text. Limitations to state when you use it:

- Gene locations are recorded to chromosome only, so two loci on one chromosome
  cannot be separated (orochi vs black on chr21 — see `content/blog/ko/black.md`).
- A trait with no GWAS interval (breeder traits) has nothing to check with. For
  an INFERRED gene that means **it cannot be recorded as a claim**: `validate`
  requires positive positional support, not merely the absence of a veto. Write
  it up as an open candidate instead, in `docs/research/<trait>-<gene>-open-candidate.md`:
  dossiers are regenerated from the graph and would overwrite a hand edit.
  `docs/research/kagamirin-edar-open-candidate.md` is the worked example.

The second phenotype frequently does not exist in the literature. In the
kagamirin case it came from the user's own breeding observation (short fins),
and that is what moved *edar* from "one word overlapping" to a candidate worth
recording. **Breeder observation is a first-class phenotype source here** — the
hobby holds phenotype data the literature does not.

Record it as a phenotype **before** searching. A phenotype added after seeing
results is selection, not convergence.

### 7. Record the disagreements too

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
- Every `associated_with_gene` claim is DIRECT, MAPPED, UNASSERTED, or a
  convergent INFERRED gene with positional support. `validate` checks this.
- Every candidate left in prose survives the positional veto, or the write-up
  says why the veto could not be applied.
- `python -m medaka_ontology.cli validate` passes, `pytest` passes, and
  `scripts/validate_rule.py` prints `matches validate_rule.baseline.json`. If
  your change is meant to move those numbers, re-run it with
  `--update-baseline` and say why in the commit.

## Pitfalls

- **Trait names that are also surnames or given names.** `medaka AND kagami`
  returns 25 papers, all of them by authors named Kagami; Miyuki is a common
  given name. Both are in `AMBIGUOUS_SURFACE_FORMS` in
  `src/medaka_ontology/lexicon.py`; add any new one there.
- **Japanese variety names are trade names, not loci.** 幹之 (miyuki), 光
  (hikari) or オロチ (orochi) name what a breeder sells, and one name can cover
  lines bred independently from different mutations. The trade's ロングフィン is
  not Kon et al.'s `longfin`. Search the phenotype or the lab mutant, never the
  variety name, and do not merge two traits because their names match.
- **Paralogs and same-name genes.** Teleost duplicates (`kitlga`/`kitlgb`) are
  different genes, often on different chromosomes, and a paper saying "kit
  ligand" may mean either. Loose aliases cross genes too:
  "oculocutaneous" matched *oca2* abstracts and credited them to *slc45a2*, and
  "zic" cannot tell *zic1* from *zic4*. Check the symbol and the chromosome, not
  the family name. The same holds for mutants: *lf* and *ml-3* are both
  leucophore mutants, and conflating them is how `leucophore free → sox5` got
  recorded.
- **Namesakes are not homology.** kagamirin is named after mirror carp, whose
  gene (*fgfr1a1*) is known. That is a naming fact. The repo already refuses the
  same move for the trade's ロングフィン vs Kon et al.'s `longfin`.
- **A house strain is not a trait.** ryuurin is kagamirin + rame + longfin, so
  searching "ryuurin" is the wrong unit. Decompose, then search the parts.
- **Composite classes inflate convergence.** YWKo, kurobuchi and akabuchi share
  phenotypes with their members by construction. `convergence.py` counts every
  `subsumes`-linked group as one neighbour; do the same by hand.
- **pytest writes fixtures into the dev Neo4j.** Regenerating dossiers straight
  after a test run bakes `doi:10.1/accept-test` into committed files. Check with
  `grep -rl "10\.1/" data/dossier/` before committing a regeneration. To run the
  suite without touching the database, point `NEO4J_URI` at a closed port
  (`bolt://127.0.0.1:1`) and the integration modules skip.

## Scripts

| script | what it answers |
|---|---|
| `scripts/probe_retrieval.py` | do these query strings retrieve anything real? |
| `scripts/anatomy_recall.py` | does the anatomy rung find the *right* paper, and under which organism scope? |
| `scripts/converge.py` | which genes reach a trait, from how many neighbours and papers, and could any be recorded? |
| `scripts/validate_rule.py` | does the rule still recover the answers we already know, and does it match the stored baseline? |

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
| `TITLE:("<term>") AND (medaka OR zebrafish OR teleost OR fish …)` | 7/14 | 9/14 |
| union | **9/14** | **10/14** |

Re-measured 2026-09-26. The earlier 10/14 and 11/14 counted yellow through the
*slc45a2* alias "oculocutaneous", which also matches *oca2*. The pipeline's
"4th" hit for yellow was a zebrafish *oca2* model paper; the probe's "33rd" was
a mouse *Matp* paper — Matp is SLC45A2's mammalian name, so that one was real
but reached through the wrong word. That is why this page no longer quotes
"yellow 33rd → 4th": the two ranks were not the same gene. With the alias
removed neither scope reaches yellow. `matp` is not in the alias map; adding it
would return yellow to the probe column only, via a mouse paper.

The two columns are two different questions and it matters which one gets
quoted. `run_queries` asks for 25 results and sends no `sort`, so it reads
Europe PMC's **relevance** order; a hand probe defaults to 50 sorted by
citation. Relevance is not the poor relation — it moved reallongfin from 40th
to 10th and albino from 12th to 2nd, because a 1288-hit pool sorted by
citations puts famous papers first rather than relevant ones. It costs one
trait (orochi, at rank 25 under citations). **Do not add a sort parameter to
the backend on the strength of the probe column**; it would move every other
rung for a measured gain of one trait.

The scopes are not nested either. Under the pipeline's own settings, tight
alone reaches daruma and fused centrum, and wide alone reaches reallongfin,
whose paper (zhangj2010) is a zebrafish paper that `TITLE:(medaka)` excludes by
construction. So the rung emits both: tight first because it is precise and
nearly free, wide because it is the only thing that reaches the comparative
literature.

**The ceiling: black, hirenaga, orochi, sanshoku and yellow are reached by
neither** under the pipeline's settings. yang2018 is mammalian, tatarakis2021
is a single-cell atlas that never names the gene in its title or abstract, and
fukamachi2001 surfaces in neither pool and calls the gene "B", not *slc45a2*.
No query shape fixes that. Say it out loud rather than treating a trait as unstudied.

`scripts/anatomy_recall.py` reproduces both columns from `data/seed`; pass
`--as-pipeline` for the left one. It derives each phenotype's terms from the
`affects_anatomy` claims and the `Anatomy` nodes' `query_terms`, the path the
rung itself takes, so it cannot drift from the seed the way its old hand-copied
map did: that map gave hypomelanism and orange spotting the pigment-cell terms
the next paragraph withholds.

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
