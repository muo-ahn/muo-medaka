# ADR 0004 — Evidence levels beyond gene claims

- **Status**: Accepted
- **Date**: 2026-09-27
- **Context**: ADR 0003 defined the levels for `associated_with_gene`,
  `associated_with_locus` and `caused_by_variant`. It left `has_phenotype`,
  `participates_in`, `affects_anatomy`, `putatively_same_as` and
  `human_gene_associated_with` using the ladder "in spirit". An audit of every
  evidence item above OBSERVATIONAL on those predicates found 18 items. The audit
  used each item's `finding`, Europe PMC abstracts for all 12 papers, and the
  kon2026 full text. Seventeen of the 18 were above what their own paper showed,
  or sat on the wrong subject.

## Decision

ADR 0003's general rules carry over unchanged: **own subject**, **data, not
wording**, **when torn, go lower**, and the comparative ceiling on `species`. What
changes per predicate is the question a level answers. For a gene claim, a level
measures how well the paper's data tied a genetic cause to the trait. Each section
below says what it measures instead.

### participates_in (Gene → BiologicalMechanism)

The question is whether perturbing the gene disturbs the process. The object is a
process, not a lesion, so **CAUSAL_VARIANT does not exist on this predicate**.
The top level is FUNCTIONAL_VALIDATION.

| level | the paper must show, for this gene in its own species |
|---|---|
| `FUNCTIONAL_VALIDATION` | an allele of the gene whose identity is established (positional cloning to the gene, editing, rescue, complementation) **and** a phenotype that reads out *this* process |
| `FINE_MAPPING` | a mutant whose phenotype reads out the process, narrowed to at most five genes that include this one |
| `QTL_GWAS_ASSOCIATION` | a trait that reads out the process maps to an interval containing the gene |
| `EXPRESSION_ASSOCIATION` | the gene's expression is lost, gained or changed where the process fails, against wild type |
| `OBSERVATIONAL` | the paper states or reviews the role, or the readout is not this process |

- "In medaka" in ADR 0003 reads here as "in the gene's own species". The subject
  is a gene, and kcnk5b is a zebrafish gene, so zebrafish data on it is its own
  subject. The loader's `species` check already handles this.
- The readout has to match the object. An edit that darkens body colour
  validates pigmentation, not chromatophore *development*.

### has_phenotype (OrnamentalTrait → Phenotype)

**Describing a mutant's phenotype is OBSERVATIONAL.** It is the paper's own data,
but the ladder is a genetic ladder, and a description ties the phenotype to the
strain, not to the trait's genetic cause. The 43 `phenotype description` items
already sit there. Above OBSERVATIONAL the level measures that tie:

| level | requires, in fish carrying the subject |
|---|---|
| `FUNCTIONAL_VALIDATION` | perturbing the trait's gene in medaka reproduces *this* phenotype. A partial or early phenocopy of something else does not count |
| `QTL_GWAS_ASSOCIATION` | *this* phenotype co-segregates with the trait's locus in crosses, and it is not the phenotype that defines the trait |
| `EXPRESSION_ASSOCIATION` | only when the phenotype is itself molecular |
| `OBSERVATIONAL` | characterization, histology, skeletal preparations, attribution |

CAUSAL_VARIANT and FINE_MAPPING are not used.

### affects_anatomy (Phenotype → Anatomy)

This predicate says where in the body a phenotype is found. No genetic experiment
makes that location more certain, so **the predicate is capped at OBSERVATIONAL**.

### putatively_same_as (OrnamentalTrait → OrnamentalTrait)

The question is whether the two traits share one genetic lesion. Rule 1 applies
strictly: only data from fish of the subject strain counts. Data on the object
alone is evidence for the object's own claims and counts for nothing here.

| level | requires |
|---|---|
| `CAUSAL_VARIANT` | the object's lesion is found in the subject's fish at sequence level (same element, same position or breakpoints) and is absent from subject-negative fish |
| `FUNCTIONAL_VALIDATION` | a complementation cross (subject × object) fails to complement. This shows the same gene, not necessarily the same allele |
| `FINE_MAPPING` | the subject narrowed to at most five genes that include the object's gene |
| `QTL_GWAS_ASSOCIATION` | the subject's peak contains the object's locus, or a genotype call of "an insertion" at the locus is concordant with the trait but not shown to be the object's lesion |
| `EXPRESSION_ASSOCIATION` | the subject shows the object's expression defect |
| `OBSERVATIONAL` | the two look alike, or a paper says they are the same |

### human_gene_associated_with (HumanGene → HumanPhenotype)

The comparative ceiling does not apply, because the subject is human. The levels
become human-genetics analogues:

| level | requires |
|---|---|
| `CAUSAL_VARIANT` | a variant segregating in more than one independent family, or recurrent de novo in unrelated probands, with its functional effect shown |
| `FUNCTIONAL_VALIDATION` | the gene perturbed in a model or in patient cells, and the disease phenotype follows |
| `QTL_GWAS_ASSOCIATION` | GWAS or linkage, or a candidate variant segregating in a single pedigree |
| `OBSERVATIONAL` | a case report without segregation, or a review |

### Experiment type sets a ceiling, per predicate

`participates_in`, `has_phenotype`, `affects_anatomy` and `putatively_same_as`
join the ceiling rule. **Each has its own table**, because one experiment reaches
different levels on different predicates. Positional cloning is CAUSAL_VARIANT on
a gene claim. On `participates_in` it is FUNCTIONAL_VALIDATION. On `has_phenotype`
it reaches only QTL_GWAS_ASSOCIATION, because cloning a lesion perturbs nothing.
On `putatively_same_as` it has no row at all.

| predicate | table | how it is built |
|---|---|---|
| `participates_in` | `PARTICIPATES_IN_CEILINGS` | ADR 0003's table capped at FUNCTIONAL_VALIDATION, plus `transgenic overexpression` and `complementation test` (FV), and `functional analysis`, `GO term annotation`, `candidate gene reasoning` (OBSERVATIONAL) |
| `has_phenotype` | `HAS_PHENOTYPE_CEILINGS` | gene perturbations (`genome editing`, `morpholino knockdown`, `mutant rescue`, `transgenic rescue`, `variant knock-in`) at FV; `positional cloning`, `mutant mapping`, `linkage analysis` at QTL_GWAS_ASSOCIATION; expression types at EXPRESSION_ASSOCIATION; `phenotype description`, `mutant characterization`, `skeletal analysis`, `literature attribution` at OBSERVATIONAL; `breeder description` at BREEDER_OBSERVATION |
| `affects_anatomy` | `AFFECTS_ANATOMY_CEILINGS` | `phenotype description`, `mutant characterization`, `skeletal analysis` at OBSERVATIONAL; `breeder description` at BREEDER_OBSERVATION |
| `putatively_same_as` | `PUTATIVELY_SAME_AS_CEILINGS` | `lesion sequencing` CV, `complementation test` FV, `fine mapping` FINE_MAPPING; `variant genotyping`, `variant calling`, `GWAS`, `linkage analysis` QTL_GWAS_ASSOCIATION; `expression analysis` EXPRESSION_ASSOCIATION; `locus comparison`, `literature attribution`, `mutant discovery` OBSERVATIONAL |

The rules are ADR 0003's. Compound types split on `" and "` and take the highest
part. A type missing from the predicate's table is an error. A ceiling is only an
upper bound.

`putatively_same_as` leaves out cloning, mapping and editing on purpose. Each is
done on one trait, and says nothing about its identity with another. A missing row
makes the one-sided evidence fail by name, before any level is read, so an item
like moriyama2012 on hikari cannot come back quietly. Name the comparison
instead: `lesion sequencing` or `complementation test`.

`affects_anatomy` gets a table although every row is a description. A flat cap
would let any new type through, and the rule that unknown types fail should not
depend on the predicate.

**`human_gene_associated_with` gets no ceiling yet.** It has one item, and its
type, `human genetics`, is too coarse to bound anything. Rename the types (for
example `pedigree segregation`, `exome sequencing`, `functional assay`) before
adding a table.

The tables are `medaka_ontology.ceilings.PREDICATE_CEILINGS`. ADR 0003's
`EXPERIMENT_CEILINGS` is unchanged and still bounds the three gene-claim
predicates.

### Where this ADR departs from the audit

- **has_phenotype does not reuse the gene table.** The audit proposed ADR 0003's
  table capped at FV. That would let `positional cloning` carry FUNCTIONAL_VALIDATION
  on a phenotype. By the audit's own definition, FV needs the gene perturbed, and
  cloning perturbs nothing: the most a cross can show is co-segregation. So
  `has_phenotype` gets its own table, and cloning and mapping stop at
  QTL_GWAS_ASSOCIATION.
- **affects_anatomy has a table, not a bare cap.** The audit said a flat cap needs
  no table. That would make it the one ceiled predicate where an unknown type
  passes.
- **putatively_same_as has no rows for cloning or mapping.** The audit said such
  evidence "gives 0". A ceiling cannot express 0, but an absent row can.
- **pnp4a and kitlga keep `positional cloning`.** The audit proposed retyping
  kimura2017 (`synteny candidate, genome editing and complementation`) and
  otsuki2020 (`positional cloning and genome editing`). The retypes do not change
  either level: `positional cloning` already caps at FV here. The same papers carry
  `positional cloning` at CAUSAL_VARIANT on `guanineless → pnp4a` and
  `few melanophore → kitlga`. If kimura2017 did not positionally clone pnp4a, that
  gene claim is the one that is wrong, and it is a gene-claim question for ADR 0003.
  Retyping one copy here would leave the two copies disagreeing about the same
  experiment. The comma form would also not split on `" and "`.
- **adcy5 → chromatophore development drops to OBSERVATIONAL.** The audit offered
  a second option: keep FV and retarget the object to a pigmentation process. No
  such mechanism exists in the seed. Creating one to keep a level is going higher
  when torn.

## Consequences

Item verdicts. All are data fixes, done alongside this ADR:

- **Own subject broken, moved or removed (2).**
  - kawanishi2013 on `hikari has_phenotype dorsal-to-ventral identity
    transformation`. The fish were Da. It moves to `Da mutant has_phenotype` of the
    same phenotype, at OBSERVATIONAL: expression loss plus transplantation perturbs
    no gene. hikari's claim keeps kon2026.
  - moriyama2012 on `hikari putatively_same_as Da mutant`. No hikari fish were
    studied. Removed. The claim keeps kon2026.
- **CAUSAL_VARIANT is not a process level, lowered to FUNCTIONAL_VALIDATION (7).**
  fukamachi2001 on slc45a2 → melanogenesis; kimura2017 on pnp4a → iridophore
  development; otsuki2020 on kitlga, and kimura2014 on slc2a15b, pax7a and
  slc2a11b → chromatophore development; perathoner2014 on kcnk5b → bioelectric fin
  size regulation. perathoner2014's type becomes `positional cloning and transgenic
  overexpression`: it was `mutant characterization`, whose ceiling is
  OBSERVATIONAL.
- **Other downgrades (7).**
  - ohtsuka2004 on `Da mutant has_phenotype`: FV → OBSERVATIONAL. It is
    characterization. The morpholino only partly phenocopied early phenotypes.
  - moriyama2012 on `dorsal-to-ventral identity transformation affects_anatomy
    caudal fin`: FV → OBSERVATIONAL. A skeletal description.
  - kon2026 on `hikari putatively_same_as Da mutant`: FINE_MAPPING →
    QTL_GWAS_ASSOCIATION. A GWAS peak and an insertion call in 35 of 35 fish, but
    not shown at sequence level to be the Da lesion, and no negative controls.
    ADR 0003 already said genotype concordance is not narrowing.
  - kon2026 on `adcy5 participates_in chromatophore development`: FV →
    OBSERVATIONAL. F0 edits darkened body colour. Melanophore development was not
    measured.
  - kawanishi2013 on `zic1 participates_in dorsoventral patterning`: FV →
    EXPRESSION_ASSOCIATION. Expression loss in Da.
  - ohtsuka2004 on `zic4 participates_in dorsoventral patterning`: FV →
    FINE_MAPPING, type `fine mapping and expression analysis`. It narrowed Da to
    174 kbp holding zic1 and zic4. The morpholino targeted zic1 only.
  - carapito2015 on `ADCY5 human_gene_associated_with ADCY5-related dyskinesia`:
    CAUSAL_VARIANT → QTL_GWAS_ASSOCIATION. One pedigree, one splice variant, no
    functional test.
- **Kept, retyped (1).** nagao2014 on `sox5 participates_in chromatophore
  development` stays FV, with type `positional cloning and morpholino knockdown`:
  90 kbp to sox5, a morpholino, and TILLING alleles. As `mutant characterization`
  the ceiling would have rejected it.
- **Unverifiable, left as is (1).** koga1995 on `tyr participates_in
  melanogenesis` stays CAUSAL_VARIANT on `positional cloning`. Its full text is
  unavailable. The abstract reads as a Southern blot on a candidate gene, not
  positional cloning, so the right level may be FV or well below. CAUSAL_VARIANT
  cannot stand on this predicate whatever the paper shows, but the level it should
  fall to needs the paper. It is pinned in `KNOWN_CEILING_VIOLATIONS`, and
  `tests/test_ceilings.py` holds that list to exactly this entry. tsutsumi2006
  (somatic reversion) would give the claim real FV evidence if added.

Follow-ups, not done here:

- `zic1 participates_in dorsoventral patterning` now sits below zic4's, at
  EXPRESSION_ASSOCIATION against FINE_MAPPING. ohtsuka2004's zic1 morpholino is
  the evidence that separates zic1, and it is not recorded on that claim.
- carapito2015's finding says disease mutations "cluster in the coiled-coil and
  C1b domains". That is not this paper's data (rule 2). The pairing with the
  orochi C1b deletion in `00-papers.yaml` rests on other papers.
- `00-papers.yaml` still says "PMID not confirmed" for koga1995. Europe PMC
  resolves it by DOI to PMID 8552044.
- Whether kimura2017 positionally cloned pnp4a, which decides the type and level
  on `guanineless → pnp4a`.
