# ADR 0006 — The genetic layer

- **Status**: Accepted; the PRD §14 part is superseded in part by [ADR 0007](0007-offspring-prediction-in-scope.md)
- **Date**: 2026-10-01
- **Context**: The ontology said which gene a trait maps to and how well. It did
  not say how a trait is *inherited*: recessive or dominant, which allele of which
  locus, what is sex-linked, what hides what, which strain is built from which
  traits. `epistatic_with` (undirected, gene-level) is the only predicate near it
  and cannot say any of it. Breeders ask exactly these questions, and the
  second-pass spec asked that the answer be expressible well enough to reproduce a
  published cross.

## Decision

### Predicates

Each was checked against the existing set first (PRD §4). Subject and object are
the labels the loader enforces (`PREDICATE_SHAPES`).

| predicate | subject → object | says |
|---|---|---|
| `inherited_as` | OrnamentalTrait / Gene / Locus / GeneticVariant → InheritanceMode | a source's statement of the mode |
| `allele_of` | GeneticVariant → Gene / Locus | a classical allele (B, b, R, r ...) belongs to this locus. Two alleles of one locus are alleles of each other; that is derived, not stored |
| `dominant_over` | GeneticVariant → GeneticVariant | the subject's phenotype shows in the heterozygote |
| `incompletely_dominant_over` | GeneticVariant → GeneticVariant | the heterozygote is intermediate |
| `requires_allele` | OrnamentalTrait → GeneticVariant | the trait is shown only when this allele is expressed. Several edges on one trait are a conjunction; how many copies follows from the dominance edges |
| `linked_to` | Gene / Locus ↔ Gene / Locus | symmetric: the two do not assort independently. Sex-determining locus included |
| `masks` | OrnamentalTrait → OrnamentalTrait | when the subject is expressed the object cannot be seen, whatever the genotype at the object's loci. Phenotype-level epistasis |
| `composed_of` | OrnamentalTrait / Strain → OrnamentalTrait | defined as a combination; every part must be present. Unlike `subsumes`, an umbrella over alternatives |

`InheritanceMode` is a new node label with a **closed set of names**
(`InheritanceModeName`): `recessive`, `dominant`, `incompletely dominant`,
`multilocus`, `sex-linked`. A node, not a property, so that two sources disagreeing
on a trait's mode are two claims with their own evidence and not an overwrite.
Sex linkage is orthogonal to dominance (the medaka r allele is recessive *and*
sex-linked), so a trait or locus may carry two `inherited_as` claims; daruma does,
because Kon et al.'s cell reads "Recessive, Incomplete dominant (dorsalfin)".

### Evidence levels

One new level, **`INFERRED`**, rank 5: above `UNKNOWN`, below `BREEDER_OBSERVATION`.
It means *a conclusion we drew from what the cited source does state*. Nobody
wrote "B is an allele of slc45a2"; it follows from b being one. It ranks below
every stated level because no source said it.

Rules for an `INFERRED` item, enforced by tests:

1. It cites a **literature** paper (DOI, PMID or PMCID), not a trade source, and
   uses `experiment_type: inference`.
2. The reasoning is on the claim's `interpretation` (PRD §2.3, our reading, never
   the source's words).
3. A claim can carry INFERRED beside a stronger stated item; its strongest-support
   level is then the stronger one.

Levels per predicate, which is the question each answers (ADR 0003, 0004 pattern):

| predicate | the question | highest level | what reaches it |
|---|---|---|---|
| `inherited_as` | does a source state this mode? | `QTL_GWAS_ASSOCIATION` | `segregation analysis`, `linkage analysis`: the paper's own counted cross. A table column citing earlier work is `literature attribution`, `OBSERVATIONAL` |
| `allele_of` | is this allele a variant of this gene or locus? | `CAUSAL_VARIANT` | the gene-claim table (ADR 0003): positional cloning of the allele. `inference` is INFERRED |
| `dominant_over`, `incompletely_dominant_over` | which allele shows in the heterozygote? | `QTL_GWAS_ASSOCIATION` | counted segregation. A methods sentence stating it is `genotype notation`, `OBSERVATIONAL` |
| `requires_allele` | which alleles does the trait need? | `QTL_GWAS_ASSOCIATION` | `GWAS` or `variant genotyping`: concordance in fish that show it. Not a cross, so no higher |
| `linked_to` | do the loci assort together? | `QTL_GWAS_ASSOCIATION` | `linkage analysis`. A statement that an allele is on the Y is `literature attribution` |
| `masks` | is the object hidden when the subject shows? | `BREEDER_OBSERVATION` in practice | a trade description (`breeder description`) or our `inference` |
| `composed_of` | is the strain made of these traits? | `BREEDER_OBSERVATION` in practice | the same |

The ceiling table is `ceilings.INHERITANCE_CEILINGS`; `allele_of` uses the
gene-claim table plus `inference`. Nothing on this layer is a lesion, so
`CAUSAL_VARIANT`, `FUNCTIONAL_VALIDATION` and `FINE_MAPPING` do not occur except on
`allele_of`. As everywhere, a ceiling is an upper bound, not a grade.

Trade sources stay `BREEDER_OBSERVATION` (existing test), so `masks`, `composed_of`
and the RLF statements from JMA and the shop are bounded by it whatever they say.

### What the seed records, and what it does not

Recorded, each with the paper and a quote where the source has one: Kon et al.
2026 Table 1's 11 modes (verbatim, tested against the paper's cells), the b, r and
i loci with alleles and dominance (Sasano 2012 Methods and Tables 3 and 4), the
sex linkage of r and its attachment to dmy (Hayasaka 2019), two JMA `masks` edges,
two `composed_of` strains, one `linked_to` pair on chr21.

Not recorded, on purpose:

- No recombination fraction. The r locus and the sex-determining locus are taken
  as completely linked (spec: no source gives a rate, so 0, stated).
- No mode for a trait no source gives one for. 33 traits have none; the query says so.
- No gene for panda or daruma. Kon et al. reject the earlier attributions, and
  the alleles `pd` and `d` are defined by the trait and the interval, with symbols
  that are ours and say so.
- Nothing from the trade's ロングフィン: it is sex-limited expression, not sex
  linkage, and not Kon et al.'s longfin.

### The cross query, and why PRD §14 is only touched by a validation query

> **Superseded in part by [ADR 0007](0007-offspring-prediction-in-scope.md) (2026-10-02).**
> The owner lifted the §14 non-goals for offspring prediction and cross simulation;
> where this section says the non-goal is only touched by a validation query, and
> that lifting it is left open, ADR 0007 is the later word. The rest of the section
> (what the query reads, what it reports) still holds.

`genetics.py` reads the loaded seed and, from two genotypes (or from what the
parents show), returns offspring genotypes and traits by sex, with exact fractions.
Every rule it applies is a claim above; the weakest evidence level among the claims
a prediction rests on is printed beside it; a trait recorded only as `multilocus`
is refused ("not predictable (multilocus, kon2026)") and a trait with no mode is
said to have none; each assumption it makes is listed in the output.

PRD §14 lists a *Mendelian cross simulator* and *offspring phenotype prediction* as
non-goals. This ADR does **not** lift them. The query exists to **validate that the
layer is expressive and honest enough**: it reproduces the Hayasaka Hd-rRII1
maintenance cross, reports the fit of Sasano's Cross I counts, and shows sex linkage
breaking 9:3:3:1 (tests/test_genetics.py; the numbers are in
docs/research/cross-validation-2026-10.md). It recommends no cross, ranks no
strategy, and manages no stock. Whether to lift the non-goal and build a breeding
tool is **the user's decision** and is left open.

## Consequences

- 8 predicates, 1 node label, 1 evidence level, and `genetics.py` with a `cross`
  command that needs no database.
- The ontology's gene-centred question ("how well is this association
  established") now has a sibling ("how well is this inheritance established") with
  its own ladder, and the weakest-link report makes the second visible.
- A prediction is only as strong as `INFERRED` wherever it leans on a recessive
  trait's dominance edge, because Table 1 says "Recessive" at the trait level and
  nothing states it at the allele level. The output says so.
- Genotype symbols for d, pd, ndf and RLF are ours. A symbol is a handle, not a
  claim, and each allele's description says it is ours.
