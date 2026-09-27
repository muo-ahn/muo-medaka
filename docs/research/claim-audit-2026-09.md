# Claim audit, September 2026

TODO.md asked two questions before an audit/enrich skill gets built:

1. How often does an `associated_with_gene` / `associated_with_locus` claim cite a
   paper that does not say what the claim says? `leucophore free → sox5` was one such
   case. Is it rare or common?
2. Does the Europe PMC citations endpoint give usable forward citations for the seed
   papers?

## 1. Sample audit

**Method.** The seed has 61 gene and locus claims in total. `random.seed(20260926)`
drew 20 of them. Each (claim, evidence item) pair was read against the cited paper, 27
pairs in all. kon2026, kimura2014, nagao2014, otsuki2020 and zhang2022 were read in
full text. moriyama2012, inohaya2010, ohtsuka2004 and kawanishi2013 were read from the
abstract only. The claim's own `finding` text did not count as proof, since it is the
thing under audit. The non-SUPPORTED verdicts were then checked by hand against the
claims and the source text.

**Result.**

| verdict | pairs | claims |
|---|---|---|
| SUPPORTED | 21 / 27 | 15 / 20 clean |
| LEVEL_WRONG | 4 | n3, n6, n11, n20 |
| DETAIL_WRONG | 1 | n13 |
| borrowed evidence | 1 | n6 |
| misattributed (lf → sox5 kind) | 0 | 0 / 20 |

The lf → sox5 kind of error, where the paper is about a different gene or a different
mutant, did not occur in 20 claims. That fits a rate of 0 to about 15% (rule of three).
The common error is level inflation, and it is systematic, not random.

### The finding: FINE_MAPPING has no definition

The seed has five `associated_with_gene` items at `FINE_MAPPING`. All five cite kon2026:

| claim | what kon2026 actually did |
|---|---|
| aurora → kitlga | 175-gene interval, never narrowed. kitlga picked by GO term, then a frameshift found |
| hikari → zic1 | confirmed the insertion already known from Da in all 35 fish. The paper calls this a check on its GWAS |
| hikari → zic4 | same locus as zic1, and the data cannot separate the two |
| hirenaga → kcnq5a | no coding variant. An intron-1 deletion that "may affect" expression |
| deme → bmp5 | 109-gene interval, bmp5 picked by GO term, an upstream SNV offered as a marker |

The audit sampled three of the five (n3, n6, n11). The other two follow the same
pattern from their own `finding` text. None of the five narrowed an interval. In this
seed, `FINE_MAPPING` has come to mean "a candidate variant was found inside the GWAS
interval". The PRD §5 lists the level names but defines none of them, so nothing stopped
that drift.

It does not change a gate outcome today. SKILL.md puts `FINE_MAPPING` and
`QTL_GWAS_ASSOCIATION` in the same MAPPED tier. It does change `EVIDENCE_RANK` sorting,
and any claim's claimed strength (50 against 40).

### Other items

- **n6 hikari → zic1, moriyama2012 at CAUSAL_VARIANT.** moriyama2012 found the
  transposon in the Da mutant, not in hikari. The allele is the same, and the claim's
  `interpretation` says the causal work is Da literature. Still, CAUSAL_VARIANT is being
  recorded for a trait whose own strain the paper never examined. Meanwhile the
  `Da mutant → zic1` claim does not cite moriyama2012 at all. The citation sits on the
  wrong claim.
- **n20 Da mutant → zic1, kawanishi2013 at FUNCTIONAL_VALIDATION.** The item's own
  `experiment_type` is "expression analysis". Per the abstract, the paper shows
  expression loss and somite transplantation, not a zic1 perturbation. It should be
  EXPRESSION_ASSOCIATION. The paper entry also has no PMID; it is 23462471.
- **n13 kurobuchi → uvrag.** The gene is right. But the text says "same chr14 interval"
  as sanshoku, and the intervals differ: kurobuchi 22.31–30.08 Mb (230 genes) sits
  inside sanshoku 22.28–30.57 Mb (248 genes). "Nested", not "same".
- Softer notes on SUPPORTED pairs: zhang2022 (zebrafish adcy5 loss lowers melanin, while
  orochi is hyper-melanic) and inohaya2010 (never mentions daruma, so a CONTRADICTS
  stance overreads it) support less than their wording suggests.

## 2. Europe PMC citations endpoint

`GET /europepmc/webservices/rest/MED/{pmid}/citations` and `/references`, 2026-09-26:

| paper | forward (MED) | already in seed | backward (MED) | already in seed |
|---|---|---|---|---|
| kimura2014 | 71 (+13 preprints) | 3 | 57 | 3 |
| nagao2014 | 45 (+4 preprints) | 3 | 50 | 0 |
| kon2026 | 0 (1 preprint) | 0 | 100 | 17 |

It is usable. Things to handle:

- Preprint records duplicate published ones: 8 of 13 for kimura2014, 4 of 4 for
  nagao2014. Deduplicate by normalised title.
- kon2026 is too new for forward citations. For it, the backward list is the useful
  direction.
- About 1 in 6 forward citations has medaka in the title. Filtering on title alone
  finds pigment-cell papers such as sox9b (2021), the Pax3/7–Sox10–Mitf network
  (2023) and uric acid in leucophores (2023). A real screen needs the abstract.
- The lists also caught a false statement in the blog: `leucophore-free.md` said
  kon2026 does not cite kimura2014. It does, in its Introduction.

## What this means for TODO.md

- The audit skill is not the first thing to build. Wrong-paper errors are rare, and
  the error that is common is fixed by a definition and a validate rule. An audit pass
  would not do it better.
- First, define each evidence level in writing. FINE_MAPPING especially: "the interval
  was narrowed to this gene by recombinants or association fine-mapping". A candidate
  variant found in an interval does not qualify. Then make `validate` reject clear
  mismatches between `experiment_type` and `level`, for example "expression analysis"
  at FUNCTIONAL_VALIDATION, or "variant calling" at FINE_MAPPING.
- The citations API makes the enrich direction cheap enough to try.
