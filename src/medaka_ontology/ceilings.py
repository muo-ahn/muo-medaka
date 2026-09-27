"""How strong a level each experiment can carry. ADR 0003 and ADR 0004.

The audit behind ADR 0003 found `FINE_MAPPING` on every kon2026 gene claim whose
paper had only found a candidate variant inside a GWAS interval, and
`FUNCTIONAL_VALIDATION` on an expression study. Neither mistake needs the paper
to catch: the experiment named on the evidence could never have reached the
level written next to it. This module holds those tables and nothing else.

ADR 0004 extends the ceiling from the three gene-claim predicates to
`participates_in`, `has_phenotype`, `affects_anatomy` and `putatively_same_as`.
Each has its own table, because one experiment reaches different levels on
different predicates: positional cloning is CAUSAL_VARIANT for a gene claim,
FUNCTIONAL_VALIDATION for a gene's role in a process, and only co-segregation
for a trait's phenotype. `human_gene_associated_with` has no ceiling: its one
type, `human genetics`, is too coarse to bound anything.

A ceiling is only an upper bound. It cannot tell whether the paper did the
experiment its type names, or whether an interval really was narrowed to five
genes. That still takes reading.
"""

from __future__ import annotations

from .models import Claim, Evidence, SeedBundle
from .vocabulary import EVIDENCE_RANK, EvidenceLevel, Predicate

_L = EvidenceLevel

#: ADR 0003, "Experiment type sets a ceiling". Keys are lower case; lookups
#: normalise. A type missing from here is an error on the predicates below, so a
#: new experiment name cannot slip past the table unbounded -- add its row.
EXPERIMENT_CEILINGS: dict[str, EvidenceLevel] = {
    # The lesion itself: mapped to, recreated, or reverted.
    "positional cloning": _L.CAUSAL_VARIANT,
    "mutant mapping": _L.CAUSAL_VARIANT,
    "variant knock-in": _L.CAUSAL_VARIANT,
    "somatic reversion analysis": _L.CAUSAL_VARIANT,
    # The gene perturbed or restored, not the variant.
    "genome editing": _L.FUNCTIONAL_VALIDATION,
    "morpholino knockdown": _L.FUNCTIONAL_VALIDATION,
    "mutant rescue": _L.FUNCTIONAL_VALIDATION,
    "transgenic rescue": _L.FUNCTIONAL_VALIDATION,
    "fine mapping": _L.FINE_MAPPING,
    # A variant found inside an interval that was never narrowed stays here.
    "gwas": _L.QTL_GWAS_ASSOCIATION,
    "gwas candidate nomination": _L.QTL_GWAS_ASSOCIATION,
    "variant calling": _L.QTL_GWAS_ASSOCIATION,
    "variant genotyping": _L.QTL_GWAS_ASSOCIATION,
    "linkage analysis": _L.QTL_GWAS_ASSOCIATION,
    "expression analysis": _L.EXPRESSION_ASSOCIATION,
    "rt-pcr": _L.EXPRESSION_ASSOCIATION,
    "rna-seq": _L.EXPRESSION_ASSOCIATION,
    "in situ hybridization": _L.EXPRESSION_ASSOCIATION,
    "mutant characterization": _L.OBSERVATIONAL,
    "literature attribution": _L.OBSERVATIONAL,
    "discussion of candidate gene function": _L.OBSERVATIONAL,
    "review of gene family function": _L.OBSERVATIONAL,
    "comparative functional analysis": _L.OBSERVATIONAL,
    "comparative mutant analysis": _L.OBSERVATIONAL,
    "comparative single-cell transcriptomics": _L.OBSERVATIONAL,
}

#: The predicates ADR 0003 defines levels for. They share `EXPERIMENT_CEILINGS`.
GENE_CLAIM_PREDICATES = frozenset(
    {Predicate.ASSOCIATED_WITH_GENE, Predicate.ASSOCIATED_WITH_LOCUS, Predicate.CAUSED_BY_VARIANT}
)

#: ADR 0004, participates_in. The object is a process, not a lesion, so the top
#: level is FUNCTIONAL_VALIDATION: the gene-claim table capped there, plus the
#: types only this predicate uses.
PARTICIPATES_IN_CEILINGS: dict[str, EvidenceLevel] = {
    **{
        k: min(v, _L.FUNCTIONAL_VALIDATION, key=EVIDENCE_RANK.__getitem__)
        for k, v in EXPERIMENT_CEILINGS.items()
    },
    "transgenic overexpression": _L.FUNCTIONAL_VALIDATION,
    "complementation test": _L.FUNCTIONAL_VALIDATION,
    "functional analysis": _L.OBSERVATIONAL,
    "go term annotation": _L.OBSERVATIONAL,
    "candidate gene reasoning": _L.OBSERVATIONAL,
}

#: ADR 0004, has_phenotype. Describing a mutant is OBSERVATIONAL. Above that the
#: level measures how the phenotype was tied to the trait's genetic cause:
#: perturbing the gene reproduces it, or it co-segregates with the locus in
#: crosses. Cloning a lesion perturbs nothing, so it reaches only co-segregation.
HAS_PHENOTYPE_CEILINGS: dict[str, EvidenceLevel] = {
    "genome editing": _L.FUNCTIONAL_VALIDATION,
    "morpholino knockdown": _L.FUNCTIONAL_VALIDATION,
    "mutant rescue": _L.FUNCTIONAL_VALIDATION,
    "transgenic rescue": _L.FUNCTIONAL_VALIDATION,
    "variant knock-in": _L.FUNCTIONAL_VALIDATION,
    "positional cloning": _L.QTL_GWAS_ASSOCIATION,
    "mutant mapping": _L.QTL_GWAS_ASSOCIATION,
    "linkage analysis": _L.QTL_GWAS_ASSOCIATION,
    # Only for a molecular phenotype. The table cannot see which one it is.
    "expression analysis": _L.EXPRESSION_ASSOCIATION,
    "rt-pcr": _L.EXPRESSION_ASSOCIATION,
    "rna-seq": _L.EXPRESSION_ASSOCIATION,
    "in situ hybridization": _L.EXPRESSION_ASSOCIATION,
    "phenotype description": _L.OBSERVATIONAL,
    "mutant characterization": _L.OBSERVATIONAL,
    "skeletal analysis": _L.OBSERVATIONAL,
    "literature attribution": _L.OBSERVATIONAL,
    "breeder description": _L.BREEDER_OBSERVATION,
}

#: ADR 0004, affects_anatomy. Where a phenotype sits in the body. No genetic
#: experiment makes that more certain, so every row is a description.
AFFECTS_ANATOMY_CEILINGS: dict[str, EvidenceLevel] = {
    "phenotype description": _L.OBSERVATIONAL,
    "mutant characterization": _L.OBSERVATIONAL,
    "skeletal analysis": _L.OBSERVATIONAL,
    "breeder description": _L.BREEDER_OBSERVATION,
}

#: ADR 0004, putatively_same_as. Whether two traits share one lesion, measured in
#: the subject's fish. Cloning or editing one trait says nothing about its
#: identity with another, so those types are absent on purpose: name the
#: comparison instead.
PUTATIVELY_SAME_AS_CEILINGS: dict[str, EvidenceLevel] = {
    "lesion sequencing": _L.CAUSAL_VARIANT,
    "complementation test": _L.FUNCTIONAL_VALIDATION,
    "fine mapping": _L.FINE_MAPPING,
    # A call at the locus, concordant with the trait, not shown at sequence
    # level to be the other trait's lesion.
    "variant genotyping": _L.QTL_GWAS_ASSOCIATION,
    "variant calling": _L.QTL_GWAS_ASSOCIATION,
    "gwas": _L.QTL_GWAS_ASSOCIATION,
    "linkage analysis": _L.QTL_GWAS_ASSOCIATION,
    "expression analysis": _L.EXPRESSION_ASSOCIATION,
    "locus comparison": _L.OBSERVATIONAL,
    "literature attribution": _L.OBSERVATIONAL,
    "mutant discovery": _L.OBSERVATIONAL,
}

#: Which table bounds which predicate. A predicate missing here has no ceiling.
PREDICATE_CEILINGS: dict[Predicate, dict[str, EvidenceLevel]] = {
    **dict.fromkeys(GENE_CLAIM_PREDICATES, EXPERIMENT_CEILINGS),
    Predicate.PARTICIPATES_IN: PARTICIPATES_IN_CEILINGS,
    Predicate.HAS_PHENOTYPE: HAS_PHENOTYPE_CEILINGS,
    Predicate.AFFECTS_ANATOMY: AFFECTS_ANATOMY_CEILINGS,
    Predicate.PUTATIVELY_SAME_AS: PUTATIVELY_SAME_AS_CEILINGS,
}

CEILED_PREDICATES = frozenset(PREDICATE_CEILINGS)

#: Where to add a missing row, and which ADR a breach cites.
_SOURCE: dict[Predicate, tuple[str, str]] = {
    **dict.fromkeys(GENE_CLAIM_PREDICATES, ("ceilings.EXPERIMENT_CEILINGS", "ADR 0003")),
    Predicate.PARTICIPATES_IN: ("ceilings.PARTICIPATES_IN_CEILINGS", "ADR 0004"),
    Predicate.HAS_PHENOTYPE: ("ceilings.HAS_PHENOTYPE_CEILINGS", "ADR 0004"),
    Predicate.AFFECTS_ANATOMY: ("ceilings.AFFECTS_ANATOMY_CEILINGS", "ADR 0004"),
    Predicate.PUTATIVELY_SAME_AS: ("ceilings.PUTATIVELY_SAME_AS_CEILINGS", "ADR 0004"),
}

#: Evidence that breaks its ceiling today and is being fixed in the data, not
#: here. Keyed (predicate, subject, object, paper, experiment_type). Pinned by
#: `tests/test_ceilings.py` in both directions, like `convergence.KNOWN_VIOLATIONS`:
#: a new breach fails the suite, and so does an entry whose data was fixed.
#:
#: ADR 0003's eleven entries were fixed in the data: the kon2026 FINE_MAPPING
#: items on aurora, hikari, hirenaga and deme became QTL_GWAS_ASSOCIATION,
#: kawanishi2013 on Da mutant -> zic1 became EXPRESSION_ASSOCIATION, and the
#: orochi exon-8 edit became FUNCTIONAL_VALIDATION.
#:
#: ADR 0004 leaves one. koga1995 on tyr -> melanogenesis is CAUSAL_VARIANT, which
#: participates_in cannot carry. The full text is unavailable, and the abstract
#: reads as a Southern blot on a candidate gene rather than positional cloning,
#: so the right level may be FUNCTIONAL_VALIDATION or well below it. It stays
#: pinned until the paper is read, rather than moved to a level nobody checked.
KNOWN_CEILING_VIOLATIONS: frozenset[tuple[str, str, str, str, str]] = frozenset(
    {("participates_in", "tyr", "melanogenesis", "koga1995", "positional cloning")}
)


def experiment_parts(experiment_type: str) -> list[str]:
    """`variant calling and genome editing` -> its two experiments, normalised."""
    return [p.strip() for p in experiment_type.strip().lower().split(" and ") if p.strip()]


def ceiling_of(
    experiment_type: str, predicate: Predicate = Predicate.ASSOCIATED_WITH_GENE
) -> EvidenceLevel | None:
    """The highest part's ceiling, or None when any part is not in the table."""
    table = PREDICATE_CEILINGS[predicate]
    levels = [table.get(p) for p in experiment_parts(experiment_type)]
    if not levels or any(lv is None for lv in levels):
        return None
    return max(levels, key=EVIDENCE_RANK.__getitem__)


def _key(claim: Claim, ev: Evidence) -> tuple[str, str, str, str, str]:
    # Names without labels: a Gene and a Locus sharing a name would collide. None
    # do today, and labels would double the width of KNOWN_CEILING_VIOLATIONS.
    return (
        claim.predicate.value, claim.subject.name, claim.object.name,
        ev.paper, ev.experiment_type,
    )


def ceiling_violations(bundle: SeedBundle) -> dict[tuple[str, str, str, str, str], str]:
    """Every evidence item on a ceiled predicate whose level its experiment cannot reach."""
    problems: dict[tuple[str, str, str, str, str], str] = {}
    for claim in bundle.claims:
        table = PREDICATE_CEILINGS.get(claim.predicate)
        if table is None:
            continue
        table_name, adr = _SOURCE[claim.predicate]
        for ev in claim.evidence:
            parts = experiment_parts(ev.experiment_type)
            if not parts:
                problems[_key(claim, ev)] = "has no experiment_type, so it has no ceiling"
                continue
            unknown = [p for p in parts if p not in table]
            if unknown:
                problems[_key(claim, ev)] = (
                    f"experiment_type {ev.experiment_type!r} has no ceiling "
                    f"(unknown: {', '.join(unknown)}); add it to "
                    f"{table_name} and {adr}"
                )
                continue
            ceiling = max((table[p] for p in parts), key=EVIDENCE_RANK.__getitem__)
            if ev.rank > EVIDENCE_RANK[ceiling]:
                problems[_key(claim, ev)] = (
                    f"{ev.level.value} is above what {ev.experiment_type!r} can show "
                    f"(ceiling {ceiling.value}, {adr})"
                )
    return problems


__all__ = [
    "AFFECTS_ANATOMY_CEILINGS",
    "CEILED_PREDICATES",
    "EXPERIMENT_CEILINGS",
    "GENE_CLAIM_PREDICATES",
    "HAS_PHENOTYPE_CEILINGS",
    "KNOWN_CEILING_VIOLATIONS",
    "PARTICIPATES_IN_CEILINGS",
    "PREDICATE_CEILINGS",
    "PUTATIVELY_SAME_AS_CEILINGS",
    "ceiling_of",
    "ceiling_violations",
    "experiment_parts",
]
