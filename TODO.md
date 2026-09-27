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
- [x] Relabel the five FINE_MAPPING gene claims, and the matching `caused_by_variant`
      items, to QTL_GWAS_ASSOCIATION (ADR 0003 §Consequences). Expect the
      leave-one-out baseline to lose aurora, hikari, hirenaga and deme (hikari once
      the Da evidence below has moved too).
      → Done in `21-claims-gwas.yaml`. Leave-one-out loses aurora, hikari and
      hirenaga (deme was never tested: no neighbour nominates it), and
      `Da mutant → zic4` turns correct because the new claim puts zic4 in Da's
      truth set. Baseline not yet re-stored: that extra move needs sign-off.
- [x] `validate`: enforce the ADR 0003 experiment_type ceiling table on
      gene, locus and variant claims. Split compound types on " and ", and reject
      unknown types. Make `is_direct` split compounds the same way. Add
      `variant knock-in` to `DIRECT_EXPERIMENTS` and to SKILL.md step 4.
      → `src/medaka_ontology/ceilings.py`, `tests/test_ceilings.py`. The 11 current
      breaches are pinned in `KNOWN_CEILING_VIOLATIONS`. Each data fix below must
      remove its entry, or the test fails.
- [x] Move borrowed Da evidence off hikari: moriyama2012 (hikari → zic1, and the
      hikari transposon `caused_by_variant`) and ohtsuka2004 (hikari → zic4). Put
      them on the Da mutant claims. Create `Da mutant → zic4`, which does not exist
      (ohtsuka2004 at FINE_MAPPING there).
      → hikari → zic1/zic4 are now MAPPED on kon2026 alone. `Da mutant → zic4`
      carries ohtsuka2004 at FINE_MAPPING and moriyama2012 at
      EXPRESSION_ASSOCIATION (shared enhancer, so torn → lower).
- [x] orochi `caused_by_variant`: kon2026 edited exon 8 out and did not recreate
      the 56-bp deletion, so it goes CAUSAL_VARIANT → FUNCTIONAL_VALIDATION.
      → Done; the claim's interpretation says why.
- [x] ohtsuka2004 on Da mutant → zic1: set the type to `positional cloning and
      morpholino knockdown`. The level stays. `is_direct` now splits compounds,
      so the claim stays DIRECT.
      → Done; `tests/test_convergence.py` now pins Da mutant → zic1 as DIRECT.
- [x] Record on the yellow and albino entries that they are the *b* and *i*
      mutants (ADR 0003 own-subject rule), with the papers that say so.
      → In each `description` (fukamachi2001, koga1995). Not an alias: PRD §8
      keeps aliases for naming variants, not biological identity.
- [x] Lower kawanishi2013 to EXPRESSION_ASSOCIATION and add PMID 23462471. Change
      "same" to "nested" on kurobuchi → uvrag.
      → Done. PMID checked on Europe PMC (DOI and title match).
      `KNOWN_CEILING_VIOLATIONS` is now empty.
- [x] Audit the levels on `has_phenotype`, `participates_in` and `affects_anatomy`.
      ADR 0003 leaves them out.
      → Done in ADR 0004 (with `putatively_same_as`): 17 of 18 items resolved, four
      predicates ceiled; koga1995 on tyr -> melanogenesis pinned until read.

### Left over from ADR 0004

- [ ] Read koga1995 in full and confirm its PMID. Then set the level on
      tyr -> melanogenesis and drop its `KNOWN_CEILING_VIOLATIONS` entry. The
      abstract reads as a Southern blot, not cloning.
- [ ] zic1 -> dorsoventral patterning does not cite ohtsuka2004's zic1
      morpholino, though that is the one experiment that perturbed zic1.
- [ ] Two finding texts are wrong: carapito2015 (domain clustering) and
      perathoner2014 (the longfin allele). Re-read them and correct.
- [ ] guanineless -> pnp4a (kimura2017): check that `positional cloning` is the
      experiment the paper actually did.
- [ ] Dossiers for traits added in PR #7 (many leucophores-3 and others) are not
      in `data/dossier/`. `load` only upserts, so a local Neo4j keeps stale
      evidence. Render from a fresh database.

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
