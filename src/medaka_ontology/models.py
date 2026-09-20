"""Typed records that sit between the YAML seed files and the graph.

Everything written to Neo4j passes through these models, so the invariants the PRD
cares about -- provenance on every claim (§2.4), raw evidence kept apart from our
reading of it (§2.3), the closed relation vocabulary (§4) -- are enforced once,
here, rather than at each call site.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .vocabulary import (
    ENTITY_LABELS,
    EVIDENCE_RANK,
    LABEL_PREFIX,
    SYMMETRIC_PREDICATES,
    EvidenceLevel,
    NodeLabel,
    Predicate,
    ReviewReason,
    ReviewStatus,
    Stance,
    TraitCategory,
    validate_claim_shape,
)

#: Bumped when extraction logic changes in a way that should force reprocessing of
#: papers already marked done. PRD §11: "동일 논문을 반복 처리하지 않는다."
PIPELINE_VERSION = 1

#: The species this ontology is about. Anything else is comparative.
MEDAKA = "Oryzias latipes"

#: The strongest levels a comparative finding may carry on a claim about medaka.
#: A zebrafish knockout is real functional validation -- of the zebrafish gene. On
#: a medaka trait-gene claim it is an argument from homology, and recording it at
#: its own level is how a knowledge base talks itself into false confidence.
COMPARATIVE_CEILING = EvidenceLevel.OBSERVATIONAL

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Lowercase ASCII slug, used for deterministic entity ids.

    Non-ASCII input (Japanese trait labels, for instance) is transliterated where
    possible and otherwise dropped, which is why the *romanized* name is the
    canonical identifier and the Japanese orthography is a display label.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_STRIP.sub("-", ascii_only.lower()).strip("-")
    if not slug:
        # Fall back to a hash so a purely non-ASCII name still gets a stable id
        # instead of colliding on the empty string.
        slug = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return slug


def entity_id(label: NodeLabel, name: str) -> str:
    """Deterministic id, so re-running the loader updates rather than duplicates."""
    return f"{LABEL_PREFIX[label]}:{slugify(name)}"


def content_digest(*parts: str) -> str:
    """Short stable digest of the given parts, used to mint deterministic ids."""
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


_digest = content_digest  # internal alias, kept so call sites below read shorter


def claim_id(predicate: Predicate, subject_id: str, object_id: str) -> str:
    """Deterministic claim id.

    For symmetric predicates the endpoints are sorted first, so `A resembles B`
    and `B resembles A` collapse to a single claim. Without this, evidence for one
    direction would not count towards the other and a well-supported symmetric
    relation could look weak from whichever side you queried.
    """
    if predicate in SYMMETRIC_PREDICATES:
        subject_id, object_id = sorted((subject_id, object_id))
    return f"claim:{_digest(predicate.value, subject_id, object_id)}"


def evidence_id(paper_id: str, experiment_type: str, finding: str) -> str:
    """Deterministic evidence id.

    Keyed on the paper and the finding, *not* on the claim, so one finding that
    bears on several claims is a single node with several edges. That is what makes
    "which findings does this paper contribute?" answerable.
    """
    return f"ev:{_digest(paper_id, experiment_type, finding)}"


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Paper(_Record):
    """Provenance root. PRD §2.4."""

    key: str = Field(description="Short handle used to reference this paper in seed YAML")
    title: str
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    url: str | None = None
    open_access: bool | None = None
    authors: list[str] = Field(default_factory=list)
    #: Set when the extraction pipeline has finished with this paper, so a later
    #: run can skip it. PRD §11.
    processed_at: datetime | None = None
    pipeline_version: int | None = None
    notes: str | None = None
    review_reasons: list[ReviewReason] = Field(default_factory=list)

    @property
    def id(self) -> str:
        # Prefer the DOI: it is the one identifier that survives our own key
        # changing, and two seed files referring to the same paper by different
        # handles must not produce two nodes.
        if self.doi:
            return f"paper:doi:{self.doi.lower()}"
        if self.pmid:
            return f"paper:pmid:{self.pmid}"
        return f"paper:key:{slugify(self.key)}"

    @model_validator(mode="after")
    def _require_some_identifier(self) -> Paper:
        if not (self.doi or self.pmid or self.pmcid or self.url):
            raise ValueError(
                f"paper {self.key!r}: needs at least one of doi/pmid/pmcid/url. "
                "PRD §2.4 requires every claim to be traceable to a source."
            )
        return self


class Entity(_Record):
    """Any node that can be the subject or object of a claim. PRD §3."""

    label: NodeLabel
    name: str = Field(description="Canonical name; romanized/ASCII for trait names")
    aliases: list[str] = Field(
        default_factory=list,
        description=(
            "Pure naming variants with a known source. PRD §8: an alias is not a "
            "claim of biological equivalence -- use putatively_same_as for that."
        ),
    )
    unverified_labels: list[str] = Field(
        default_factory=list,
        description=(
            "Strings we could not trace to a source, kept separate from `aliases` "
            "so unsourced text never masquerades as sourced. PRD §2.4."
        ),
    )
    description: str | None = None
    # OrnamentalTrait
    category: TraitCategory | None = None
    japanese_name: str | None = Field(
        default=None,
        description="Only when attested in a source. Otherwise use unverified_labels.",
    )
    is_composite: bool = Field(
        default=False,
        description=(
            "True for umbrella phenotype classes such as YWKo or kurobuchi that "
            "the seed paper defines as unions of other traits."
        ),
    )
    # Gene / HumanGene
    symbol: str | None = None
    species: str | None = Field(
        default=None,
        description=(
            "Binomial name. Required on Gene: comparative work on zebrafish or "
            "mouse orthologues is a large part of the evidence base, and an "
            "unlabelled gene node silently reads as medaka."
        ),
    )
    ensembl_id: str | None = None
    ncbi_gene_id: str | None = None
    # Locus / GeneticVariant
    chromosome: str | None = None
    start: int | None = None
    end: int | None = None
    position: int | None = None
    assembly: str | None = None
    variant_type: str | None = None
    #: Numbers the seed paper reports for a GWAS interval. Kept on the locus so the
    #: fragility of a hit (n=4 with an extreme P) travels with it.
    n_cases: int | None = None
    best_p_value: str | None = None
    n_genes_in_interval: int | None = None

    review_status: ReviewStatus = ReviewStatus.PENDING
    review_reasons: list[ReviewReason] = Field(default_factory=list)

    @field_validator("best_p_value", mode="before")
    @classmethod
    def _p_value_as_text(cls, value: Any) -> Any:
        """Accept `6.28E-25` written bare in YAML.

        YAML reads that as a float, and requiring seed authors to remember quotes
        around every P-value is a rule that will be forgotten. The value is kept
        as text because it is a reported figure to display, not a number this
        project does arithmetic on -- and round-tripping through float would
        rewrite the paper's own notation.
        """
        if isinstance(value, float):
            return repr(value)
        if isinstance(value, int):
            return str(value)
        return value

    @model_validator(mode="after")
    def _check(self) -> Entity:
        if self.label not in ENTITY_LABELS:
            raise ValueError(
                f"{self.label.value} is not a claim endpoint; "
                f"expected one of {sorted(x.value for x in ENTITY_LABELS)}"
            )
        if self.category is not None and self.label is not NodeLabel.ORNAMENTAL_TRAIT:
            raise ValueError("category applies only to OrnamentalTrait")
        overlap = set(self.aliases) & set(self.unverified_labels)
        if overlap:
            raise ValueError(
                f"{self.name}: {sorted(overlap)} appear as both a sourced alias and "
                "an unverified label; pick one"
            )
        if self.label is NodeLabel.GENE and not self.species:
            raise ValueError(
                f"gene {self.name!r}: species is required. Most of the functional "
                "evidence here is comparative, and an unlabelled gene reads as medaka."
            )
        return self

    @property
    def id(self) -> str:
        return entity_id(self.label, self.name)


class EntityRef(_Record):
    """A pointer to an entity from a claim in a seed file."""

    label: NodeLabel
    name: str

    @property
    def id(self) -> str:
        return entity_id(self.label, self.name)


class Evidence(_Record):
    """A single finding as the source states it. PRD §2.3 -- raw only.

    Our reading of what the finding *means* belongs on the claim, in
    `Claim.interpretation`. Keeping them in separate records is the whole point of
    §2.3, and it is why `finding` should paraphrase the paper rather than argue
    with it.
    """

    paper: str = Field(description="Paper.key this finding comes from")
    experiment_type: str
    finding: str = Field(description="What the source states, in its own terms")
    level: EvidenceLevel = EvidenceLevel.UNKNOWN
    stance: Stance = Stance.SUPPORTS
    quote: str | None = Field(default=None, description="Verbatim excerpt where available")
    section: str | None = Field(default=None, description="Section / figure / table")
    strain: str | None = Field(default=None, description="Strain or population studied")
    species: str = Field(
        default=MEDAKA,
        description=(
            "Species the experiment was performed in. Defaults to medaka; set it "
            "for every comparative finding. PRD §10."
        ),
    )
    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    review_reasons: list[ReviewReason] = Field(default_factory=list)

    @property
    def rank(self) -> int:
        return EVIDENCE_RANK[self.level]

    @property
    def is_comparative(self) -> bool:
        return not self.species.lower().startswith("oryzias")

    def id_for(self, paper_id: str) -> str:
        return evidence_id(paper_id, self.experiment_type, self.finding)


class Claim(_Record):
    """A reified relation. PRD §9.

    A claim carries no truth value of its own. Its standing is whatever the
    attached evidence adds up to, which is what lets a contradicting paper be
    recorded as an extra edge instead of an overwrite.
    """

    predicate: Predicate
    subject: EntityRef
    object: EntityRef
    interpretation: str | None = Field(
        default=None,
        description="Our reading of the evidence, never the source's own words. PRD §2.3.",
    )
    evidence: list[Evidence] = Field(default_factory=list)
    subject_species: str | None = Field(
        default=None,
        description=(
            "The subject entity's species, when the caller knows it. Needed for "
            "the comparative-evidence ceiling on Gene subjects, whose species "
            "lives on the entity rather than being implied by the label."
        ),
    )
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_reasons: list[ReviewReason] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Claim:
        validate_claim_shape(self.predicate, self.subject.label, self.object.label)
        if not self.evidence:
            raise ValueError(
                f"claim {self.predicate.value} {self.subject.name} -> {self.object.name}: "
                "has no evidence. PRD §2.2 requires every claim to carry a source."
            )
        # A medaka subject means comparative evidence on it is an argument from
        # homology, whatever its standing in its own species.
        #
        # An OrnamentalTrait or Phenotype is medaka by definition, so the check
        # always applies there. A Gene is not: `kcnk5b` is a zebrafish gene, and
        # zebrafish evidence about it is direct, not comparative. Its species
        # lives on the entity, which this model cannot see, so the caller passes
        # it in `subject_species`.
        #
        # When a Gene subject arrives with no species, the check is skipped here
        # and the caller is responsible. Both callers do it: the seed loader
        # checks in `loader.validate`, where the entity map is available, and
        # acceptance looks the species up before constructing the claim. A third
        # write path would have to do the same -- which is why
        # `candidates.accept_candidate` routes through this model rather than
        # writing its own Cypher.
        if self.subject.label in {NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.PHENOTYPE}:
            subject_is_medaka = True
        elif self.subject_species is None:
            subject_is_medaka = False
        else:
            subject_is_medaka = self.subject_species.lower().startswith("oryzias")

        if subject_is_medaka:
            for ev in self.evidence:
                if ev.is_comparative and ev.rank > EVIDENCE_RANK[COMPARATIVE_CEILING]:
                    raise ValueError(
                        f"claim {self.predicate.value} {self.subject.name} -> "
                        f"{self.object.name}: {ev.species} evidence is recorded at "
                        f"{ev.level.value}, above the comparative ceiling "
                        f"{COMPARATIVE_CEILING.value}. A result in another species "
                        "supports the medaka claim by homology, not directly; "
                        "record the functional level on that species' own gene."
                    )
        return self

    @property
    def id(self) -> str:
        return claim_id(self.predicate, self.subject.id, self.object.id)

    @property
    def is_disputed(self) -> bool:
        stances = {e.stance for e in self.evidence}
        return Stance.SUPPORTS in stances and Stance.CONTRADICTS in stances

    @property
    def strongest_support(self) -> EvidenceLevel:
        supporting = [e for e in self.evidence if e.stance is Stance.SUPPORTS]
        if not supporting:
            return EvidenceLevel.UNKNOWN
        return max(supporting, key=lambda e: e.rank).level

    def derived_review_reasons(self) -> list[ReviewReason]:
        """Flags the graph can work out for itself. PRD §12.

        Explicit reasons in the seed file are merged with these; the union is what
        lands on the node, so a human never has to notice a contradiction manually.
        """
        reasons = set(self.review_reasons)
        if self.is_disputed:
            reasons.add(ReviewReason.CONTRADICTORY_EVIDENCE)
        if self.predicate is Predicate.CAUSED_BY_VARIANT:
            reasons.add(ReviewReason.NEW_CAUSAL_VARIANT)
        if self.predicate is Predicate.PUTATIVELY_SAME_AS:
            reasons.add(ReviewReason.BREEDER_ACADEMIC_LINK)
        if any(e.level is EvidenceLevel.UNKNOWN for e in self.evidence):
            reasons.add(ReviewReason.EVIDENCE_LEVEL_UNCLEAR)
        return sorted(reasons, key=lambda r: r.value)


class SeedBundle(_Record):
    """One parsed seed YAML file."""

    source_file: str | None = None
    papers: list[Paper] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


__all__ = [
    "PIPELINE_VERSION",
    "Claim",
    "Entity",
    "EntityRef",
    "Evidence",
    "Paper",
    "SeedBundle",
    "claim_id",
    "entity_id",
    "evidence_id",
    "slugify",
]
