"""The cross query: from two parents' genotypes (or what they show) to the
offspring's genotypes and traits. ADR 0006.

This is a *validation* query. PRD §14 lists a Mendelian cross simulator and
offspring phenotype prediction as non-goals; this module exists to show that the
genetic layer in 13-entities-genetics.yaml and 24-claims-inheritance.yaml says
enough to reproduce published crosses (tests/test_genetics.py, AC-8), not to be a
breeding tool. It recommends nothing and plans nothing. Lifting the non-goal is
the user's decision (ADR 0006).

It reads the loaded `SeedBundle` and nothing else, so it needs no Neo4j and cannot
see anything the seed does not claim. Every rule is a claim:

    loci            objects of `allele_of`; a locus's alleles are its subjects
    wild type       the allele whose entity says `variant_type: wild type`
    dominance       `dominant_over`, `incompletely_dominant_over` between alleles
    sex linkage     `inherited_as sex-linked` on the locus
    traits          `requires_allele`: expressed iff every required allele is
    masking         `masks`: an expressed masker hides the masked trait
    strains         `composed_of`: expressed iff every part is
    refusals        `inherited_as multilocus`: not predicted, said so

Probabilities are `fractions.Fraction`, so 9:3:3:1 is 9/16 and not 0.5625, and a
test can assert equality.

Assumptions the code makes and every result states (the ones that matter are
listed in `CrossResult.assumptions`):

  * sex is 1:1 (XY, dmy on the Y);
  * loci that are not sex-linked assort independently; no `linked_to` claim is
    used for anything, because no source gives a recombination fraction;
  * a sex-linked locus is completely linked to sex: the father's Y allele goes to
    his sons and his X allele to his daughters (spec 열린 결정: the r-dmy rate is
    zero, because no source gives one);
  * a locus the caller does not give is homozygous wild type.
"""

from __future__ import annotations

import itertools
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction

from .models import Claim, SeedBundle
from .vocabulary import EVIDENCE_RANK, EvidenceLevel, NodeLabel, Predicate

SEX_LINKED = "sex-linked"
MULTILOCUS = "multilocus"
WILD_TYPE = "wild type"
#: Class label for an offspring that shows none of the traits the model can express.
NO_TRAIT = "none of the modelled traits"


class ModelError(ValueError):
    """The seed's genetic layer is inconsistent, or the caller's input is."""


class NotPredictable(ModelError):
    """A trait the model cannot reason about, with the reason a reader can act on."""


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


class State(StrEnum):
    """How far an allele or trait is expressed in one genotype."""

    EXPRESSED = "expressed"
    PARTIAL = "partial"  # incomplete dominance: the heterozygote is intermediate
    ABSENT = "absent"
    UNKNOWN = "unknown"  # a heterozygote whose two alleles have no dominance edge


@dataclass(frozen=True)
class Allele:
    symbol: str
    name: str
    locus: str
    wild_type: bool


@dataclass
class LocusInfo:
    name: str
    alleles: dict[str, Allele] = field(default_factory=dict)
    sex_linked: bool = False
    claims: list[Claim] = field(default_factory=list)

    @property
    def wild(self) -> Allele:
        wild = [a for a in self.alleles.values() if a.wild_type]
        if len(wild) != 1:
            raise ModelError(
                f"locus {self.name!r} has {len(wild)} wild-type alleles; the cross query "
                "needs exactly one to default unspecified genotypes"
            )
        return wild[0]


@dataclass(frozen=True)
class Genotype:
    """One individual at every locus. `pairs` is sorted by locus.

    For a locus that is not sex-linked, or for a female, the two alleles are
    sorted by symbol (their order carries no meaning). For a male at a sex-linked
    locus they are (X allele, Y allele) and the order is the point.
    """

    sex: Sex
    pairs: tuple[tuple[str, tuple[str, str]], ...]

    def at(self, locus: str) -> tuple[str, str]:
        for name, pair in self.pairs:
            if name == locus:
                return pair
        raise KeyError(locus)


@dataclass
class PhenotypeCall:
    states: dict[str, State]
    visible: tuple[str, ...]
    shown: frozenset[str]  # trait names visible and at least partly expressed
    masked: frozenset[str]
    absorbed: dict[str, tuple[str, ...]]


ClassKey = tuple[str, ...]


@dataclass
class TraitSupport:
    """The weakest link under one trait's prediction. ADR 0006."""

    trait: str
    level: EvidenceLevel
    weakest: str  # "predicate subject -> object"
    claims: int


@dataclass
class CrossResult:
    mother: str
    father: str
    loci: list[str]
    by_sex: dict[Sex, dict[ClassKey, Fraction]]
    overall: dict[ClassKey, Fraction]
    genotypes: dict[Sex, dict[str, Fraction]]
    support: dict[str, TraitSupport]
    inferred_steps: list[str]
    assumptions: list[str]
    unpredictable: dict[str, str]
    no_data: list[str]


@dataclass
class RangeResult:
    """A cross from what the parents show: each class's share is a range."""

    mother: list[str]
    father: list[str]
    n_mother: int
    n_father: int
    by_sex: dict[Sex, dict[ClassKey, tuple[Fraction, Fraction]]]
    overall: dict[ClassKey, tuple[Fraction, Fraction]]
    support: dict[str, TraitSupport]
    assumptions: list[str]
    unpredictable: dict[str, str]
    no_data: list[str]


def _weakest(claims: Iterable[Claim]) -> tuple[EvidenceLevel, Claim] | None:
    best: tuple[EvidenceLevel, Claim] | None = None
    for claim in claims:
        level = claim.strongest_support
        if best is None or EVIDENCE_RANK[level] < EVIDENCE_RANK[best[0]]:
            best = (level, claim)
    return best


def _describe(claim: Claim) -> str:
    return f"{claim.predicate.value} {claim.subject.name} -> {claim.object.name}"


def _combine(states: Iterable[State]) -> State:
    """Conjunction over tri-state values: one definite absence settles it."""
    states = list(states)
    if any(s is State.ABSENT for s in states):
        return State.ABSENT
    if any(s is State.UNKNOWN for s in states):
        return State.UNKNOWN
    if any(s is State.PARTIAL for s in states):
        return State.PARTIAL
    return State.EXPRESSED


class GeneticModel:
    """The genetic layer of a seed bundle, ready to cross."""

    def __init__(self, bundle: SeedBundle) -> None:
        self.loci: dict[str, LocusInfo] = {}
        self.by_symbol: dict[str, Allele] = {}
        self.by_name: dict[str, Allele] = {}
        #: (dominant symbol, other symbol) -> (kind, claim)
        self.dominance: dict[tuple[str, str], tuple[State, Claim]] = {}
        self.requires: dict[str, list[tuple[Allele, Claim]]] = defaultdict(list)
        #: masked trait -> [(masker, claim)]
        self.masked_by: dict[str, list[tuple[str, Claim]]] = defaultdict(list)
        self.parts: dict[str, list[tuple[str, Claim]]] = defaultdict(list)
        self.modes: dict[str, list[tuple[str, Claim]]] = defaultdict(list)
        self.linked: list[Claim] = []
        self.ornamental: list[str] = [
            e.name for e in bundle.entities if e.label is NodeLabel.ORNAMENTAL_TRAIT
        ]
        entities = {(e.label, e.name): e for e in bundle.entities}

        for claim in bundle.claims:
            if claim.predicate is Predicate.ALLELE_OF:
                self._add_allele(claim, entities)
        for claim in bundle.claims:
            p, s, o = claim.predicate, claim.subject.name, claim.object.name
            if p is Predicate.DOMINANT_OVER:
                self.dominance[self._sym(s), self._sym(o)] = (State.EXPRESSED, claim)
            elif p is Predicate.INCOMPLETELY_DOMINANT_OVER:
                self.dominance[self._sym(s), self._sym(o)] = (State.PARTIAL, claim)
            elif p is Predicate.REQUIRES_ALLELE:
                self.requires[s].append((self.by_name[o], claim))
            elif p is Predicate.MASKS:
                self.masked_by[o].append((s, claim))
            elif p is Predicate.COMPOSED_OF:
                self.parts[s].append((o, claim))
            elif p is Predicate.INHERITED_AS:
                self.modes[s].append((o, claim))
                if o == SEX_LINKED and s in self.loci:
                    self.loci[s].sex_linked = True
                    self.loci[s].claims.append(claim)
            elif p is Predicate.LINKED_TO:
                self.linked.append(claim)

    # ------------------------------------------------------------------ building

    def _sym(self, name: str) -> str:
        try:
            return self.by_name[name].symbol
        except KeyError:
            raise ModelError(
                f"dominance names {name!r}, which is not an allele_of subject"
            ) from None

    def _add_allele(self, claim: Claim, entities: dict) -> None:
        entity = entities[(claim.subject.label, claim.subject.name)]
        if not entity.symbol:
            raise ModelError(f"allele {entity.name!r} has no `symbol`; a genotype is written in it")
        locus = self.loci.setdefault(claim.object.name, LocusInfo(claim.object.name))
        allele = Allele(entity.symbol, entity.name, locus.name, entity.variant_type == WILD_TYPE)
        if entity.symbol in self.by_symbol and self.by_symbol[entity.symbol] != allele:
            raise ModelError(f"symbol {entity.symbol!r} names two alleles")
        locus.alleles[entity.symbol] = allele
        self.by_symbol[entity.symbol] = allele
        self.by_name[entity.name] = allele

    # ------------------------------------------------------------------ genotypes

    def _canonical(self, locus: str, pair: tuple[str, str], sex: Sex) -> tuple[str, str]:
        if self.loci[locus].sex_linked and sex is Sex.MALE:
            return pair
        return (pair[0], pair[1]) if pair[0] <= pair[1] else (pair[1], pair[0])

    def genotype(self, sex: Sex, given: dict[str, tuple[str, str]]) -> Genotype:
        pairs = []
        for name, locus in sorted(self.loci.items()):
            pair = given.get(name, (locus.wild.symbol, locus.wild.symbol))
            pairs.append((name, self._canonical(name, pair, sex)))
        return Genotype(sex, tuple(pairs))

    def parse(self, text: str, sex: Sex) -> Genotype:
        """`b/b r/R` -> a genotype. Unspecified loci are homozygous wild type.

        One `a/b` token per locus. At a sex-linked locus a male's token is
        X allele first, Y allele second, so `r/R` is X^r Y^R. A female's is her
        two X alleles.
        """
        given: dict[str, tuple[str, str]] = {}
        for token in re.split(r"[\s,;]+", text.strip()):
            if not token:
                continue
            parts = token.split("/")
            if len(parts) != 2 or not all(parts):
                raise ModelError(f"{token!r}: write each locus as two alleles, like b/b")
            alleles = []
            for sym in parts:
                if sym not in self.by_symbol:
                    known = ", ".join(sorted(self.by_symbol))
                    raise ModelError(f"unknown allele {sym!r}; known symbols: {known}")
                alleles.append(self.by_symbol[sym])
            if alleles[0].locus != alleles[1].locus:
                raise ModelError(
                    f"{token!r}: {parts[0]} is an allele of {alleles[0].locus!r} and "
                    f"{parts[1]} of {alleles[1].locus!r}"
                )
            locus = alleles[0].locus
            if locus in given:
                raise ModelError(f"locus {locus!r} given twice")
            given[locus] = (parts[0], parts[1])
        return self.genotype(sex, given)

    def show(self, g: Genotype, loci: Iterable[str] | None = None) -> str:
        """`b/b X^r Y^R`; the loci a reader needs, not all eight."""
        chosen = set(loci) if loci is not None else {n for n, p in g.pairs if not self._is_wild(p)}
        out = []
        for name, pair in g.pairs:
            if name not in chosen:
                continue
            if self.loci[name].sex_linked:
                x, y = pair
                out.append(f"X^{x} X^{y}" if g.sex is Sex.FEMALE else f"X^{x} Y^{y}")
            else:
                out.append(f"{pair[0]}/{pair[1]}")
        return " ".join(out) or "wild type throughout"

    def _is_wild(self, pair: tuple[str, str]) -> bool:
        return all(self.by_symbol[s].wild_type for s in pair)

    # ----------------------------------------------------------------- expression

    def allele_state(self, symbol: str, pair: tuple[str, str]) -> State:
        """Is this allele expressed in a genotype at its locus?"""
        a, b = pair
        if symbol not in pair:
            return State.ABSENT
        if a == b:
            return State.EXPRESSED
        other = b if a == symbol else a
        if (symbol, other) in self.dominance:
            return self.dominance[symbol, other][0]
        if (other, symbol) in self.dominance:
            return (
                State.PARTIAL if self.dominance[other, symbol][0] is State.PARTIAL else State.ABSENT
            )
        return State.UNKNOWN

    def predictable(self, trait: str, _seen: frozenset[str] = frozenset()) -> bool:
        if trait in self.requires:
            return True
        if trait in self.parts and trait not in _seen:
            return all(self.predictable(t, _seen | {trait}) for t, _ in self.parts[trait])
        return False

    def trait_loci(self, trait: str) -> set[str]:
        if trait in self.requires:
            return {a.locus for a, _ in self.requires[trait]}
        loci: set[str] = set()
        for part, _ in self.parts.get(trait, []):
            loci |= self.trait_loci(part)
        return loci

    def raw_state(self, trait: str, g: Genotype) -> State:
        if trait in self.requires:
            return _combine(
                self.allele_state(a.symbol, g.at(a.locus)) for a, _ in self.requires[trait]
            )
        return _combine(self.raw_state(t, g) for t, _ in self.parts[trait])

    def phenotype(self, g: Genotype) -> PhenotypeCall:
        traits = [t for t in [*self.requires, *self.parts] if self.predictable(t)]
        raw = {t: self.raw_state(t, g) for t in traits}
        final = dict(raw)
        masked: set[str] = set()
        for victim, maskers in self.masked_by.items():
            if victim not in raw:
                continue
            for masker, _ in maskers:
                if masker not in raw:
                    continue
                if raw[masker] is State.EXPRESSED and raw[victim] is not State.ABSENT:
                    masked.add(victim)
                elif raw[masker] in (State.PARTIAL, State.UNKNOWN) and final[victim] in (
                    State.EXPRESSED,
                    State.PARTIAL,
                ):
                    final[victim] = State.UNKNOWN
        absorbed: dict[str, tuple[str, ...]] = {}
        for comp, parts in self.parts.items():
            if comp in raw and raw[comp] is State.EXPRESSED:
                absorbed[comp] = tuple(sorted(t for t, _ in parts))
        gone = {p for ps in absorbed.values() for p in ps}
        labels: list[str] = []
        shown: set[str] = set()
        for t in sorted(traits):
            if t in masked or t in gone:
                continue
            state = final[t]
            if state is State.EXPRESSED:
                labels.append(t)
                shown.add(t)
            elif state is State.PARTIAL:
                labels.append(f"{t} (partial)")
                shown.add(t)
            elif state is State.UNKNOWN:
                labels.append(f"{t}?")
        return PhenotypeCall(
            final,
            tuple(labels) or (NO_TRAIT,),
            frozenset(shown),
            frozenset(masked - gone),
            absorbed,
        )

    # ---------------------------------------------------------------- offspring

    @staticmethod
    def _gametes(pair: tuple[str, str]) -> dict[str, Fraction]:
        a, b = pair
        return {a: Fraction(1)} if a == b else {a: Fraction(1, 2), b: Fraction(1, 2)}

    def _locus_offspring(
        self, locus: str, mother: tuple[str, str], father: tuple[str, str], sex: Sex
    ) -> dict[tuple[str, str], Fraction]:
        out: dict[tuple[str, str], Fraction] = defaultdict(Fraction)
        for m, pm in self._gametes(mother).items():
            if self.loci[locus].sex_linked:
                # Complete linkage to sex: the Y allele goes to sons, the X to daughters.
                f = father[1] if sex is Sex.MALE else father[0]
                out[self._canonical(locus, (m, f), sex)] += pm
            else:
                for f, pf in self._gametes(father).items():
                    out[self._canonical(locus, (m, f), sex)] += pm * pf
        return out

    def offspring(self, mother: Genotype, father: Genotype, sex: Sex) -> dict[Genotype, Fraction]:
        if mother.sex is not Sex.FEMALE or father.sex is not Sex.MALE:
            raise ModelError("the first parent must be a female and the second a male")
        per_locus = [
            [
                (name, pair, p)
                for pair, p in self._locus_offspring(
                    name, mother.at(name), father.at(name), sex
                ).items()
            ]
            for name in sorted(self.loci)
        ]
        out: dict[Genotype, Fraction] = {}
        for combo in itertools.product(*per_locus):
            p = Fraction(1)
            for _, _, q in combo:
                p *= q
            out[Genotype(sex, tuple((n, pair) for n, pair, _ in combo))] = p
        return out

    def class_shares(
        self, mother: Genotype, father: Genotype, sex: Sex
    ) -> dict[ClassKey, Fraction]:
        shares: dict[ClassKey, Fraction] = defaultdict(Fraction)
        for g, p in self.offspring(mother, father, sex).items():
            shares[self.phenotype(g).visible] += p
        return dict(shares)

    # ----------------------------------------------------------------- evidence

    def support_claims(self, trait: str, _seen: frozenset[str] = frozenset()) -> list[Claim]:
        """Every claim a prediction for this trait can rest on. Static, so it errs
        toward the weaker side: a dominance edge counts even when the particular
        cross never reads it."""
        claims: list[Claim] = []
        if trait in self.requires:
            for allele, claim in self.requires[trait]:
                claims.append(claim)
                locus = self.loci[allele.locus]
                claims.extend(locus.claims)
                for x, y in itertools.permutations(locus.alleles, 2):
                    if (x, y) in self.dominance:
                        claims.append(self.dominance[x, y][1])
        elif trait in self.parts and trait not in _seen:
            for part, claim in self.parts[trait]:
                claims.append(claim)
                claims.extend(self.support_claims(part, _seen | {trait}))
        for _, claim in self.masked_by.get(trait, []):
            claims.append(claim)
        return list({c.id: c for c in claims}.values())

    def support(self, trait: str) -> TraitSupport:
        claims = self.support_claims(trait)
        weak = _weakest(claims)
        if weak is None:
            return TraitSupport(trait, EvidenceLevel.UNKNOWN, "no claims", 0)
        return TraitSupport(trait, weak[0], _describe(weak[1]), len(claims))

    # -------------------------------------------------------------- reporting

    def unpredictable_traits(self) -> tuple[dict[str, str], list[str]]:
        """Traits the query refuses, with why, and traits with no inheritance data."""
        refused: dict[str, str] = {}
        none: list[str] = []
        for trait in self.ornamental:
            if self.predictable(trait):
                continue
            modes = self.modes.get(trait, [])
            names = {m for m, _ in modes}
            if MULTILOCUS in names:
                papers = sorted({e.paper for m, c in modes if m == MULTILOCUS for e in c.evidence})
                refused[trait] = f"not predictable (multilocus, {', '.join(papers)})"
            elif modes:
                refused[trait] = (
                    f"inheritance recorded ({', '.join(sorted(names))}) but no allele model"
                )
            else:
                none.append(trait)
        return refused, sorted(none)

    def _assumptions(self, genotypes: list[Genotype], traits_shown: set[str]) -> list[str]:
        in_play = {name for g in genotypes for name, pair in g.pairs if not self._is_wild(pair)}
        notes = ["Offspring sex is 1:1 (XY; dmy on the Y)."]
        autosomal = sorted(n for n in in_play if not self.loci[n].sex_linked)
        if len(autosomal) > 1 or (autosomal and in_play - set(autosomal)):
            notes.append(
                "Loci assort independently. sasano2012 states b and r are unlinked; for "
                "the others no source gives a recombination fraction, and no `linked_to` "
                "claim is used."
            )
        for name in sorted(in_play):
            if self.loci[name].sex_linked:
                notes.append(
                    f"{name} is taken as completely linked to sex: a father's Y allele "
                    "goes to his sons and his X allele to his daughters (no source gives "
                    "a recombination rate between it and the sex-determining locus)."
                )
        notes.append("A locus not given is homozygous wild type.")
        seen: set[str] = set()
        for trait in sorted(traits_shown):
            for claim in self.support_claims(trait):
                if claim.strongest_support is EvidenceLevel.INFERRED and claim.interpretation:
                    text = " ".join(claim.interpretation.split())
                    if text not in seen:
                        seen.add(text)
                        notes.append(f"{trait} ({_describe(claim)}, INFERRED): {text}")
        for trait in sorted(traits_shown):
            for mode, claim in self.modes.get(trait, []):
                if claim.interpretation:
                    text = " ".join(claim.interpretation.split())
                    if text not in seen:
                        seen.add(text)
                        notes.append(f"{trait} ({mode}): {text}")
        return notes

    def _inferred_steps(self, traits: Iterable[str]) -> list[str]:
        steps: dict[str, None] = {}
        for trait in sorted(traits):
            for claim in self.support_claims(trait):
                if claim.strongest_support is EvidenceLevel.INFERRED:
                    steps[_describe(claim)] = None
        return list(steps)

    # ------------------------------------------------------------------- cross

    def cross(self, mother: str | Genotype, father: str | Genotype) -> CrossResult:
        m = mother if isinstance(mother, Genotype) else self.parse(mother, Sex.FEMALE)
        f = father if isinstance(father, Genotype) else self.parse(father, Sex.MALE)
        by_sex = {sex: self.class_shares(m, f, sex) for sex in Sex}
        overall: dict[ClassKey, Fraction] = defaultdict(Fraction)
        for shares in by_sex.values():
            for key, p in shares.items():
                overall[key] += p / 2
        in_play = [
            n for n in sorted(self.loci) if not (self._is_wild(m.at(n)) and self._is_wild(f.at(n)))
        ]
        genotypes: dict[Sex, dict[str, Fraction]] = {}
        for sex in Sex:
            dist: dict[str, Fraction] = defaultdict(Fraction)
            for g, p in self.offspring(m, f, sex).items():
                dist[self.show(g, in_play)] += p
            genotypes[sex] = dict(dist)
        traits = self._traits_in(by_sex.values())
        refused, none = self.unpredictable_traits()
        return CrossResult(
            self.show(m, in_play),
            self.show(f, in_play),
            in_play,
            by_sex,
            dict(overall),
            genotypes,
            {t: self.support(t) for t in sorted(traits)},
            self._inferred_steps(traits),
            self._assumptions([m, f], traits),
            refused,
            none,
        )

    @staticmethod
    def _traits_in(distributions: Iterable[dict[ClassKey, object]]) -> set[str]:
        traits: set[str] = set()
        for dist in distributions:
            for key in dist:
                for label in key:
                    if label != NO_TRAIT:
                        traits.add(re.sub(r"( \(partial\)|\?)$", "", label))
        return traits

    # --------------------------------------------------- from what parents show

    def _closure(self, shown: Iterable[str]) -> tuple[set[str], set[str]]:
        """The loci and traits that can change what `shown` looks like: the loci
        of the shown traits, every trait on those loci, and whatever masks any of
        them (an albino hides blue, so a blue fish is not albino)."""
        traits = set(shown)
        loci: set[str] = set()
        changed = True
        while changed:
            changed = False
            for t in list(traits):
                loci |= self.trait_loci(t)
            for t in [x for x in self.requires if x not in traits]:
                if self.trait_loci(t) & loci:
                    traits.add(t)
                    changed = True
            for t in list(traits):
                for masker, _ in self.masked_by.get(t, []):
                    if masker not in traits and self.predictable(masker):
                        traits.add(masker)
                        changed = True
        return loci, traits

    def hypotheses(
        self, shown: Iterable[str], sex: Sex, *, true_breeding: bool = False
    ) -> list[Genotype]:
        """Every genotype that shows exactly these traits, among those loci that
        can matter. Other loci are homozygous wild type. `true_breeding` keeps
        only homozygotes, the case of a fixed strain."""
        shown = set(shown)
        if not shown:
            raise ModelError("name at least one trait the parent shows, or give its genotype")
        refused, _ = self.unpredictable_traits()
        for trait in sorted(shown):
            if not self.predictable(trait):
                raise NotPredictable(
                    f"{trait}: {refused.get(trait, 'no inheritance data in the seed')}"
                )
        loci, traits = self._closure(shown)
        options = []
        for name in sorted(loci):
            symbols = sorted(self.loci[name].alleles)
            if self.loci[name].sex_linked and sex is Sex.MALE:
                pairs = list(itertools.product(symbols, repeat=2))
            else:
                pairs = list(itertools.combinations_with_replacement(symbols, 2))
            if true_breeding:
                pairs = [p for p in pairs if p[0] == p[1]]
            options.append([(name, p) for p in pairs])
        found = []
        for combo in itertools.product(*options):
            g = self.genotype(sex, dict(combo))
            if self.phenotype(g).shown & traits == shown:
                found.append(g)
        if not found:
            raise ModelError(
                f"no genotype shows exactly {sorted(shown)}"
                + (" and is homozygous" if true_breeding else "")
            )
        return found

    def cross_from_phenotypes(
        self,
        mother_shows: Iterable[str],
        father_shows: Iterable[str],
        *,
        true_breeding: bool = False,
    ) -> RangeResult:
        mothers = self.hypotheses(mother_shows, Sex.FEMALE, true_breeding=true_breeding)
        fathers = self.hypotheses(father_shows, Sex.MALE, true_breeding=true_breeding)
        per_cross: list[dict[Sex, dict[ClassKey, Fraction]]] = []
        for m, f in itertools.product(mothers, fathers):
            per_cross.append({sex: self.class_shares(m, f, sex) for sex in Sex})

        def span(
            dists: list[dict[ClassKey, Fraction]],
        ) -> dict[ClassKey, tuple[Fraction, Fraction]]:
            keys = {k for d in dists for k in d}
            return {
                k: (
                    min(d.get(k, Fraction(0)) for d in dists),
                    max(d.get(k, Fraction(0)) for d in dists),
                )
                for k in keys
            }

        by_sex = {sex: span([c[sex] for c in per_cross]) for sex in Sex}
        overall = span(
            [
                {
                    k: (c[Sex.FEMALE].get(k, Fraction(0)) + c[Sex.MALE].get(k, Fraction(0))) / 2
                    for k in {*c[Sex.FEMALE], *c[Sex.MALE]}
                }
                for c in per_cross
            ]
        )
        traits = self._traits_in([*by_sex.values()])
        refused, none = self.unpredictable_traits()
        return RangeResult(
            sorted(mother_shows),
            sorted(father_shows),
            len(mothers),
            len(fathers),
            by_sex,
            overall,
            {t: self.support(t) for t in sorted(traits)},
            [
                *self._assumptions([*mothers[:1], *fathers[:1]], traits),
                "The parents' genotypes are not known: every genotype that shows exactly "
                "the stated traits, over the loci that can change them, is a hypothesis, and "
                "each class is a range over the crosses of all hypotheses"
                + (" (homozygotes only, as for a fixed strain)." if true_breeding else "."),
            ],
            refused,
            none,
        )


# ------------------------------------------------------------------- formatting


def _pct(p: Fraction) -> str:
    return f"{p} ({float(p) * 100:.1f}%)"


def _name(key: ClassKey) -> str:
    return " + ".join(key)


def format_cross(result: CrossResult) -> str:
    lines = [f"mother  {result.mother}", f"father  {result.father}", ""]
    for sex in Sex:
        lines.append(f"{sex.value} offspring (within sex)")
        for key, p in sorted(result.by_sex[sex].items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {_pct(p):>14}  {_name(key)}")
        genos = result.genotypes[sex]
        lines.append("  genotypes: " + "; ".join(f"{g} {p}" for g, p in sorted(genos.items())))
    lines += ["", "overall (sex 1:1)"]
    for key, p in sorted(result.overall.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {_pct(p):>14}  {_name(key)}")
    lines += _tail(
        result.support,
        result.inferred_steps,
        result.assumptions,
        result.unpredictable,
        result.no_data,
    )
    return "\n".join(lines)


def format_range(result: RangeResult) -> str:
    lines = [
        f"mother shows {', '.join(result.mother)} ({result.n_mother} genotype hypotheses)",
        f"father shows {', '.join(result.father)} ({result.n_father} genotype hypotheses)",
        "",
    ]
    for sex in Sex:
        lines.append(f"{sex.value} offspring (min - max over hypotheses)")
        for key, (lo, hi) in sorted(result.by_sex[sex].items(), key=lambda kv: (-kv[1][1], kv[0])):
            lines.append(f"  {lo} - {hi}  {_name(key)}")
    lines += ["", "overall (sex 1:1)"]
    for key, (lo, hi) in sorted(result.overall.items(), key=lambda kv: (-kv[1][1], kv[0])):
        lines.append(f"  {lo} - {hi}  {_name(key)}")
    lines += _tail(result.support, [], result.assumptions, result.unpredictable, result.no_data)
    return "\n".join(lines)


def _tail(support, inferred, assumptions, unpredictable, no_data) -> list[str]:
    lines = ["", "evidence (weakest claim under each predicted trait)"]
    for t, s in support.items():
        lines.append(f"  {t}: {s.level.value} <- {s.weakest} ({s.claims} claims)")
    if inferred:
        lines += ["", "inferred steps used"] + [f"  {s}" for s in inferred]
    lines += ["", "assumptions"] + [f"  - {a}" for a in assumptions]
    lines += ["", "not predictable"]
    lines += [f"  {t}: {why}" for t, why in sorted(unpredictable.items())]
    lines.append(f"  {len(no_data)} further traits have no inheritance data in the seed.")
    return lines


__all__ = [
    "NO_TRAIT",
    "Allele",
    "CrossResult",
    "GeneticModel",
    "Genotype",
    "ModelError",
    "NotPredictable",
    "PhenotypeCall",
    "RangeResult",
    "Sex",
    "State",
    "format_cross",
    "format_range",
]
