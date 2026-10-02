"""The cross query: from two parents' genotypes (or what they show) to the
offspring's genotypes and traits. ADR 0006 built it; ADR 0007 made it a feature.

Offspring trait prediction is in the project's scope (PRD §1, §14, ADR 0007).
Prediction is not recommendation: this module says what the seed's claims imply
for a cross someone already chose, how well each prediction is established, and
what it assumes or refuses. It ranks no cross, picks no mate and keeps no stock.

It reads the loaded `SeedBundle` and nothing else, so it needs no Neo4j and cannot
see anything the seed does not claim. Every rule is a claim:

    loci            objects of `allele_of`; a locus's alleles are its subjects
    wild type       the allele whose entity says `variant_type: wild type`
    dominance       `dominant_over`, `incompletely_dominant_over` between alleles
    sex linkage     `inherited_as sex-linked` on the locus
    traits          `requires_allele`: expressed iff every required allele is
    masking         `masks`: an expressed masker hides the masked trait
    strains         `composed_of`: expressed iff every part is
    refusals        see `REFUSALS`: a trait the claims cannot support is not guessed

Probabilities are `fractions.Fraction`, so 9:3:3:1 is 9/16 and not 0.5625, and a
test can assert equality. The output contract (`cross_to_json`, `range_to_json`,
README "Predicting offspring") is versioned by `SCHEMA_VERSION`.

Assumptions the code makes and every result states (`CrossResult.assumptions`):

  * sex is 1:1 (XY, dmy on the Y);
  * loci that are not sex-linked assort independently, so two loci joined by a
    `linked_to` claim with no recombination fraction are refused, not assumed apart;
  * a sex-linked locus is completely linked to sex: the father's Y allele goes to
    his sons and his X allele to his daughters (the r-dmy rate is zero because no
    source gives one; an open decision, spec 열린 결정);
  * a locus the caller does not give is homozygous wild type;
  * four decisions the owner has not made are stated on every result:
    `OPEN_DECISIONS`.
"""

from __future__ import annotations

import itertools
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction

from .models import Claim, SeedBundle, Stance
from .vocabulary import EVIDENCE_RANK, EvidenceLevel, NodeLabel, Predicate

#: Version of the JSON the cross command prints (`cross_to_json`, `range_to_json`,
#: `error_to_json`). Bump it when a key is removed, renamed or changes meaning;
#: adding a key does not.
SCHEMA_VERSION = 1

SEX_LINKED = "sex-linked"
MULTILOCUS = "multilocus"
WILD_TYPE = "wild type"
#: Class label for an offspring that shows none of the traits the model can express.
NO_TRAIT = "none of the modelled traits"


class ModelError(ValueError):
    """The seed's genetic layer is inconsistent, or the caller's input is.

    `code` is the machine-readable kind that `error_to_json` prints."""

    code = "seed_inconsistent"


class InputError(ModelError):
    """The caller's genotype, trait name or option is wrong. Fix the input."""

    code = "invalid_input"


class NotPredictable(ModelError):
    """A trait the model cannot reason about, with the reason a reader can act on."""

    code = "not_predictable"


class LinkedLoci(NotPredictable):
    """Two loci in the cross are linked and no source gives how often they
    recombine, so independent assortment would be a guess presented as a result."""

    code = "linked_loci_no_recombination_fraction"


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


class State(StrEnum):
    """How far an allele or trait is expressed in one genotype."""

    EXPRESSED = "expressed"
    PARTIAL = "partial"  # incomplete dominance: the heterozygote is intermediate
    ABSENT = "absent"
    UNKNOWN = "unknown"  # a heterozygote whose two alleles have no dominance edge


#: Why a trait is not predicted. Each code is a refusal path with a test.
REFUSALS = {
    "multilocus": "a source records the trait as multilocus; no allele model exists",
    "no_allele_model": "an inheritance mode is recorded but no allele model exists",
    "no_inheritance_data": "no source in the seed says how the trait is inherited",
    "disputed": "a claim the prediction rests on is contradicted by a source",
    "linked_loci_no_recombination_fraction": "two loci are linked and no source gives a rate",
}


@dataclass(frozen=True)
class Refusal:
    trait: str | None  # None when the refusal is about the cross, not one trait
    code: str
    reason: str


@dataclass(frozen=True)
class Assumption:
    id: str
    text: str
    #: True for the decisions the owner has not made. They are stated on every
    #: result, whether or not the cross happens to touch them.
    open_decision: bool = False


OPEN_DECISIONS = (
    Assumption(
        "strain_scope",
        "Only two composite strains are modelled (seethrough = albino + panda, Hitomi = bigeye "
        "+ suihougan). The 356 strain names of the trade vocabulary are not incorporated, so a "
        "strain cannot be named as a parent; name the traits it shows.",
        True,
    ),
    Assumption(
        "source_authority",
        "The authority order between sources (JMA > field guide > breeding farm > blog) is "
        "provisional and undecided. The query does not use it to settle a disagreement: it uses "
        "evidence levels, caps trade sources at BREEDER_OBSERVATION, and refuses a disputed claim.",
        True,
    ),
    Assumption(
        "r_sex_recombination",
        "A sex-linked locus (the r locus) is taken as completely linked to the sex-determining "
        "locus, recombination fraction 0: a father's Y allele goes to his sons and his X allele "
        "to his daughters. No source gives a rate; the value is undecided.",
        True,
    ),
    Assumption(
        "albino_allele",
        "Albino is modelled as the i allele of tyr (koga1995). kon2026 Table 1 cites oca2 for "
        "albino; two albino parents are assumed to carry the same allele, so albino "
        "heterogeneity (tyr vs oca2) cannot be represented and two albino strains of different "
        "loci would not be told apart.",
        True,
    ),
)

#: Levels below this rank are a *weak basis*: no source stated the claim from its own
#: data (a trade source, or a conclusion this project drew). Display rule R2.
WEAK_BASIS_BELOW = EVIDENCE_RANK[EvidenceLevel.OBSERVATIONAL]

LEVEL_GLOSS = {
    EvidenceLevel.BREEDER_OBSERVATION: "trade or breeder description only",
    EvidenceLevel.INFERRED: "a conclusion this project drew, no source states it",
    EvidenceLevel.UNKNOWN: "evidence level unclear",
}


def weak_basis(level: EvidenceLevel) -> bool:
    """Display rule R2: a prediction resting on a level below OBSERVATIONAL is
    marked wherever the trait is named, not only in the evidence section."""
    return EVIDENCE_RANK[level] < WEAK_BASIS_BELOW


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
    #: Every claim the prediction can rest on, weakest first.
    used: tuple[Claim, ...] = ()


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
    assumptions: list[Assumption]
    unpredictable: dict[str, str]
    no_data: list[str]
    refusals: list[Refusal] = field(default_factory=list)
    mother_pairs: dict[str, tuple[str, str]] = field(default_factory=dict)
    father_pairs: dict[str, tuple[str, str]] = field(default_factory=dict)
    #: per sex, per class: masked trait -> (share of the class it is hidden in, maskers)
    hidden: dict[Sex, dict[ClassKey, dict[str, tuple[Fraction, tuple[str, ...]]]]] = field(
        default_factory=dict
    )


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
    assumptions: list[Assumption]
    unpredictable: dict[str, str]
    no_data: list[str]
    refusals: list[Refusal] = field(default_factory=list)
    true_breeding: bool = False
    mother_hypotheses: list[str] = field(default_factory=list)
    father_hypotheses: list[str] = field(default_factory=list)
    #: per sex, per class: masked trait -> maskers, in at least one hypothesis cross
    hidden: dict[Sex, dict[ClassKey, dict[str, tuple[str, ...]]]] = field(default_factory=dict)


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
        self._predictable: dict[str, bool] = {}
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
            if len(parts) == 1 and token in self.by_symbol:
                locus = self.by_symbol[token].locus
                if self.loci[locus].sex_linked:
                    raise InputError(
                        f"{token!r}: {locus!r} is sex-linked, so write both chromosomes: a "
                        "male's X allele first and Y allele second (r/R is X^r Y^R), a "
                        "female's two X alleles"
                    )
            if len(parts) != 2 or not all(parts):
                raise InputError(f"{token!r}: write each locus as two alleles, like b/b")
            alleles = []
            for sym in parts:
                if sym not in self.by_symbol:
                    known = ", ".join(sorted(self.by_symbol))
                    raise InputError(f"unknown allele {sym!r}; known symbols: {known}")
                alleles.append(self.by_symbol[sym])
            if alleles[0].locus != alleles[1].locus:
                raise InputError(
                    f"{token!r}: {parts[0]} is an allele of {alleles[0].locus!r} and "
                    f"{parts[1]} of {alleles[1].locus!r}"
                )
            locus = alleles[0].locus
            if locus in given:
                raise InputError(f"locus {locus!r} given twice")
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

    def predictable(self, trait: str) -> bool:
        """The trait has an allele model and no claim under it is disputed."""
        if trait not in self._predictable:
            self._predictable[trait] = self._modelled(trait) and not self.disputed(trait)
        return self._predictable[trait]

    def _modelled(self, trait: str, _seen: frozenset[str] = frozenset()) -> bool:
        if trait in self.requires:
            return True
        if trait in self.parts and trait not in _seen:
            return all(self._modelled(t, _seen | {trait}) for t, _ in self.parts[trait])
        return False

    def disputed(self, trait: str) -> list[Claim]:
        """Claims under the prediction that a source contradicts. Refusal path:
        which allele shows, or what a trait needs, is contested, and the query
        will not pick a side (ADR 0007)."""
        return [c for c in self.support_claims(trait) if c.is_disputed]

    def known_traits(self) -> set[str]:
        return {*self.ornamental, *self.requires, *self.parts}

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
            raise InputError("the first parent must be a female and the second a male")
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
        return self._classes(mother, father, sex)[0]

    def _classes(
        self, mother: Genotype, father: Genotype, sex: Sex
    ) -> tuple[
        dict[ClassKey, Fraction], dict[ClassKey, dict[str, tuple[Fraction, tuple[str, ...]]]]
    ]:
        """Class shares, and for each class what its fish carry but do not show:
        masked trait -> (share of the class hidden, the expressed maskers)."""
        shares: dict[ClassKey, Fraction] = defaultdict(Fraction)
        mass: dict[ClassKey, dict[str, Fraction]] = defaultdict(lambda: defaultdict(Fraction))
        maskers: dict[ClassKey, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for g, p in self.offspring(mother, father, sex).items():
            call = self.phenotype(g)
            shares[call.visible] += p
            for victim in call.masked:
                mass[call.visible][victim] += p
                for masker, _ in self.masked_by[victim]:
                    if call.states.get(masker) is State.EXPRESSED:
                        maskers[call.visible][victim].add(masker)
        hidden = {
            key: {
                victim: (p / shares[key], tuple(sorted(maskers[key][victim])))
                for victim, p in victims.items()
            }
            for key, victims in mass.items()
        }
        return dict(shares), hidden

    # ----------------------------------------------------------------- evidence

    def support_claims(
        self,
        trait: str,
        masked: frozenset[str] | None = None,
        _seen: frozenset[str] = frozenset(),
    ) -> list[Claim]:
        """Every claim a prediction for this trait can rest on. Static, so it errs
        toward the weaker side: a dominance edge counts even when the particular
        cross never reads it. A `masks` claim is the exception (R-78): with `masked`
        given, it counts only for a trait in it, the traits the result actually hides
        in some class. `None` counts every masks claim (the refusal check)."""
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
                claims.extend(self.support_claims(part, masked, _seen | {trait}))
        if masked is None or trait in masked:
            claims.extend(claim for _, claim in self.masked_by.get(trait, []))
        return list({c.id: c for c in claims}.values())

    def support(self, trait: str, masked: frozenset[str] | None = None) -> TraitSupport:
        claims = self.support_claims(trait, masked)
        weak = _weakest(claims)
        if weak is None:
            return TraitSupport(trait, EvidenceLevel.UNKNOWN, "no claims", 0)
        used = tuple(sorted(claims, key=lambda c: (EVIDENCE_RANK[c.strongest_support], c.id)))
        return TraitSupport(trait, weak[0], _describe(weak[1]), len(claims), used)

    # -------------------------------------------------------------- reporting

    def refusals(self) -> list[Refusal]:
        """Every ornamental trait the query will not predict, with a code from
        `REFUSALS` and the reason a reader can act on."""
        out: list[Refusal] = []
        for trait in sorted(self.known_traits()):
            if self.predictable(trait):
                continue
            modes = self.modes.get(trait, [])
            names = {m for m, _ in modes}
            if self._modelled(trait) and self.disputed(trait):
                claims = "; ".join(sorted(_describe(c) for c in self.disputed(trait)))
                out.append(Refusal(trait, "disputed", f"disputed claim ({claims})"))
            elif MULTILOCUS in names:
                papers = sorted({e.paper for m, c in modes if m == MULTILOCUS for e in c.evidence})
                reason = f"not predictable (multilocus, {', '.join(papers)})"
                out.append(Refusal(trait, "multilocus", reason))
            elif trait in self.parts and trait not in self.modes:
                bare = sorted(t for t, _ in self.parts[trait] if not self._modelled(t))
                reason = f"composed of traits with no allele model ({', '.join(bare)})"
                out.append(Refusal(trait, "no_allele_model", reason))
            elif modes:
                out.append(
                    Refusal(
                        trait,
                        "no_allele_model",
                        f"inheritance recorded ({', '.join(sorted(names))}) but no allele model",
                    )
                )
            else:
                out.append(Refusal(trait, "no_inheritance_data", "no inheritance data in the seed"))
        return out

    def unpredictable_traits(self) -> tuple[dict[str, str], list[str]]:
        """Traits the query refuses, with why, and traits with no inheritance data."""
        refused: dict[str, str] = {}
        none: list[str] = []
        for r in self.refusals():
            if r.code == "no_inheritance_data":
                none.append(r.trait)
            else:
                refused[r.trait] = r.reason
        return refused, sorted(none)

    def check_linkage(self, loci: Iterable[str]) -> None:
        """Refuse a cross over two loci that a `linked_to` claim joins: they do not
        assort independently and no source says how often they recombine. The r
        locus and the sex-determining gene are joined too, but dmy is not a locus
        the cross has alleles for; that pair is the stated r-sex assumption."""
        loci = set(loci)
        for claim in self.linked:
            a, b = claim.subject.name, claim.object.name
            if a != b and a in loci and b in loci:
                raise LinkedLoci(
                    f"{a} and {b} are linked ({_describe(claim)}) and no recombination fraction "
                    "is recorded, so the query will not assume they assort independently"
                )

    def _assumptions(
        self, genotypes: list[Genotype], traits_shown: set[str], masked: frozenset[str]
    ) -> list[Assumption]:
        in_play = {name for g in genotypes for name, pair in g.pairs if not self._is_wild(pair)}
        notes = [Assumption("sex_ratio", "Offspring sex is 1:1 (XY; dmy on the Y).")]
        autosomal = sorted(n for n in in_play if not self.loci[n].sex_linked)
        if len(autosomal) > 1 or (autosomal and in_play - set(autosomal)):
            notes.append(
                Assumption(
                    "independent_assortment",
                    "Loci assort independently. sasano2012 states b and r are unlinked; for "
                    "the others no source gives a recombination fraction, and no `linked_to` "
                    "claim between two of them exists (one would make the cross refused).",
                )
            )
        notes.append(Assumption("wild_type_default", "A locus not given is homozygous wild type."))
        seen: set[str] = set()
        for trait in sorted(traits_shown):
            for claim in self.support_claims(trait, masked):
                if claim.strongest_support is EvidenceLevel.INFERRED and claim.interpretation:
                    text = " ".join(claim.interpretation.split())
                    if text not in seen:
                        seen.add(text)
                        notes.append(
                            Assumption(
                                f"inferred:{claim.id}",
                                f"{trait} ({_describe(claim)}, INFERRED): {text}",
                            )
                        )
        for trait in sorted(traits_shown):
            for mode, claim in self.modes.get(trait, []):
                if claim.interpretation:
                    text = " ".join(claim.interpretation.split())
                    if text not in seen:
                        seen.add(text)
                        notes.append(
                            Assumption(f"mode:{claim.id}", f"{trait} ({mode}): {text}")
                        )
        return [*notes, *OPEN_DECISIONS]

    def _inferred_steps(self, traits: Iterable[str], masked: frozenset[str]) -> list[str]:
        steps: dict[str, None] = {}
        for trait in sorted(traits):
            for claim in self.support_claims(trait, masked):
                if claim.strongest_support is EvidenceLevel.INFERRED:
                    steps[_describe(claim)] = None
        return list(steps)

    # ------------------------------------------------------------------- cross

    def cross(self, mother: str | Genotype, father: str | Genotype) -> CrossResult:
        m = mother if isinstance(mother, Genotype) else self.parse(mother, Sex.FEMALE)
        f = father if isinstance(father, Genotype) else self.parse(father, Sex.MALE)
        in_play = [
            n for n in sorted(self.loci) if not (self._is_wild(m.at(n)) and self._is_wild(f.at(n)))
        ]
        self.check_linkage(in_play)
        by_sex: dict[Sex, dict[ClassKey, Fraction]] = {}
        hidden: dict[Sex, dict[ClassKey, dict[str, tuple[Fraction, tuple[str, ...]]]]] = {}
        for sex in Sex:
            by_sex[sex], hidden[sex] = self._classes(m, f, sex)
        overall: dict[ClassKey, Fraction] = defaultdict(Fraction)
        for shares in by_sex.values():
            for key, p in shares.items():
                overall[key] += p / 2
        genotypes: dict[Sex, dict[str, Fraction]] = {}
        for sex in Sex:
            dist: dict[str, Fraction] = defaultdict(Fraction)
            for g, p in self.offspring(m, f, sex).items():
                dist[self.show(g, in_play)] += p
            genotypes[sex] = dict(dist)
        traits = self._traits_in(by_sex.values())
        masked = self._hidden_traits(hidden)
        refusals = self.refusals()
        refused, none = self.unpredictable_traits()
        return CrossResult(
            self.show(m, in_play),
            self.show(f, in_play),
            in_play,
            by_sex,
            dict(overall),
            genotypes,
            {t: self.support(t, masked) for t in sorted(traits)},
            self._inferred_steps(traits, masked),
            self._assumptions([m, f], traits, masked),
            refused,
            none,
            refusals,
            {n: m.at(n) for n in in_play},
            {n: f.at(n) for n in in_play},
            hidden,
        )

    @staticmethod
    def _hidden_traits(hidden: dict) -> frozenset[str]:
        """The traits some class of the result hides (R-78)."""
        return frozenset(
            victim
            for by_class in hidden.values()
            for victims in by_class.values()
            for victim in victims
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
            raise InputError("name at least one trait the parent shows, or give its genotype")
        known = self.known_traits()
        for trait in sorted(shown):
            if trait not in known:
                nameable = ", ".join(sorted(t for t in known if self.predictable(t)))
                raise InputError(f"unknown trait {trait!r}; traits that can be named: {nameable}")
        reasons = {r.trait: r.reason for r in self.refusals()}
        for trait in sorted(shown):
            if not self.predictable(trait):
                raise NotPredictable(f"{trait}: {reasons[trait]}")
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
            raise InputError(
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
        mother_shows, father_shows = set(mother_shows), set(father_shows)
        mothers = self.hypotheses(mother_shows, Sex.FEMALE, true_breeding=true_breeding)
        fathers = self.hypotheses(father_shows, Sex.MALE, true_breeding=true_breeding)
        self.check_linkage(self._closure(mother_shows)[0] | self._closure(father_shows)[0])
        per_cross: list[dict[Sex, dict[ClassKey, Fraction]]] = []
        hidden: dict[Sex, dict[ClassKey, dict[str, set[str]]]] = {
            sex: defaultdict(lambda: defaultdict(set)) for sex in Sex
        }
        for m, f in itertools.product(mothers, fathers):
            cross_shares = {}
            for sex in Sex:
                cross_shares[sex], h = self._classes(m, f, sex)
                for key, victims in h.items():
                    for victim, (_, maskers) in victims.items():
                        hidden[sex][key][victim].update(maskers)
            per_cross.append(cross_shares)

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
        masked = self._hidden_traits(hidden)
        refused, none = self.unpredictable_traits()
        return RangeResult(
            sorted(mother_shows),
            sorted(father_shows),
            len(mothers),
            len(fathers),
            by_sex,
            overall,
            {t: self.support(t, masked) for t in sorted(traits)},
            [
                *self._assumptions([*mothers[:1], *fathers[:1]], traits, masked),
                Assumption(
                    "phenotype_hypotheses",
                    "The parents' genotypes are not known: every genotype that shows exactly "
                    "the stated traits, over the loci that can change them, is a hypothesis, and "
                    "each class is a range over the crosses of all hypotheses"
                    + (" (homozygotes only, as for a fixed strain)." if true_breeding else "."),
                ),
            ],
            refused,
            none,
            self.refusals(),
            true_breeding,
            [self.show(g) for g in mothers],
            [self.show(g) for g in fathers],
            {
                sex: {
                    key: {v: tuple(sorted(ms)) for v, ms in victims.items()}
                    for key, victims in hidden[sex].items()
                }
                for sex in Sex
            },
        )


# ------------------------------------------------------------------- formatting
#
# Display rules. Both renderers (the text view and the JSON) go through the same
# helpers, so a rule cannot hold in one and not the other. ADR 0007.
#
#   R1  Every predicted trait carries its weakest evidence level and the claim that
#       sets it, and the claims used are listed (JSON) or counted (text).
#   R2  A trait whose weakest level is below OBSERVATIONAL (BREEDER_OBSERVATION,
#       INFERRED, UNKNOWN) is marked `[LEVEL]` wherever the trait is named in a
#       class, and `weak_basis` is true in the JSON.
#   R3  Every INFERRED claim a prediction leans on prints its reasoning as an
#       assumption.
#   R4  The assumptions list is part of every result. A result missing any of
#       OPEN_DECISIONS is not rendered: `_check_displayable` raises.
#   R5  A class with an unresolved heterozygote (`trait?`) is flagged with a
#       warning that names the cause.
#   R6  Traits the query refuses are listed with a code and reason, never dropped.


def _check_displayable(assumptions: list[Assumption]) -> None:
    present = {a.id for a in assumptions}
    missing = [a.id for a in OPEN_DECISIONS if a.id not in present]
    if missing:
        raise ModelError(f"result lacks the assumption(s) {missing}; it is not rendered (R4)")


def _frac(p: Fraction) -> str:
    return f"{p.numerator}/{p.denominator}"


def _pct(p: Fraction) -> str:
    return f"{p} ({float(p) * 100:.1f}%)"


_LABEL_SUFFIX = re.compile(r"( \(partial\)|\?)$")


def _label_trait(label: str) -> str:
    return _LABEL_SUFFIX.sub("", label)


def _label_state(label: str) -> str:
    if label.endswith(" (partial)"):
        return "partial"
    return "unresolved" if label.endswith("?") else "expressed"


def _name(key: ClassKey, support: dict[str, TraitSupport] | None = None) -> str:
    """The class as text; R2 marks a weak-basis trait inline."""
    parts = []
    for label in key:
        s = (support or {}).get(_label_trait(label))
        parts.append(f"{label} [{s.level.value}]" if s and weak_basis(s.level) else label)
    return " + ".join(parts)


def _frac_or_range(p: Fraction | tuple[Fraction, Fraction]) -> dict:
    if isinstance(p, tuple):
        return {"probability": {"min": _frac(p[0]), "max": _frac(p[1])}}
    return {"probability": _frac(p)}


def _upper(p: Fraction | tuple[Fraction, Fraction]) -> Fraction:
    return p[1] if isinstance(p, tuple) else p


def _class_json(
    key: ClassKey,
    support: dict[str, TraitSupport],
    p: Fraction | tuple[Fraction, Fraction],
    hidden: list[dict],
) -> dict:
    traits = []
    for label in key:
        if label == NO_TRAIT:
            continue
        name = _label_trait(label)
        s = support.get(name)
        traits.append(
            {
                "trait": name,
                "state": _label_state(label),
                "weakest_level": s.level.value if s else None,
                "weak_basis": weak_basis(s.level) if s else False,
            }
        )
    return {"label": " + ".join(key), "traits": traits, **_frac_or_range(p), "hidden": hidden}


def _hidden_json(victims: dict, with_fraction: bool) -> list[dict]:
    out = []
    for victim, value in sorted(victims.items()):
        if with_fraction:
            fraction, maskers = value
            out.append(
                {"trait": victim, "hidden_by": list(maskers), "fraction_of_class": _frac(fraction)}
            )
        else:
            out.append({"trait": victim, "hidden_by": list(value)})
    return out


def _evidence_json(support: dict[str, TraitSupport]) -> list[dict]:
    return [
        {
            "trait": trait,
            "weakest_level": s.level.value,
            "weakest_claim": s.weakest,
            "weak_basis": weak_basis(s.level),
            "claims_used": [
                {
                    "id": c.id,
                    "statement": _describe(c),
                    "level": c.strongest_support.value,
                    "papers": sorted({e.paper for e in c.evidence if e.stance is Stance.SUPPORTS}),
                    "disputed": c.is_disputed,
                }
                for c in s.used
            ],
        }
        for trait, s in support.items()
    ]


def _warnings(keys: Iterable[ClassKey], support: dict[str, TraitSupport]) -> list[dict]:
    warnings = []
    if any(label.endswith("?") for key in keys for label in key):
        warnings.append(
            {
                "code": "dominance_unrecorded",
                "text": "A class marked unresolved ('?') is a heterozygote whose two alleles "
                "have no dominance claim; the seed does not say whether the trait shows.",
            }
        )
    weak = sorted(t for t, s in support.items() if weak_basis(s.level))
    if weak:
        warnings.append(
            {
                "code": "weak_basis",
                "text": "Predicted on a weak basis (no source states it from its own data): "
                + ", ".join(weak),
            }
        )
    return warnings


def _sex_json(result: CrossResult | RangeResult, sex: Sex) -> list[dict]:
    ranged = isinstance(result, RangeResult)
    ordered = sorted(result.by_sex[sex].items(), key=lambda kv: (-_upper(kv[1]), " + ".join(kv[0])))
    hidden = result.hidden.get(sex, {})
    return [
        _class_json(key, result.support, p, _hidden_json(hidden.get(key, {}), not ranged))
        for key, p in ordered
    ]


def _overall_json(result: CrossResult | RangeResult) -> list[dict]:
    ranged = isinstance(result, RangeResult)
    rows = []
    ordered = sorted(result.overall.items(), key=lambda kv: (-_upper(kv[1]), " + ".join(kv[0])))
    for key, p in ordered:
        # What either sex hides. The fraction is per sex, so the overall row names
        # the masked traits and maskers without one.
        victims: dict[str, set[str]] = defaultdict(set)
        for sex in Sex:
            for victim, value in result.hidden.get(sex, {}).get(key, {}).items():
                victims[victim].update(value if ranged else value[1])
        hidden = _hidden_json({v: tuple(sorted(ms)) for v, ms in victims.items()}, False)
        rows.append(_class_json(key, result.support, p, hidden))
    return rows


def _common_json(result: CrossResult | RangeResult, inferred: list[str]) -> dict:
    _check_displayable(result.assumptions)
    keys = [k for d in result.by_sex.values() for k in d]
    return {
        "evidence": _evidence_json(result.support),
        "inferred_steps": inferred,
        "assumptions": [
            {"id": a.id, "text": a.text, "open_decision": a.open_decision}
            for a in result.assumptions
        ],
        "not_predictable": [
            {"trait": r.trait, "code": r.code, "reason": r.reason} for r in result.refusals
        ],
        "warnings": _warnings(keys, result.support),
    }


def cross_to_json(result: CrossResult) -> dict:
    """The documented JSON of a genotype cross (README, "Predicting offspring")."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "genotype_cross",
        "loci_in_play": result.loci,
        "parents": {
            "mother": {
                "genotype": result.mother,
                "alleles": {n: list(p) for n, p in result.mother_pairs.items()},
            },
            "father": {
                "genotype": result.father,
                "alleles": {n: list(p) for n, p in result.father_pairs.items()},
            },
        },
        "offspring": {
            "female": {"classes": _sex_json(result, Sex.FEMALE)},
            "male": {"classes": _sex_json(result, Sex.MALE)},
            "overall": {"classes": _overall_json(result)},
            "genotypes": {
                sex.value: [
                    {"genotype": g, "probability": _frac(p)}
                    for g, p in sorted(result.genotypes[sex].items())
                ]
                for sex in Sex
            },
        },
        **_common_json(result, result.inferred_steps),
    }


def range_to_json(result: RangeResult) -> dict:
    """The documented JSON of a cross from phenotypes: each share is a min/max."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "phenotype_cross",
        "true_breeding": result.true_breeding,
        "parents": {
            "mother": {
                "shows": result.mother,
                "hypothesis_count": result.n_mother,
                "hypotheses": result.mother_hypotheses,
            },
            "father": {
                "shows": result.father,
                "hypothesis_count": result.n_father,
                "hypotheses": result.father_hypotheses,
            },
        },
        "offspring": {
            "female": {"classes": _sex_json(result, Sex.FEMALE)},
            "male": {"classes": _sex_json(result, Sex.MALE)},
            "overall": {"classes": _overall_json(result)},
        },
        **_common_json(result, []),
    }


def error_to_json(exc: ModelError) -> dict:
    """What `cross --json` prints, with exit status 1, when it refuses."""
    return {"schema_version": SCHEMA_VERSION, "error": {"code": exc.code, "message": str(exc)}}


def format_cross(result: CrossResult) -> str:
    _check_displayable(result.assumptions)
    lines = [f"mother  {result.mother}", f"father  {result.father}", ""]
    for sex in Sex:
        lines.append(f"{sex.value} offspring (within sex)")
        for key, p in sorted(result.by_sex[sex].items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {_pct(p):>14}  {_name(key, result.support)}")
            lines += _hidden_lines(result.hidden.get(sex, {}).get(key, {}), True)
        genos = result.genotypes[sex]
        lines.append("  genotypes: " + "; ".join(f"{g} {p}" for g, p in sorted(genos.items())))
    lines += ["", "overall (sex 1:1)"]
    for key, p in sorted(result.overall.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {_pct(p):>14}  {_name(key, result.support)}")
    lines += _tail(result)
    return "\n".join(lines)


def format_range(result: RangeResult) -> str:
    _check_displayable(result.assumptions)
    lines = [
        f"mother shows {', '.join(result.mother)} ({result.n_mother} genotype hypotheses)",
        f"father shows {', '.join(result.father)} ({result.n_father} genotype hypotheses)",
        "",
    ]
    for sex in Sex:
        lines.append(f"{sex.value} offspring (min - max over hypotheses)")
        for key, (lo, hi) in sorted(result.by_sex[sex].items(), key=lambda kv: (-kv[1][1], kv[0])):
            lines.append(f"  {lo} - {hi}  {_name(key, result.support)}")
            lines += _hidden_lines(result.hidden.get(sex, {}).get(key, {}), False)
    lines += ["", "overall (sex 1:1)"]
    for key, (lo, hi) in sorted(result.overall.items(), key=lambda kv: (-kv[1][1], kv[0])):
        lines.append(f"  {lo} - {hi}  {_name(key, result.support)}")
    lines += _tail(result)
    return "\n".join(lines)


def _hidden_lines(victims: dict, with_fraction: bool) -> list[str]:
    lines = []
    for victim, value in sorted(victims.items()):
        if with_fraction:
            share, maskers = value
            amount = "all" if share == 1 else _frac(share)
            lines.append(f"      hides {victim} (masked by {', '.join(maskers)}) in {amount} of it")
        else:
            lines.append(f"      may hide {victim} (masked by {', '.join(value)})")
    return lines


def _tail(result: CrossResult | RangeResult) -> list[str]:
    lines = ["", "evidence (weakest claim under each predicted trait)"]
    for t, s in result.support.items():
        mark = "! " if weak_basis(s.level) else "  "
        gloss = f" -- {LEVEL_GLOSS[s.level]}" if s.level in LEVEL_GLOSS else ""
        lines.append(f"{mark}{t}: {s.level.value} <- {s.weakest} ({s.claims} claims){gloss}")
    inferred = getattr(result, "inferred_steps", [])
    if inferred:
        lines += ["", "inferred steps used"] + [f"  {s}" for s in inferred]
    keys = [k for d in result.by_sex.values() for k in d]
    warnings = _warnings(keys, result.support)
    if warnings:
        lines += ["", "warnings"] + [f"  ! {w['text']}" for w in warnings]
    lines += ["", "assumptions"] + [
        f"  - {a.text}" + ("  [open decision]" if a.open_decision else "")
        for a in result.assumptions
    ]
    lines += ["", "not predictable"]
    lines += [f"  {t}: {why}" for t, why in sorted(result.unpredictable.items())]
    lines.append(
        f"  {len(result.no_data)} further traits have no inheritance data in the seed "
        "(--json lists them)."
    )
    return lines


__all__ = [
    "NO_TRAIT",
    "OPEN_DECISIONS",
    "REFUSALS",
    "SCHEMA_VERSION",
    "Allele",
    "Assumption",
    "CrossResult",
    "GeneticModel",
    "Genotype",
    "InputError",
    "LinkedLoci",
    "ModelError",
    "NotPredictable",
    "PhenotypeCall",
    "RangeResult",
    "Refusal",
    "Sex",
    "State",
    "cross_to_json",
    "error_to_json",
    "format_cross",
    "format_range",
    "range_to_json",
    "weak_basis",
]
