# ADR 0007 — Offspring prediction is in scope

- **Status**: Accepted
- **Date**: 2026-10-02
- **Supersedes in part**: [ADR 0006](0006-genetic-layer.md), the section that kept PRD §14
  untouched. PRD §14 is amended to match.
- **Context**: PRD §14 listed a *Mendelian cross simulator* and *offspring phenotype
  prediction* as non-goals. ADR 0006 built the genetic layer and a `cross` query anyway,
  scoped as a validation query ("it exists to show the layer is honest enough, lifts
  nothing"), and left lifting the non-goal to the owner. The query reproduced the
  published crosses it was tested on (Hayasaka 2019, Sasano 2012 Cross I, the sex-linked
  F2; `docs/research/cross-validation-2026-10.md`). On 2026-10-02 the owner decided
  that offspring trait prediction belongs to the project. This ADR records what that
  does and does not mean, so that a prediction feature does not grow into the
  breeding-decision system the PRD still excludes.

## Decision

1. **Offspring trait prediction is a formal feature** of the ontology: from two parents'
   genotypes, or from the traits two parents show, the genotypes and traits of their
   offspring, by sex and overall, as exact fractions. `medaka cross` is its command and
   `medaka_ontology.genetics` its module. The "validation query" label is dropped.
2. **Prediction is not recommendation.** The feature answers "what do these claims imply
   for this cross", never "which cross should I make". It is the same kind of answer as
   a gene dossier: sourced, graded, and silent where the sources are.
3. PRD §14 now lists as non-goals: mating recommendation, pedigree management,
   individual stock management, optimal cross strategy, image-based phenotype
   classification. "Mendelian cross simulator" and "offspring phenotype prediction" are
   removed. PRD §1 and §14 carry a dated decision note.

## Scope boundary

**In scope**

- Genotype input and phenotype input (a range over every genotype consistent with what
  the parents show), with an optional true-breeding restriction.
- Per-sex and overall class distributions; genotype distributions; masked traits and
  the composite strains that absorb their parts.
- For each predicted trait, the weakest evidence level among the claims the prediction
  rests on, and the claims used.
- Every assumption the query makes, in both views, always.
- Explicit refusals, each with a code and a reason.
- A machine-readable output, `--json`, whose shape is a documented, versioned contract.

**Out of scope (still non-goals)**

- Choosing, ranking or suggesting crosses; proposing parents for a target trait; scoring
  a cross by anything but the probability it states.
- Storing individuals, pedigrees or breeding records. The query takes its parents as
  arguments and keeps nothing.
- Anything the seed does not claim. The query reads claims; a rule that is not a claim
  does not exist for it. It adds no biology of its own.
- Quantitative traits, penetrance, expressivity, sex-limited expression, linkage maps,
  and the 356 trade strain names (two composite strains are modelled).

## The contract

**Input.** A genotype is one `a/b` token per locus, separated by space, comma or
semicolon. At the sex-linked r locus a male's token is `X allele / Y allele`, so `r/R` is
X^r Y^R and `R/r` is X^R Y^r; a female's is her two X alleles and the order carries no
meaning. A locus not given is homozygous wild type. A parent may instead be described by
the trait names it shows (`--mother-shows`, `--father-shows`), optionally restricted to
homozygotes (`--true-breeding`). Errors name the fix: unknown symbol (with the known
ones), alleles of two loci in one token, a locus given twice, a lone allele at a
sex-linked locus, the wrong sexes, an unknown trait name (with the nameable ones), a
trait set no genotype can show.

**Output.** `schema_version` 1. Fractions are strings `"n/d"` (`"1/1"` for one). A phenotype
cross gives each share as `{"min", "max"}`. Keys and their order are pinned by
`tests/test_cross_feature.py`; the README documents them. A key may be added without a
version bump, a key removed, renamed or re-meant bumps it.

**Display rules**, enforced in `genetics.py` and shared by the text and JSON renderers:

- R1. Every predicted trait carries its weakest evidence level, the claim that sets it,
  and the claims used. A `masks` claim is one of them only when the result hides that
  trait in some class (it appears under `hidden`); the other claims are counted
  statically.
- R2. A weakest level below `OBSERVATIONAL` (`BREEDER_OBSERVATION`, `INFERRED`,
  `UNKNOWN`) is a *weak basis*: the trait is marked `[LEVEL]` wherever a class names it,
  the evidence line is flagged, and the JSON says `weak_basis: true`.
- R3. Every `INFERRED` claim a prediction leans on prints its reasoning as an assumption.
- R4. The assumptions are part of every result. A result missing any of the four open
  decisions is not rendered (`ModelError`).
- R5. A class with an unresolved heterozygote (`T?`) carries a warning.
- R6. A trait the query refuses is listed with a code and a reason, never dropped.

**Refusals** (`genetics.REFUSALS`), each tested:

| code | when | behaviour |
|---|---|---|
| `multilocus` | a source records the trait as multilocus | error if named as input; listed otherwise |
| `no_allele_model` | a mode is recorded but no allele model exists, or a composite's parts have none | same |
| `no_inheritance_data` | no source says how the trait is inherited | same |
| `disputed` | a claim the prediction rests on has contradicting evidence | the trait is not predicted; same |
| `linked_loci_no_recombination_fraction` | two loci in the cross are joined by `linked_to` and no rate is recorded | the cross is refused |

Two further cases are deliberate non-refusals. A heterozygote whose alleles have no
dominance claim is reported as an unresolved class (`T?`) with a warning, because the
rest of the cross is still determined and hiding the half that is not would be worse
than marking it. The `linked_to` claim between the r locus and the sex-determining gene
does not refuse, because that pair is the stated r-sex assumption below.

## Assumptions the owner has not decided

The decision above does not settle the following. They are kept exactly as ADR 0006 and
the second-pass spec left them and are **stated on every result** as open decisions:

1. **Strain names.** Only two composite strains are modelled; the 356 trade names are
   not incorporated. A strain cannot be a parent; name its traits.
2. **Source authority order** (JMA > field guide > breeding farm > blog): provisional.
   The query does not use it to settle disagreements; it uses evidence levels, caps trade
   sources at `BREEDER_OBSERVATION`, and refuses a disputed claim.
3. **r–sex-locus recombination fraction**: 0. No source gives one.
4. **Albino allele heterogeneity** (`tyr` vs `oca2`): two albino parents are assumed to
   carry the same allele.

## Consequences

- The "validation" caveat comes out of the README, the CLI help, the module docstring
  and the cross-validation note; the cross numbers do not change.
- `genetics.py` grows an output layer with a versioned schema. Changing the layout of
  the JSON is now a breaking change for whoever parses it.
- Every prediction is as weak as its weakest claim, and says so. Today most predictions
  that involve dominance of a recessive trait's allele are `INFERRED` (ADR 0006), and a
  prediction for `blue` is `BREEDER_OBSERVATION` when some class hides blue behind an
  albino (the `masks` claim, a trade description, then bears on it) and not otherwise.
  Both are deliberate and visible (R2). The `masks` claim was first counted statically
  even when no albino was in the cross; that over-marked every blue prediction.
- A disputed claim now silences the traits under it. That is a loss of output and a gain
  in honesty; the seed has none today (a test says so).
- If the owner later wants recommendation or strategy, that is a new ADR and a new
  module. Nothing here is a half-built version of it.
