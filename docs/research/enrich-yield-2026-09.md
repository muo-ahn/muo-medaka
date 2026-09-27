# Enrich yield measurement — Europe PMC forward citations of 3 seed papers

## Method
Seeds: kimura2014 (PMID 24803434, 85 forward citations), nagao2014 (PMID 24699463, 49),
kimura2017 (PMID 28258112, 30). Pooled = 164 raw hits. Deduplicated by normalised title
(dropping preprints that duplicate a MED record, papers citing >1 seed counted once, and
7 rows that are seed papers citing each other) to 106 unique papers screened by abstract.

## Pooled counts (106 screened)

| bin | count |
|---|---|
| COMPARATIVE | 75 |
| IRRELEVANT | 25 |
| NEW_CLAIM | 3 |
| CHANGES_CLAIM | 1 |
| NEEDS_FULLTEXT | 2 |

**Yield = (NEW_CLAIM + CHANGES_CLAIM) / screened = 4 / 106 = 3.8%**

## Per-seed counts

| seed | screened (citing this seed) | NEW_CLAIM | CHANGES_CLAIM | COMPARATIVE | IRRELEVANT | NEEDS_FULLTEXT |
|---|---|---|---|---|---|---|
| kimura2014  | 71 | 3 | 1 | 54 | 11 | 2 |
| nagao2014   | 42 | 2 | 1 | 30 |  8 | 1 |
| kimura2017  | 27 | 2 | 0 | 14 | 11 | 0 |

(Rows citing more than one seed are counted once in the pooled total but once per seed here,
so the per-seed columns sum to more than 106.)

## The 5 best finds

1. **34807452** — *Contribution of sox9b to pigment cell formation in medaka fish* (2021).
   sox9b is functionally redundant with sox10a/b in medaka leucophore formation (CRISPR
   compound mutants). sox9b is not in the ontology at all — a clean NEW_CLAIM at
   FUNCTIONAL_VALIDATION.
2. **37823232** — *A gene regulatory network combining Pax3/7, Sox10 and Mitf...* (2023).
   Medaka mitf mutants lose melanophores, xanthophores *and* leucophores; pax7 (not just
   pax7a/lf-2's role) switches xanthophore vs. leucophore fate downstream of mitf. NEW_CLAIM,
   FUNCTIONAL_VALIDATION.
3. **29621239** — *Distinct interactions of Sox5 and Sox10...* (2018). Same lab, same sox5
   gene as nagao2014's ml-3 claim, but shows sox5's direction of effect on leucophores is
   opposite in medaka vs. zebrafish, and that sox5 acts epistatic to sox10. CHANGES_CLAIM —
   adds mechanism to the existing sox5/ml-3 claim at the same level.
4. **30845151** — *Enhanced in vivo-imaging in medaka...* (2019). Buried in a methods paper:
   oca2;pnp4a CRISPR double mutants are fully depigmented. oca2 is a plausible new
   gene-to-trait NEW_CLAIM the ontology doesn't have, found only because the abstract was
   read past its "methods" framing.
5. **34460822** — *The genetics and evolution of eye color in domestic pigeons* (2021, not a
   medaka paper). GWAS + causal nonsense variant in **SLC2A11B** — the same gene as medaka's
   `wl` (white leucophore, kimura2014) — for pigeon iris colour. Capped at COMPARATIVE/
   OBSERVATIONAL for medaka, but a striking independent confirmation that SLC2A11B loss
   depigments a chromatophore-derived structure in a second vertebrate lineage.

## Verdict: would a title filter ("medaka" in title) have sufficed?

Yes, on this sample. All 11 papers with "medaka" or "Oryzias" in the title were read in full;
the other 95 were binned by title/abstract topic without needing the "own subject" test.
**All 4 of the useful finds (3 NEW_CLAIM + 1 CHANGES_CLAIM) have "medaka" in the title.**
Recall of a naive title filter on the useful set: **4/4 = 100%**. Precision would be low
(4/11 = 36%, since 7 of the 11 medaka-titled hits are methods papers, reviews, or
out-of-scope phenotypes), but recall is what matters for not missing a claim, and it was
perfect here. The 34460822 (pigeon SLC2A11B) find shows a title filter would still miss
genuinely useful comparative confirmations that never say "medaka" — but those are capped
at OBSERVATIONAL by ADR 0003's own-subject rule anyway, so missing them costs less.

## Cost

- HTTP calls: 3 (citations lists, pageSize 1000 each) + 6 (batched abstract searches,
  20 IDs each via `EXT_ID:... OR EXT_ID:...`) = 9 calls total.
- Abstracts read: 101 fetched via Europe PMC `search` (batch abstracts), plus the 11
  medaka-titled ones read in full by hand; 2 had no abstract text at all (NEEDS_FULLTEXT).
- Wall time: roughly 30-35 minutes end to end, including a broken `python_repl` bridge
  that had to be worked around with PowerShell/`ConvertFrom-Json` and `curl`.

## Conclusion

3.8% yield (4/106) on a 3-seed sample, and only 3 of those are genuinely new gene-trait
claims (1 is a refinement of an existing claim). That is low but not zero, and 2 of the 4
were found only because a "methods" or "sex determination" paper was read past its own
framing (30845151, 29621239) — a keyword filter beyond "medaka in title" would have surfaced
them anyway since both have medaka in the title. The bigger practical finding is that a plain
title filter on "medaka"/"Oryzias" would have cut the abstract-reading load by ~90% (106 to
11) at 100% recall on the useful set for this sample, which is a much cheaper first pass than
screening all forward citations by abstract. Given the low absolute yield, a full standalone
"enrich" skill built around forward-citation chasing is not obviously worth it on its own;
it is closer to being worth it as a title-filtered pre-screen bolted onto the existing
audit/discovery pipeline, and even then only 3 seeds were tested here.

## Caveats (added on review)

- **The title filter's 100% recall is partly by construction.** The 11
  medaka-titled papers were read in full. The other 95 were binned from their
  topic, on the reasoning that a non-medaka paper can only be COMPARATIVE. But
  a medaka paper does not always say so in its title. kawanishi2013 is titled
  "the teleost trunk" and is a medaka paper. This method would not have caught
  such a paper, so the true recall of a title filter is unmeasured.
  A safer pre-screen matches medaka/Oryzias in the **abstract**, which costs the
  same number of HTTP calls (abstracts are batch-fetched) and nothing extra to
  read.
- **Three seeds, one lab cluster.** All three are Hashimoto-lab pigment-cell
  papers, and their citers overlap heavily. The yield may not transfer to
  kon2026's GWAS neighbourhood, or to morphology traits.
- The pigeon SLC2A11B find is capped at OBSERVATIONAL by the comparative
  ceiling (ADR 0003 rule 4). The own-subject rule is a different rule.

Raw rows: `enrich-yield-2026-09.csv`.
