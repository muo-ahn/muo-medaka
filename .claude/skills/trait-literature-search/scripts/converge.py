"""Which genes do a trait's phenotypes reach, and which survive the veto?

Reads data/seed/*.yaml. No database.

A gene scores one point per DISTINCT phenotype of the trait that reaches it
through another trait carrying the same phenotype. Score 1 is the PRD section 8
failure mode and is wrong 75% of the time on traits whose answer we know. Score
2 or more is the kagamirin situation.

The positional veto is applied after scoring: a gene on a chromosome other than
the trait's own GWAS interval cannot be that trait's gene. On the known-answer
traits it removed 5 wrong nominations and 0 correct ones.

    python .claude/skills/trait-literature-search/scripts/converge.py [trait ...]
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

SEED = Path("data/seed")
CLAIM_FILES = ("20-claims-structure", "21-claims-gwas", "22-claims-background",
               "23-claims-breeder")
ENTITY_FILES = ("10-entities-traits", "11-entities-genomic",
                "12-entities-breeder-traits")

#: Ordering only. Mirrors vocabulary.EvidenceLevel ranks closely enough to sort
#: nominations; it is not a substitute for the real ladder.
RANK = {"CAUSAL_VARIANT": 5, "FUNCTIONAL_VALIDATION": 4, "FINE_MAPPING": 3,
        "EXPRESSION_ASSOCIATION": 3, "QTL_GWAS_ASSOCIATION": 2,
        "OBSERVATIONAL": 1, "BREEDER_OBSERVATION": 0, "UNKNOWN": 0}

#: Below this a claim is not treated as naming a gene for the trait at all.
NOMINATION_FLOOR = RANK["QTL_GWAS_ASSOCIATION"]


def load():
    claims, ents = [], []
    for f in CLAIM_FILES:
        claims += yaml.safe_load((SEED / f"{f}.yaml").read_text("utf-8"))["claims"]
    for f in ENTITY_FILES:
        ents += yaml.safe_load((SEED / f"{f}.yaml").read_text("utf-8"))["entities"]

    pheno_of: dict[str, set[str]] = defaultdict(set)
    genes_of: dict[str, dict[str, int]] = defaultdict(dict)
    subsumes: set[frozenset[str]] = set()
    trait_chr: dict[str, str] = {}

    for c in claims:
        pred, subj, obj = c["predicate"], c["subject"], c["object"]
        rank = max((RANK.get(e.get("level", "UNKNOWN"), 0)
                    for e in c.get("evidence", [])), default=0)
        if pred == "has_phenotype":
            pheno_of[subj["name"]].add(obj["name"])
        elif pred == "associated_with_gene":
            prev = genes_of[subj["name"]].get(obj["name"], -1)
            genes_of[subj["name"]][obj["name"]] = max(prev, rank)
        elif pred == "subsumes":
            subsumes.add(frozenset((subj["name"], obj["name"])))
        elif pred == "associated_with_locus":
            for e in c.get("evidence", []):
                m = re.search(r"chromosome (\d+)", e.get("finding", ""))
                if m:
                    trait_chr[subj["name"]] = m.group(1)

    gene_chr = {e["name"]: str(e["chromosome"]) for e in ents
                if e.get("label") == "Gene" and e.get("chromosome")}
    return pheno_of, genes_of, subsumes, trait_chr, gene_chr


def nominate(trait, pheno_of, genes_of, subsumes, hide=None):
    """gene -> set of the trait's phenotypes that reach it."""
    score: dict[str, set[str]] = defaultdict(set)
    via: dict[str, set[str]] = defaultdict(set)
    for ph in pheno_of.get(trait, ()):
        for other in set(pheno_of) | set(genes_of):
            if other in (trait, hide):
                continue
            if frozenset((trait, other)) in subsumes:
                continue          # definitional sharing, not evidence
            if ph not in pheno_of.get(other, ()):
                continue
            for gene, rank in genes_of.get(other, {}).items():
                if rank >= NOMINATION_FLOOR:
                    score[gene].add(ph)
                    via[gene].add(other)
    return score, via


def main(argv):
    pheno_of, genes_of, subsumes, trait_chr, gene_chr = load()
    targets = argv or sorted(set(pheno_of) | set(genes_of))

    for trait in targets:
        if trait not in pheno_of and trait not in genes_of:
            print(f"{trait}: not in the ontology")
            continue
        score, via = nominate(trait, pheno_of, genes_of, subsumes)
        own = set(genes_of.get(trait, {}))
        hits = {g: p for g, p in score.items() if g not in own}
        if not hits:
            continue

        tc = trait_chr.get(trait)
        print(f"\n{trait}  (chr{tc or '?'}; "
              f"{'known: ' + ', '.join(sorted(own)) if own else 'no gene yet'})")
        for gene, phs in sorted(hits.items(), key=lambda kv: -len(kv[1])):
            gc = gene_chr.get(gene)
            if tc and gc and tc != gc:
                verdict = f"VETOED (gene on chr{gc})"
            elif not tc or not gc:
                verdict = "no position to check"
            elif len(phs) >= 2:
                verdict = "CANDIDATE -- convergent"
            else:
                verdict = "insufficient: one phenotype is not evidence"
            print(f"  {gene:12} score={len(phs)}  via {', '.join(sorted(via[gene]))}")
            print(f"      {' + '.join(sorted(phs))}")
            print(f"      -> {verdict}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1:])
