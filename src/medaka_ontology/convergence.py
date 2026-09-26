"""Whether an `associated_with_gene` claim on a trait has earned its gene.

PRD §8: the failure this repo exists to prevent is a gene name becoming folk
knowledge because one word appeared in two sentences. Measured on the traits
whose answer is known, a single shared phenotype nominates the right gene 3
times in 12. So a gene claim is sorted by *how* it was reached, and only the
claims that were reached by inference have to show convergence:

- DIRECT -- the gene was identified in medaka by an experiment that isolates
  it: positional cloning, mutant mapping, rescue, genome editing, somatic
  reversion. Such a claim needs nothing from other traits.
- MAPPED -- a medaka association study put the gene under the trait's own
  signal. Not causal, but not borrowed from another trait either.
- UNASSERTED -- no supporting evidence above UNKNOWN. These record an
  attribution the repo could not resolve (a seed paper's Table 1 citing a gene
  it never tested), and they are exempt: they assert nothing to check.
- INFERRED -- everything else. The gene reached the trait from somewhere else,
  so it must converge (>=2 independent neighbour traits, >=2 distinct papers)
  and survive the positional check.

Species must be stated, not defaulted. `Evidence.species` defaults to medaka so
that comparative findings stand out, but that default is exactly what lets a
zebrafish result read as a medaka one if the author forgets the field. DIRECT
and MAPPED therefore require the field to have been set explicitly, and the
loader refuses a medaka-subject claim whose strong evidence leaves it unset.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum

from .models import Claim, Evidence, SeedBundle
from .vocabulary import EVIDENCE_RANK, EvidenceLevel, NodeLabel, Predicate, Stance

#: Experiments that identify a gene in medaka rather than argue for it. Closed on
#: purpose: `mutant characterization` and `expression analysis` describe a gene
#: already assumed to be the right one, and `GWAS candidate nomination` picks a
#: gene out of an interval by its GO term.
DIRECT_EXPERIMENTS: frozenset[str] = frozenset(
    {
        "positional cloning",
        "mutant mapping",
        "mutant rescue",
        "transgenic rescue",
        "genome editing",
        "somatic reversion analysis",
    }
)

DIRECT_LEVELS = frozenset({EvidenceLevel.CAUSAL_VARIANT, EvidenceLevel.FUNCTIONAL_VALIDATION})
MAPPED_LEVELS = frozenset({EvidenceLevel.FINE_MAPPING, EvidenceLevel.QTL_GWAS_ASSOCIATION})

#: Convergence thresholds for an INFERRED claim.
MIN_NEIGHBOURS = 2
MIN_PAPERS = 2

#: INFERRED claims that fail the rule today and are being fixed in the data, not
#: here. Pinned by `tests/test_convergence.py` in both directions: a new violation
#: fails the suite, and so does an entry that has stopped violating, so this list
#: can only shrink by the data actually being corrected.
#:
#: Empty. Its one entry, leucophore free -> sox5, was a data error: nagao2014
#: (PMID 24699463) cloned sox5 from ml-3 (many leucophores-3), and kimura2014
#: (PMID 24803434) cloned lf as slc2a15b. The seed now records both.
KNOWN_VIOLATIONS: frozenset[tuple[str, str]] = frozenset()


class GeneBasis(StrEnum):
    DIRECT = "DIRECT"
    MAPPED = "MAPPED"
    UNASSERTED = "UNASSERTED"
    INFERRED = "INFERRED"


def states_medaka(ev: Evidence) -> bool:
    """True only when the author wrote the species down and it is medaka."""
    return "species" in ev.model_fields_set and not ev.is_comparative


def _supporting(claim: Claim) -> list[Evidence]:
    return [e for e in claim.evidence if e.stance is Stance.SUPPORTS]


def is_direct(ev: Evidence) -> bool:
    return (
        ev.stance is Stance.SUPPORTS
        and ev.level in DIRECT_LEVELS
        and states_medaka(ev)
        and ev.experiment_type.strip().lower() in DIRECT_EXPERIMENTS
    )


def is_mapped(ev: Evidence) -> bool:
    return ev.stance is Stance.SUPPORTS and ev.level in MAPPED_LEVELS and states_medaka(ev)


def classify(claim: Claim) -> GeneBasis:
    if claim.strongest_support is EvidenceLevel.UNKNOWN:
        return GeneBasis.UNASSERTED
    if any(is_direct(e) for e in claim.evidence):
        return GeneBasis.DIRECT
    if any(is_mapped(e) for e in claim.evidence):
        return GeneBasis.MAPPED
    return GeneBasis.INFERRED


def support_rank(claim: Claim) -> int:
    """Strongest SUPPORTS level. CONTRADICTS evidence never raises a rank."""
    return max((e.rank for e in _supporting(claim)), default=EVIDENCE_RANK[EvidenceLevel.UNKNOWN])


@dataclass
class Nomination:
    """One gene reaching a trait through the trait's phenotypes."""

    gene: str
    phenotypes: set[str] = field(default_factory=set)
    #: Neighbour traits by name, for display.
    neighbours: set[str] = field(default_factory=set)
    #: Neighbour traits counted once per subsumes-component: yellow, white,
    #: kouhaku and YWKo share phenotypes by construction and are one neighbour.
    via: set[str] = field(default_factory=set)
    #: Distinct papers behind the neighbours' gene claims. Two neighbours that
    #: both got their gene from one GWAS are one line of evidence, not two.
    papers: set[str] = field(default_factory=set)

    @property
    def convergent(self) -> bool:
        return len(self.via) >= MIN_NEIGHBOURS and len(self.papers) >= MIN_PAPERS


class GeneGraph:
    """The slice of a seed bundle the convergence rule reads."""

    def __init__(self, bundle: SeedBundle):
        entities = {e.id: e for e in bundle.entities}
        self.phenotypes: dict[str, set[str]] = defaultdict(set)
        self.gene_claims: dict[str, dict[str, Claim]] = defaultdict(dict)
        self.trait_chromosomes: dict[str, set[str]] = defaultdict(set)
        self.gene_chromosome: dict[str, str] = {
            e.name: str(e.chromosome)
            for e in bundle.entities
            if e.label is NodeLabel.GENE and e.chromosome
        }
        parent: dict[str, str] = {}

        def root(name: str) -> str:
            while parent.get(name, name) != name:
                name = parent[name]
            return name

        for claim in bundle.claims:
            if claim.subject.label is not NodeLabel.ORNAMENTAL_TRAIT:
                continue
            subject, obj = claim.subject.name, claim.object.name
            supporting = _supporting(claim)
            if claim.predicate is Predicate.HAS_PHENOTYPE and supporting:
                self.phenotypes[subject].add(obj)
            elif claim.predicate is Predicate.ASSOCIATED_WITH_GENE:
                self.gene_claims[subject][obj] = claim
            elif claim.predicate is Predicate.SUBSUMES:
                parent[root(subject)] = root(obj)
            elif claim.predicate is Predicate.ASSOCIATED_WITH_LOCUS and supporting:
                locus = entities.get(claim.object.id)
                if locus is not None and locus.chromosome:
                    self.trait_chromosomes[subject].add(str(locus.chromosome))
        self._root = root

    @property
    def traits(self) -> list[str]:
        return sorted(set(self.phenotypes) | set(self.gene_claims))

    def nominate(self, trait: str, hide: str | None = None) -> dict[str, Nomination]:
        """gene -> how the trait's phenotypes reach it through other traits.

        Only DIRECT or MAPPED neighbour claims nominate: an inferred gene
        seeding further inference is how one guess becomes two.
        """
        own_component = self._root(trait)
        out: dict[str, Nomination] = {}
        for phenotype in self.phenotypes.get(trait, ()):
            for other in self.traits:
                if other in (trait, hide):
                    continue
                if self._root(other) == own_component:
                    continue  # definitional sharing across subsumes, not evidence
                if phenotype not in self.phenotypes.get(other, ()):
                    continue
                for gene, claim in self.gene_claims.get(other, {}).items():
                    basis = classify(claim)
                    if basis is GeneBasis.DIRECT:
                        papers = {e.paper for e in claim.evidence if is_direct(e)}
                    elif basis is GeneBasis.MAPPED:
                        papers = {e.paper for e in claim.evidence if is_mapped(e)}
                    else:
                        continue
                    nom = out.setdefault(gene, Nomination(gene))
                    nom.phenotypes.add(phenotype)
                    nom.neighbours.add(other)
                    nom.via.add(self._root(other))
                    nom.papers |= papers
        return out

    def position(self, trait: str, gene: str) -> str:
        """`consistent`, `vetoed`, or `unknown` when either side has no chromosome."""
        trait_chrs = self.trait_chromosomes.get(trait)
        gene_chr = self.gene_chromosome.get(gene)
        if not trait_chrs or not gene_chr:
            return "unknown"
        return "consistent" if gene_chr in trait_chrs else "vetoed"


def gene_claim_violations(bundle: SeedBundle) -> dict[tuple[str, str], str]:
    """(trait, gene) -> why the claim has not earned its gene.

    INFERRED claims need convergence and a consistent position; an unknown
    position is not support. MAPPED claims need only the position not to
    contradict them. DIRECT and UNASSERTED claims are not checked here.
    """
    graph = GeneGraph(bundle)
    problems: dict[tuple[str, str], str] = {}
    for trait, claims in graph.gene_claims.items():
        for gene, claim in claims.items():
            basis = classify(claim)
            position = graph.position(trait, gene)
            if basis is GeneBasis.MAPPED and position == "vetoed":
                problems[(trait, gene)] = "mapped gene lies off the trait's GWAS chromosome"
            elif basis is GeneBasis.INFERRED:
                nom = graph.nominate(trait).get(gene)
                if nom is None or not nom.convergent:
                    via = len(nom.via) if nom else 0
                    papers = len(nom.papers) if nom else 0
                    problems[(trait, gene)] = (
                        f"inferred gene without convergence ({via} neighbour trait(s), "
                        f"{papers} paper(s); need {MIN_NEIGHBOURS} and {MIN_PAPERS}) -- "
                        "if a medaka experiment identified it, record the experiment "
                        "with an explicit species and a direct experiment_type"
                    )
                elif position != "consistent":
                    problems[(trait, gene)] = (
                        f"inferred gene without positional support ({position})"
                    )
    return problems


#: A trait counts as having a known answer at fine-mapping or better.
TRUTH_FLOOR = EVIDENCE_RANK[EvidenceLevel.FINE_MAPPING]


def leave_one_out(bundle: SeedBundle) -> dict:
    """Hide each known-answer trait's genes and ask whether the rule recovers them.

    A rule that cannot recover answers we have has no business producing answers
    we do not. The result is plain data so a baseline can be stored and diffed.
    """
    graph = GeneGraph(bundle)
    rows = []
    for trait in graph.traits:
        truth = {
            g for g, c in graph.gene_claims.get(trait, {}).items() if support_rank(c) >= TRUTH_FLOOR
        }
        if not truth or not graph.phenotypes.get(trait):
            continue
        for gene, nom in sorted(graph.nominate(trait, hide=trait).items()):
            rows.append(
                {
                    "trait": trait,
                    "gene": gene,
                    "correct": gene in truth,
                    "neighbours": len(nom.via),
                    "papers": len(nom.papers),
                    "convergent": nom.convergent,
                    "position": graph.position(trait, gene),
                }
            )
    convergent = [r for r in rows if r["convergent"]]
    return {
        "traits_tested": len({r["trait"] for r in rows}),
        "nominations": len(rows),
        "correct": sum(r["correct"] for r in rows),
        "convergent": len(convergent),
        "convergent_correct": sum(r["correct"] for r in convergent),
        "veto_kept": sum(r["position"] == "consistent" for r in rows),
        "veto_kept_wrong": sum(r["position"] == "consistent" and not r["correct"] for r in rows),
        "vetoed": sum(r["position"] == "vetoed" for r in rows),
        "vetoed_correct": sum(r["position"] == "vetoed" and r["correct"] for r in rows),
        "rows": rows,
    }


__all__ = [
    "DIRECT_EXPERIMENTS",
    "KNOWN_VIOLATIONS",
    "GeneBasis",
    "GeneGraph",
    "Nomination",
    "classify",
    "gene_claim_violations",
    "leave_one_out",
    "states_medaka",
]
