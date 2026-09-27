"""How strong a level each experiment can carry. ADR 0003.

The audit behind ADR 0003 found `FINE_MAPPING` on every kon2026 gene claim whose
paper had only found a candidate variant inside a GWAS interval, and
`FUNCTIONAL_VALIDATION` on an expression study. Neither mistake needs the paper
to catch: the experiment named on the evidence could never have reached the
level written next to it. This module holds that table and nothing else.

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

#: The predicates ADR 0003 defines levels for. Others use the ladder only in
#: spirit and have not been audited.
CEILED_PREDICATES = frozenset(
    {Predicate.ASSOCIATED_WITH_GENE, Predicate.ASSOCIATED_WITH_LOCUS, Predicate.CAUSED_BY_VARIANT}
)

#: Evidence that breaks its ceiling today and is being fixed in the data, not
#: here. Keyed (predicate, subject, object, paper, experiment_type). Pinned by
#: `tests/test_ceilings.py` in both directions, like `convergence.KNOWN_VIOLATIONS`:
#: a new breach fails the suite, and so does an entry whose data was fixed.
#: Every entry is listed in ADR 0003 §Consequences.
KNOWN_CEILING_VIOLATIONS: frozenset[tuple[str, str, str, str, str]] = frozenset(
    {
        # FINE_MAPPING without narrowing: a candidate variant in a GWAS interval.
        ("associated_with_gene", "aurora", "kitlga", "kon2026", "variant calling"),
        ("associated_with_gene", "hirenaga", "kcnq5a", "kon2026", "variant calling"),
        ("associated_with_gene", "deme", "bmp5", "kon2026", "variant calling"),
        ("associated_with_gene", "hikari", "zic1", "kon2026", "GWAS and variant genotyping"),
        ("associated_with_gene", "hikari", "zic4", "kon2026", "GWAS and variant genotyping"),
        (
            "caused_by_variant", "aurora", "kitlga frameshift chr6:2485888",
            "kon2026", "variant calling",
        ),
        (
            "caused_by_variant", "hirenaga", "kcnq5a intron1 deletion",
            "kon2026", "variant calling",
        ),
        (
            "caused_by_variant", "deme", "bmp5 upstream SNV chr15:24280607",
            "kon2026", "variant calling",
        ),
        (
            "caused_by_variant", "hikari", "zic1/zic4 enhancer transposon insertion",
            "kon2026", "variant genotyping",
        ),
        # Expression recorded as function.
        ("associated_with_gene", "Da mutant", "zic1", "kawanishi2013", "expression analysis"),
        # The edit removed exon 8; it did not recreate the 56-bp deletion.
        (
            "caused_by_variant", "orochi", "adcy5 exon8 56-bp deletion",
            "kon2026", "variant calling and genome editing",
        ),
    }
)


def experiment_parts(experiment_type: str) -> list[str]:
    """`variant calling and genome editing` -> its two experiments, normalised."""
    return [p.strip() for p in experiment_type.strip().lower().split(" and ") if p.strip()]


def ceiling_of(experiment_type: str) -> EvidenceLevel | None:
    """The highest part's ceiling, or None when any part is not in the table."""
    levels = [EXPERIMENT_CEILINGS.get(p) for p in experiment_parts(experiment_type)]
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
        if claim.predicate not in CEILED_PREDICATES:
            continue
        for ev in claim.evidence:
            parts = experiment_parts(ev.experiment_type)
            if not parts:
                problems[_key(claim, ev)] = "has no experiment_type, so it has no ceiling"
                continue
            unknown = [p for p in parts if p not in EXPERIMENT_CEILINGS]
            if unknown:
                problems[_key(claim, ev)] = (
                    f"experiment_type {ev.experiment_type!r} has no ceiling "
                    f"(unknown: {', '.join(unknown)}); add it to "
                    "ceilings.EXPERIMENT_CEILINGS and ADR 0003"
                )
                continue
            ceiling = max((EXPERIMENT_CEILINGS[p] for p in parts), key=EVIDENCE_RANK.__getitem__)
            if ev.rank > EVIDENCE_RANK[ceiling]:
                problems[_key(claim, ev)] = (
                    f"{ev.level.value} is above what {ev.experiment_type!r} can show "
                    f"(ceiling {ceiling.value}, ADR 0003)"
                )
    return problems


__all__ = [
    "CEILED_PREDICATES",
    "EXPERIMENT_CEILINGS",
    "KNOWN_CEILING_VIOLATIONS",
    "ceiling_of",
    "ceiling_violations",
    "experiment_parts",
]
