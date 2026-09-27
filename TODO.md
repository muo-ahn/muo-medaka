# TODO

## Split literature work by where it starts

`trait-literature-search` judges one thing well: **may this gene be recorded for
this trait?** It starts from a trait's phenotypes and ends at the gate
(`medaka_ontology.convergence` + `validate`).

It is not built for the other two jobs:

- **Improving what is already recorded.** In PR #7, none of the useful data work
  came from the skill's own search:
  - `leucophore free → sox5` was caught by the new `validate` rule. Reading the
    cited paper confirmed it: nagao2014 cloned *sox5* from *ml-3*.
  - lf-2 and wl came from reading one paper (kimura2014) to the end, which
    means expanding outward from a paper.
  - fused centrum → *wnt4b* moved to DIRECT because someone re-read its
    abstract. The skill has no step that looks for stronger or newer evidence.
- **Taking in a trait the ontology does not have.** Step 1 reads
  `data/dossier/<trait>.md`, so the trait must already exist. `converge.py`
  nominates only genes already in the graph. There is no procedure for defining
  a new trait, and none for trade names or surname-like names.

### Proposed shape

Keep one gate. Add entry points instead of growing the current skill.

| job | starts from | core steps |
|---|---|---|
| candidate judgement (exists) | a trait's phenotypes | convergence, positional check |
| audit / enrich (new) | existing claims and their cited papers | check the citation says what the claim says → follow citations forward and backward (Europe PMC citations API) → harvest sibling loci and traits from the same paper → upgrade or downgrade evidence level |
| new-trait intake (new) | a trade name or breeder observation | define the trait, decompose phenotypes before searching, check for name collisions (`AMBIGUOUS_SURFACE_FORMS`), Japanese names |

All three end at `convergence.py` + `validate`, so the rules live in one place.

### Measure before building

- [x] Sample-audit about 20 random `associated_with_gene` / `associated_with_locus`
      claims against their cited papers. Record the misattribution rate.
      → `docs/research/claim-audit-2026-09.md`. 0/20 misattributed, 5/20 with a
      problem, mostly level inflation. Every FINE_MAPPING gene claim is really
      "candidate variant in the interval". The audit skill does not come first.
- [x] Check whether the Europe PMC citations endpoint returns usable forward
      citations for the seed papers (kimura2014, nagao2014, kon2026).
      → Yes for kimura2014 (71) and nagao2014 (45). kon2026 is too new, so use its
      100 references instead. Deduplicate preprints by title.

### Next, from the audit

- [x] Write a definition for each evidence level (PRD §5 only lists names).
      → `docs/decisions/0003-evidence-level-definitions.md`.
- [ ] Relabel the five FINE_MAPPING gene claims, and the matching `caused_by_variant`
      items, to QTL_GWAS_ASSOCIATION (ADR 0003 §Consequences). Expect the
      leave-one-out baseline to lose aurora, hikari, hirenaga and deme (hikari once
      the Da evidence below has moved too).
- [x] `validate`: enforce the ADR 0003 experiment_type ceiling table on
      gene, locus and variant claims. Split compound types on " and ", and reject
      unknown types. Make `is_direct` split compounds the same way. Add
      `variant knock-in` to `DIRECT_EXPERIMENTS` and to SKILL.md step 4.
      → `src/medaka_ontology/ceilings.py`, `tests/test_ceilings.py`. The 11 current
      breaches are pinned in `KNOWN_CEILING_VIOLATIONS`. Each data fix below must
      remove its entry, or the test fails.
- [ ] Move borrowed Da evidence off hikari: moriyama2012 (hikari → zic1, and the
      hikari transposon `caused_by_variant`) and ohtsuka2004 (hikari → zic4). Put
      them on the Da mutant claims. Create `Da mutant → zic4`, which does not exist
      (ohtsuka2004 at FINE_MAPPING there).
- [ ] orochi `caused_by_variant`: kon2026 edited exon 8 out and did not recreate
      the 56-bp deletion, so it goes CAUSAL_VARIANT → FUNCTIONAL_VALIDATION.
- [ ] ohtsuka2004 on Da mutant → zic1: set the type to `positional cloning and
      morpholino knockdown`. The level stays. `is_direct` now splits compounds,
      so the claim stays DIRECT.
- [ ] Record on the yellow and albino entries that they are the *b* and *i*
      mutants (ADR 0003 own-subject rule), with the papers that say so.
- [ ] Lower kawanishi2013 to EXPRESSION_ASSOCIATION and add PMID 23462471. Change
      "same" to "nested" on kurobuchi → uvrag.
- [ ] Audit the levels on `has_phenotype`, `participates_in` and `affects_anatomy`.
      ADR 0003 leaves them out.

## Smaller follow-ups

- [x] Add CI (`validate`, `pytest` with `NEO4J_URI=bolt://127.0.0.1:1`,
      `ruff`). The repo has no workflows, so PRs show no checks.
      → `.github/workflows/ci.yml`. It runs `ruff check` only: 21 files fail
      `ruff format --check`.
- [x] Check `content/blog/README.md:58`, which says zebrafish lack
      leucophores. It may be outdated.
      → It was. Adult zebrafish have two leucophore populations (Lewis 2019, PNAS,
      doi:10.1073/pnas.1901021116). Fixed there and in `leucophore-free.md`, whose
      thesis rested on it.
- [ ] Measure the precision of the ≥2 convergence branch once it fires. It has
      never fired.
- [x] `data/seed/23-claims-breeder.yaml` shows as modified from line endings
      only. Normalise it or add a `.gitattributes`.
      → `.gitattributes` with `* text=auto eol=lf`. The blob already matches the
      index; `git update-index --refresh` clears the stale flag.
