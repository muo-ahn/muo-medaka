"""Does the rule still recover the answers we already know?

Hides the genes of one trait that already has them, then asks whether its own
phenotypes recover the hidden gene through other traits. A rule that cannot
recover answers we have has no business producing answers we do not.

Run this after changing phenotypes, the nomination floor, or the veto. The
numbers it printed when the rule was adopted:

    single shared phenotype  ->  3 of 12 nominations correct
    two or more phenotypes   ->  never fires (0 recall)
    positional veto          ->  removes 5 wrong, 0 correct

If a change makes the veto remove a correct nomination, the change is wrong.

    python .claude/skills/trait-literature-search/scripts/validate_rule.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from converge import RANK, load, nominate  # noqa: E402

#: A trait counts as having a known answer only at fine-mapping or better.
TRUTH_FLOOR = RANK["FINE_MAPPING"]


def main():
    pheno_of, genes_of, subsumes, trait_chr, gene_chr = load()
    traits = sorted(set(pheno_of) | set(genes_of))

    rows = []
    for trait in traits:
        truth = {g for g, r in genes_of.get(trait, {}).items() if r >= TRUTH_FLOOR}
        if not truth or not pheno_of.get(trait):
            continue
        score, _ = nominate(trait, pheno_of, genes_of, subsumes, hide=trait)
        for gene, phs in score.items():
            rows.append((trait, gene, gene in truth, len(phs)))

    print("=== leave-one-out ===\n")
    tested = sorted({r[0] for r in rows})
    for trait in tested:
        mine = [r for r in rows if r[0] == trait]
        got = [r for r in mine if r[2]]
        top = ", ".join(f"{g}({n})" for _, g, _, n in
                        sorted(mine, key=lambda r: -r[3])[:4])
        print(f"  {trait:18} {'RECOVERED' if got else 'miss':10} {top}")

    ok = sum(1 for r in rows if r[2])
    print(f"\n  {ok}/{len(rows)} nominations correct across {len(tested)} traits")

    by_score = defaultdict(lambda: [0, 0])
    for _, _, correct, n in rows:
        by_score[n][0 if correct else 1] += 1
    print("\n=== by convergence score ===")
    for n in sorted(by_score):
        good, bad = by_score[n]
        print(f"  score {n}: {good} correct / {good + bad} nominations")

    kept = vetoed = bad_kept = good_vetoed = 0
    for trait, gene, correct, _ in rows:
        tc, gc = trait_chr.get(trait), gene_chr.get(gene)
        if tc is None or gc is None:
            continue
        if tc == gc:
            kept += 1
            bad_kept += not correct
        else:
            vetoed += 1
            good_vetoed += correct
    print("\n=== positional veto ===")
    print(f"  kept {kept} ({bad_kept} of them wrong)")
    print(f"  vetoed {vetoed} ({good_vetoed} of them CORRECT -- must stay 0)")
    if good_vetoed:
        print("\n  REGRESSION: the veto is removing a correct nomination.")
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
