"""Which genes do a trait's phenotypes reach, and which could be recorded?

Reads data/seed/*.yaml. No database. The rule itself lives in
`medaka_ontology.convergence`, which `validate` enforces; this script only shows
its working for one trait at a time.

A gene reaches a trait when another trait carries one of the same phenotypes
and has that gene on DIRECT or MAPPED evidence. It converges when it arrives
from at least 2 distinct neighbour traits (subsumes-linked traits count once)
AND rests on at least 2 distinct papers. Counting phenotypes instead is what
this script used to do; two phenotypes reaching one neighbour's gene through
one paper is one line of evidence, not two.

Convergence is decided first. Only a convergent gene gets the positional
check: a gene on a chromosome other than the trait's own GWAS interval cannot
be that trait's gene, and a trait with no interval has nothing to check with --
which means the gene cannot be recorded, not that it passes.

    python .claude/skills/trait-literature-search/scripts/converge.py [trait ...]

Run from any directory. The script puts this checkout's `src/` first on
sys.path, so a worktree reads its own code rather than the editable install.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SEED = REPO / "data" / "seed"
sys.path.insert(0, str(REPO / "src"))

from medaka_ontology.convergence import (  # noqa: E402
    MIN_NEIGHBOURS,
    MIN_PAPERS,
    GeneGraph,
    classify,
)
from medaka_ontology.loader import load_file  # noqa: E402
from medaka_ontology.models import SeedBundle  # noqa: E402


def load_seed(seed_dir: Path = SEED) -> SeedBundle:
    """Parse without cross-validating, so the script still runs while a seed
    edit is failing `validate` -- which is exactly when it is needed."""
    merged = SeedBundle(source_file=str(seed_dir))
    for path in sorted(seed_dir.glob("*.yaml")):
        bundle = load_file(path)
        merged.papers.extend(bundle.papers)
        merged.entities.extend(bundle.entities)
        merged.claims.extend(bundle.claims)
    return merged


def verdict(nom, position, gene_chr) -> str:
    if not nom.convergent:
        text = (f"insufficient: {len(nom.via)} neighbour(s), {len(nom.papers)} paper(s); "
                f"need {MIN_NEIGHBOURS} and {MIN_PAPERS}")
        if position == "vetoed":
            text += f" (and off-chromosome: gene on chr{gene_chr})"
        return text
    if position == "vetoed":
        return f"VETOED (gene on chr{gene_chr})"
    if position == "unknown":
        return "convergent, but no position to check -- not recordable as a gene claim"
    return "CANDIDATE -- convergent and on the trait's chromosome"


def main(argv):
    graph = GeneGraph(load_seed())
    explicit = bool(argv)
    targets = argv or graph.traits
    empty = []

    for trait in targets:
        if trait not in graph.traits:
            print(f"{trait}: not in the ontology")
            continue
        own = graph.gene_claims.get(trait, {})
        hits = {g: n for g, n in graph.nominate(trait).items() if g not in own}
        if not hits:
            if explicit:
                print(f"\n{trait}: no candidates ({len(graph.phenotypes.get(trait, ()))} "
                      "phenotype(s), none shared with a trait whose gene is DIRECT or MAPPED)")
            else:
                empty.append(trait)
            continue

        chrs = sorted(graph.trait_chromosomes.get(trait, ()))
        known = ", ".join(f"{g} [{classify(c).value}]" for g, c in sorted(own.items()))
        print(f"\n{trait}  (chr{'/'.join(chrs) or '?'}; "
              f"{'known: ' + known if own else 'no gene yet'})")
        ranked = sorted(hits.values(),
                        key=lambda n: (n.convergent, len(n.via), len(n.papers)), reverse=True)
        for nom in ranked:
            position = graph.position(trait, nom.gene)
            print(f"  {nom.gene:12} neighbours={len(nom.via)} papers={len(nom.papers)}  "
                  f"via {', '.join(sorted(nom.neighbours))}")
            print(f"      {' + '.join(sorted(nom.phenotypes))}  [{', '.join(sorted(nom.papers))}]")
            print(f"      -> {verdict(nom, position, graph.gene_chromosome.get(nom.gene))}")

    if empty:
        print(f"\nno candidates: {', '.join(empty)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1:])
