# kagamirin → *edar*: open candidate

**Status: OPEN CANDIDATE. Not a claim, not a cause.** Nothing below is in the
graph, and `data/dossier/kagamirin.md` correctly still says "No genetic
association recorded". This file is hand-maintained; the dossiers are
regenerated from Neo4j by `cli dossier-all` and would overwrite anything written
into them by hand, which is why the write-up lives here instead of in the
dossier the skill mentions (`trait-literature-search` §6).

## Why it cannot be a claim yet

An INFERRED `associated_with_gene` needs convergence **and** positive positional
support (`validate`). kagamirin has neither:

- **No locus.** kagamirin is a breeder trait with no GWAS interval, so there is
  no chromosome to test *edar* against. The veto cannot be applied, and absence
  of a veto is not support.
- **No graph convergence.** No trait in the repo holds *edar* on DIRECT or
  MAPPED evidence, so §5 has no neighbours to count. The link below comes from
  reading medaka mutant papers against kagamirin's phenotypes, not from the
  convergence rule.
- **No direct evidence.** No sequencing, mapping or cross of kagamirin fish.

## The two phenotypes that point at the Eda/Edar pathway

| kagamirin phenotype | source of the phenotype | medaka mutant that shares it | evidence cap |
|---|---|---|---|
| enlarged scale | seed claim, BREEDER_OBSERVATION (`swampcreek_kagamirin`) | *rs-3* (*edar*): surviving scales "nearly 3 times larger" than wild type — PMID 22572181 | OBSERVATIONAL phenotype match |
| short fins | **user's own tank observation** (see below) | *afl* (*eda*): "short and twisted fin rays" plus abnormal scales and teeth — PMID 24585696 | OBSERVATIONAL phenotype match |

Papers, all checked against Europe PMC on 2026-09-26:

- **PMID 11516953** — Kondo et al. 2001, *Curr Biol*, doi:10.1016/s0960-9822(01)00324-4.
  The *rs-3* locus encodes *edar*; a transposon in intron 1 causes aberrant
  splicing and near-complete scale loss. Establishes the gene in medaka.
- **PMID 22572181** — Atukorala et al. 2010, *Arch Histol Cytol*, doi:10.1679/aohc.73.139.
  *rs-3*: 83% fewer scales, the survivors irregular in shape and ~3× larger;
  oral teeth −43.5%, pharyngeal −73.5%.
- **PMID 24585696** — Iida et al. 2014, *Dev Dyn*, doi:10.1002/dvdy.24120.
  *afl*, a nonsense mutation in *eda* (the ligand, not the receptor): short and
  twisted fin rays, missing and misshapen scales and teeth, skull deformation.
- **PMID 18833299** — Harris et al. 2008, *PLoS Genet*, doi:10.1371/journal.pgen.1000206.
  **Comparative only (zebrafish), capped at OBSERVATIONAL.** *eda*/*edar* loss
  removes fin rays, scales and pharyngeal teeth, and the response is
  dose-sensitive — the only published hint that a partial allele could give a
  milder phenotype than *rs-3*.

Note the second phenotype is matched through *eda*, the first through *edar*.
They converge on the **pathway**; that is not the same as two hits on one gene.

### Breeder observation (labelled source)

**BREEDER_OBSERVATION, unpublished, the user's own tanks (2026-09-26):**
kagamirin-line fish tend to have short fins. This observation is what moved
*edar* from a one-phenotype overlap to a candidate. It is **not yet in the
seed**: there is no `Source` entry for it and no `has_phenotype → short fin`
claim on kagamirin. Per the skill it should be recorded as a phenotype, with its
date, before any further search on its back.

## Contradicting detail and counter-evidence

- **Shape and order point the other way.** *rs-3* survivors are *irregular*;
  kagamirin is valued for scales that sit in one *orderly*, bilaterally
  symmetric row. Scale *number* is also unrecorded for kagamirin — the mutants'
  primary phenotype is scale loss.
- **ryuurin** (already in the repo, BREEDER_OBSERVATION) combines full-body
  kagamirin with **long fins** at a claimed ~100% fixation. That argues against
  short fins being inseparable from kagamirin, and so weakens the second leg.
- **The namesake is not evidence.** Mirror carp's gene (*fgfr1a1*) is a naming
  fact about carp, not a medaka candidate.

## Falsifiable prediction

Both *eda* (*afl*) and *edar* (*rs-3*) mutants lose teeth. If kagamirin carries
a reduced-function Eda/Edar allele, **kagamirin fish should show fewer oral or
pharyngeal teeth** than wild type or than a non-kagamirin line from the same
breeder. A tooth count (alizarin red, or cleared-and-stained heads) is cheap and
settles the pathway question either way. A normal dentition would count heavily
against the candidate.

## What promotion needs

In the order that makes each step cheapest:

1. **Record the short-fin observation** as a `Source` + `has_phenotype` claim
   (BREEDER_OBSERVATION), dated.
2. **Run the tooth-count prediction** above.
3. **A locus.** A cross or pool-seq of kagamirin × wild type that puts the trait
   on a chromosome, so the positional check can pass rather than merely not
   fail. Only then can an INFERRED claim survive `validate`.
4. **Independent sources.** A second, unrelated breeder account of short fins
   or of tooth anomalies in kagamirin, so the second leg is not one tank.
5. **Direct evidence** (sequencing *edar* and *eda* in kagamirin fish, or
   complementation with *rs-3*) is what would move it past "candidate".
