"""Does the rule still recover the answers we already know?

Hides the genes of one trait that already has them, then asks whether its own
phenotypes recover the hidden gene through other traits. A rule that cannot
recover answers we have has no business producing answers we do not.

The numbers are compared against `validate_rule.baseline.json` beside this
script, and `tests/test_convergence.py` makes the same comparison, so a drift
fails the suite rather than waiting for someone to re-read a docstring. When a
change is meant to move them, re-run with `--update-baseline` and say why in
the commit.

If a change makes the veto remove a correct nomination, the change is wrong.

    python .claude/skills/trait-literature-search/scripts/validate_rule.py
    python .claude/skills/trait-literature-search/scripts/validate_rule.py --update-baseline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from converge import load_seed  # noqa: E402

from medaka_ontology.convergence import leave_one_out  # noqa: E402

BASELINE = Path(__file__).with_name("validate_rule.baseline.json")


def main(argv):
    result = leave_one_out(load_seed())
    rows = result["rows"]

    print("=== leave-one-out ===\n")
    for trait in sorted({r["trait"] for r in rows}):
        mine = [r for r in rows if r["trait"] == trait]
        got = any(r["correct"] for r in mine)
        top = ", ".join(f"{r['gene']}({r['neighbours']}n/{r['papers']}p)" for r in
                        sorted(mine, key=lambda r: (-r["neighbours"], -r["papers"]))[:4])
        print(f"  {trait:18} {'RECOVERED' if got else 'miss':10} {top}")
    print(f"\n  {result['correct']}/{result['nominations']} nominations correct "
          f"across {result['traits_tested']} traits")

    print("\n=== convergent (>=2 neighbours and >=2 papers) ===")
    print(f"  {result['convergent_correct']} correct / {result['convergent']} convergent"
          + ("  -- precision UNMEASURED: the branch never fires" if not result["convergent"]
             else ""))

    print("\n=== positional veto ===")
    print(f"  kept {result['veto_kept']} ({result['veto_kept_wrong']} of them wrong)")
    print(f"  vetoed {result['vetoed']} ({result['vetoed_correct']} of them CORRECT "
          "-- must stay 0)")

    if "--update-baseline" in argv:
        BASELINE.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\n  baseline written to {BASELINE.name}")
        return 0

    status = 0
    if result["vetoed_correct"]:
        print("\n  REGRESSION: the veto is removing a correct nomination.")
        status = 1
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if baseline != result:
        drift = [k for k in result if k != "rows" and result[k] != baseline.get(k)]
        print(f"\n  DRIFT from {BASELINE.name}: {', '.join(drift) or 'rows'}")
        status = 1
    else:
        print(f"\n  matches {BASELINE.name}")
    return status


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
