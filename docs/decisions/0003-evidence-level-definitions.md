# ADR 0003 — What each evidence level requires

- **Status**: Accepted
- **Date**: 2026-09-27
- **Context**: PRD §5 lists the levels and defines none of them.
  [claim-audit-2026-09](../research/claim-audit-2026-09.md) found the gap filled by
  habit. Every `FINE_MAPPING` gene claim in the seed meant "a candidate variant was
  found in the GWAS interval". None of them narrowed an interval.

## Decision

A level records **what the cited paper's own data showed about this claim's
subject**. It does not record what the paper concluded, what the field believes, or
what another paper showed.

### Rules that apply to every level

1. **Own subject.** The fish in the experiment must carry the claim's subject. They
   count as the same subject when either holds:
   - they belong to the trait's strain;
   - they are the mutant that the trait's own entry defines it as. yellow is
     himedaka, the *b* mutant, so fukamachi2001's cloning of *b* is yellow's own
     evidence. albino is the *i* mutant, so the same holds for koga1995 and
     tsutsumi2006. Neither entry says so yet (see Consequences).

   An equivalence that is itself a finding is not assumed. hikari resembling the Da
   mutant is kon2026's genotyping result, recorded as `hikari putatively_same_as
   Da mutant`. So moriyama2012, which cloned the insertion from Da, is
   CAUSAL_VARIANT evidence for `Da mutant → zic1`. For `hikari → zic1` it is
   nothing. hikari reaches it through the `putatively_same_as` claim, whose own
   evidence says how sure that link is.
2. **Data, not wording.** The level is the strongest thing the paper's data
   reached. It is not the strength of its prose. A gene the authors call a
   "strong candidate" is a candidate.
3. **When torn, go lower.** PRD §5: preserve uncertainty over false confidence.
   `UNKNOWN` is always available.
4. **Other species.** A finding outside medaka is capped at `OBSERVATIONAL` on a
   medaka claim. The loader enforces this through `species` (`COMPARATIVE_CEILING`).
   This ADR does not change it.

### The levels

Written for claims that reach a gene or a variant: `associated_with_gene`,
`associated_with_locus`, `caused_by_variant`.

| level | the paper must show, in fish carrying the subject | does **not** qualify |
|---|---|---|
| `CAUSAL_VARIANT` | a specific variant identified as the lesion. The trait is mapped to it in crosses **or** the same sequence change is introduced (knock-in) or reverted and the phenotype follows | a candidate variant enriched in cases, however striking; an edit that disrupts the gene differently from the natural variant, even one with the same predicted consequence (that is FUNCTIONAL_VALIDATION) |
| `FUNCTIONAL_VALIDATION` | the gene itself perturbed or restored in medaka, and the trait's phenotype appears, is phenocopied, or is rescued: genome editing, morpholino knockdown, transgenic or BAC rescue | expression loss in the mutant; transplantation or other experiments that do not touch the gene |
| `FINE_MAPPING` | the trait's interval **narrowed**, by recombination breakpoints in crosses or by association fine-mapping within the peak, to a region of at most five genes that includes this one | picking a gene out of a wider interval by GO term or known function; finding a candidate variant inside an interval that was never narrowed |
| `QTL_GWAS_ASSOCIATION` | the trait maps by GWAS, QTL or linkage to an interval containing this gene or variant. A candidate variant found inside that interval, or a gene nominated from it, stays here | a gene outside the reported interval |
| `EXPRESSION_ASSOCIATION` | expression of the gene differs between fish with and without the trait, or is lost or gained in the affected tissue: RT-PCR, RNA-seq, in situ | expression in a tissue with no comparison to trait-free fish |
| `OBSERVATIONAL` | the paper names or discusses the link without its own data testing it: a table attribution, a discussion of candidate function, a review, any finding in another species | — |
| `BREEDER_OBSERVATION` | a breeder source, not a paper, records it | — |
| `UNKNOWN` | not yet classified. Not a failure state | — |

"At most five genes" is a line drawn to be checkable, not a biological threshold.
The seed's cloned loci narrowed to a region this small (Da: 174 kbp, two genes; lf:
85 kbp). Its GWAS intervals hold 30 to 318 genes.

Other predicates, such as `has_phenotype`, `participates_in` and `affects_anatomy`,
use the same ladder in spirit. This ADR does not audit them. Several carry
`FUNCTIONAL_VALIDATION` on `mutant characterization` or `expression analysis`.
`hikari putatively_same_as Da mutant` carries FINE_MAPPING on `variant genotyping`.
They need a separate pass.

### Experiment type sets a ceiling

`Evidence.experiment_type` names the experiment, and each experiment can reach only
so far. The table covers every type the seed uses on the three predicates above.

| experiment_type | ceiling |
|---|---|
| `positional cloning`, `mutant mapping`, `variant knock-in`, `somatic reversion analysis` | CAUSAL_VARIANT |
| `genome editing`, `morpholino knockdown`, `mutant rescue`, `transgenic rescue` | FUNCTIONAL_VALIDATION |
| `fine mapping` | FINE_MAPPING |
| `GWAS`, `GWAS candidate nomination`, `variant calling`, `variant genotyping`, `linkage analysis` | QTL_GWAS_ASSOCIATION |
| `expression analysis`, `RT-PCR`, `RNA-seq`, `in situ hybridization` | EXPRESSION_ASSOCIATION |
| `mutant characterization`, `literature attribution`, `discussion of candidate gene function`, `review of gene family function`, `comparative functional analysis`, `comparative mutant analysis`, `comparative single-cell transcriptomics` | OBSERVATIONAL |

How a validate rule reads it:

- **Compound types.** A type such as `variant calling and genome editing` splits on
  `" and "`, and its ceiling is the highest of its parts.
- **Unknown types.** On the three predicates, a part not in the table is an error.
  Adding a type means adding its row. Without that, a new name would slip past the
  table unbounded.
- **A ceiling is only an upper bound.** It catches a level too high for its
  experiment. It cannot tell whether the paper did the experiment its type names,
  or whether an interval was narrowed to five genes. That still takes reading.

`somatic reversion analysis` gets CAUSAL_VARIANT because reversion acts on the
variant: tsutsumi2006 watched the albino phenotype revert where the Tol-1 insertion
excised. The *variant* part of each definition is carried by the type name
(`variant knock-in` against `genome editing`), because no field stores it.

**The DIRECT list is a different question.** `convergence.DIRECT_EXPERIMENTS`
decides which experiments *identify* a gene, so that its claim can skip
convergence. `morpholino knockdown` carries FUNCTIONAL_VALIDATION but stays off
that list. It tests a gene someone already chose, and morphants phenocopy through
off-target effects often enough that one knockdown should not bypass the
convergence rule. A claim that rests on a knockdown alone is INFERRED. `variant
knock-in` belongs on the DIRECT list, and it is on both `DIRECT_EXPERIMENTS` and
SKILL.md step 4.

The table is `medaka_ontology.ceilings.EXPERIMENT_CEILINGS`, and `validate`
enforces it. The Consequences items that a ceiling can see are pinned there as
`KNOWN_CEILING_VIOLATIONS` until their data is fixed. These are the FINE_MAPPING,
expression and edit items. `tests/test_ceilings.py` holds that list equal to what
the seed actually breaks, in both directions. The borrowed-evidence items are
invisible to a ceiling, because the level fits the experiment and only the subject
is wrong. Only reading catches them.

## Consequences

The seed items below break the definition. Each is a separate data fix and not part
of this decision:

- **FINE_MAPPING without narrowing.** kon2026 on aurora → kitlga,
  hikari → zic1 and zic4, hirenaga → kcnq5a and deme → bmp5, plus their
  `caused_by_variant` items. They become QTL_GWAS_ASSOCIATION. All 35 hikari fish
  carry the Da insertion, but genotype concordance is not narrowing.
- **Borrowed across mutants.** The own-subject rule moves these onto the Da mutant:
  - moriyama2012 on `hikari → zic1` and on `hikari → zic1/zic4 enhancer transposon
    insertion`;
  - ohtsuka2004 on `hikari → zic4`. No `Da mutant → zic4` claim exists yet, so it
    has to be created. There ohtsuka2004 is FINE_MAPPING: it narrowed Da to 174
    kbp holding zic1 and zic4, but its morpholino targeted zic1 only. Whether
    moriyama2012 lifts zic4 higher is decided when the claim is written.
- **Expression recorded as function.** kawanishi2013 on `Da mutant → zic1` becomes
  EXPRESSION_ASSOCIATION.
- **Edit is not the variant.** kon2026 on `orochi → adcy5 exon8 56-bp deletion`,
  at CAUSAL_VARIANT. The founders were edited to delete exon 8, and the natural
  variant is a 56-bp intron 7/exon 8 deletion. That is FUNCTIONAL_VALIDATION. The
  gene claim `orochi → adcy5` keeps FUNCTIONAL_VALIDATION and stays DIRECT.
- **Type under-named.** ohtsuka2004 on `Da mutant → zic1` is at
  FUNCTIONAL_VALIDATION on `positional cloning`. The level is right, because a
  *zic1* morpholino partly phenocopied Da. The type should read `positional
  cloning and morpholino knockdown`. Today `convergence.is_direct` compares the
  whole string with the DIRECT list, so the renamed item would stop being DIRECT.
  `is_direct` must split compound types on `" and "` the same way the ceiling
  rule does: a type is DIRECT when any part is on the list. It now does, so the
  rename is safe.
- **Mutant not named on the trait.** The yellow and albino entries do not record
  that they are the *b* and *i* mutants. The own-subject rule needs that written
  down, or their cloning papers fail it and both traits drop out of the truth set.
  Record it on the entries (an alias or the description) with the papers that
  say so.

`convergence.TRUTH_FLOOR` counts a trait as having a known answer at FINE_MAPPING or
better. It keeps that meaning, and the meaning becomes true. After the fixes above,
aurora, hikari, hirenaga and deme drop out of the leave-one-out truth set, because
in their own fish their genes were never more than candidates. The stored baseline
(`validate_rule.baseline.json`) moves with them, and that move is the intended
effect, not a regression.

`extraction.py` suggests FINE_MAPPING for `positional clon*` and `co-segregat*`. A
suggestion is only a proposal (ADR 0002). Positional cloning that ends at the lesion
is still CAUSAL_VARIANT under this table. The regex can wait until the suggestions
are measured.
