"""Render the human-readable trait dossier. PRD §13.

The layout follows the PRD's own worked example. Two things it adds, both because
the seed data made them necessary: every genetic association shows its evidence
level inline, and "Open questions" is generated rather than hand-written -- a
contradiction or a missing causal gene appears there because the graph says so,
not because someone remembered to note it.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from neo4j import Session

from .queries import claims_about, claims_targeting, get_trait, mechanisms_via_genes
from .vocabulary import EvidenceLevel, Predicate, ReviewStatus

_GENETIC_PREDICATES = {
    Predicate.ASSOCIATED_WITH_GENE.value,
    Predicate.ASSOCIATED_WITH_LOCUS.value,
    Predicate.CAUSED_BY_VARIANT.value,
    Predicate.MODIFIED_BY.value,
}
_RELATED_PREDICATES = {
    Predicate.RESEMBLES.value,
    Predicate.CO_OCCURS_WITH.value,
    Predicate.SUBSUMES.value,
    Predicate.PUTATIVELY_SAME_AS.value,
    Predicate.PLEIOTROPIC_WITH.value,
}

#: Levels at which the ontology is entitled to say a gene *causes* a trait.
_CAUSAL_LEVELS = {EvidenceLevel.CAUSAL_VARIANT.value, EvidenceLevel.FUNCTIONAL_VALIDATION.value}


def _cite(ev: dict[str, Any]) -> str:
    bits = []
    if ev.get("paper_title"):
        title = ev["paper_title"]
        bits.append(title if len(title) <= 90 else title[:87] + "...")
    if ev.get("paper_year"):
        bits.append(f"({ev['paper_year']})")
    ref = " ".join(bits) or "source unrecorded"
    if ev.get("paper_doi"):
        ref += f" — doi:{ev['paper_doi']}"
    elif ev.get("paper_pmid"):
        ref += f" — PMID:{ev['paper_pmid']}"
    elif ev.get("paper_url"):
        # A breeder source has no DOI and the URL is its only locator. Without
        # this branch the strongest thing we can say about an entire axis of the
        # ontology prints with no way to check it, which PRD §2.4 does not allow
        # merely because the source is a shop page.
        ref += f" — {ev['paper_url']}"
    return ref


def _locus_detail(row: dict[str, Any]) -> str:
    """Carry the fragility of a GWAS hit with the hit itself."""
    parts = []
    if row.get("object_chromosome"):
        span = ""
        if row.get("object_start") and row.get("object_end"):
            span = f":{row['object_start']:,}-{row['object_end']:,}"
        parts.append(f"chr{row['object_chromosome']}{span}")
    if row.get("object_n_cases"):
        parts.append(f"n={row['object_n_cases']}")
    if row.get("object_best_p"):
        parts.append(f"P={row['object_best_p']}")
    if row.get("object_n_genes"):
        parts.append(f"{row['object_n_genes']} genes in interval")
    return ", ".join(parts)


def render_trait(session: Session, name: str) -> str:
    trait = get_trait(session, name)
    if trait is None:
        raise KeyError(f"no OrnamentalTrait named {name!r}")

    outbound = claims_about(session, trait["id"])
    inbound = claims_targeting(session, trait["id"])

    by_predicate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outbound:
        by_predicate[row["predicate"]].append(row)

    lines: list[str] = []
    heading = trait["name"]
    if trait.get("japanese_name"):
        heading += f" ({trait['japanese_name']})"
    lines += [f"# {heading}", ""]

    meta = []
    if trait.get("category"):
        meta.append(trait["category"])
    if trait.get("is_composite"):
        meta.append("composite class")
    if meta:
        lines += [" · ".join(meta), ""]
    if trait.get("description"):
        lines += [trait["description"], ""]

    # -- Aliases -------------------------------------------------------------
    lines += ["## Aliases", ""]
    if trait.get("aliases"):
        lines += [f"- {a}" for a in trait["aliases"]]
    else:
        lines.append("- _none recorded_")
    if trait.get("unverified_labels"):
        lines += [
            "",
            "Unverified labels (no source; not usable as identifiers — PRD §2.4):",
            *[f"- {a}" for a in trait["unverified_labels"]],
        ]
    lines.append("")

    # -- Phenotypes ----------------------------------------------------------
    lines += ["## Phenotypes", ""]
    phenos = by_predicate.get(Predicate.HAS_PHENOTYPE.value, [])
    if phenos:
        for row in phenos:
            lines.append(f"- {row['object_name']}")
    else:
        lines.append("- _none recorded_")
    lines.append("")

    # -- Genetics ------------------------------------------------------------
    lines += ["## Genetics", ""]
    genetic = [r for r in outbound if r["predicate"] in _GENETIC_PREDICATES]
    if genetic:
        lines += ["| Target | Relation | Strongest evidence | Detail |", "|---|---|---|---|"]
        for row in genetic:
            supports = [e for e in row["evidence"] if e["stance"] == "SUPPORTS"]
            level = supports[0]["level"] if supports else "—"
            contra = sum(1 for e in row["evidence"] if e["stance"] == "CONTRADICTS")
            if contra:
                level += f" (⚠ {contra} contradicting)"
            detail = _locus_detail(row) or (row.get("object_label") or "")
            lines.append(
                f"| {row['object_name']} | {row['predicate']} | {level} | {detail} |"
            )
    else:
        lines.append("_No genetic association recorded._")
    lines.append("")

    # -- Mechanism -----------------------------------------------------------
    # Two hops: trait -> gene -> mechanism. The trait-gene hop's strength is shown
    # alongside, since a mechanism reached through a positional candidate inside a
    # 200-gene interval is a guess about a guess.
    lines += ["## Mechanism", ""]
    mechanisms = mechanisms_via_genes(session, trait["id"])
    if mechanisms:
        for row in mechanisms:
            via = ", ".join(row["via_genes"])
            lines.append(
                f"- {row['mechanism']} — via {via} "
                f"(trait→gene link: {row['strongest_link']})"
            )
    else:
        lines.append("- _not yet linked to a developmental mechanism_")
    lines.append("")

    # -- Evidence ------------------------------------------------------------
    lines += ["## Evidence", ""]
    seen: set[tuple[str, str]] = set()
    any_evidence = False
    for row in outbound:
        for ev in row["evidence"]:
            key = (ev.get("paper_doi") or ev.get("paper_title") or "", ev["finding"])
            if key in seen:
                continue
            seen.add(key)
            any_evidence = True
            marker = "✗" if ev["stance"] == "CONTRADICTS" else "•"
            lines.append(f"{marker} **{ev['level']}** — {_cite(ev)}")
            lines.append(f"  - {row['predicate']} → {row['object_name']}")
            lines.append(f"  - {ev['finding']}")
            if ev.get("quote"):
                lines.append(f"  - > {ev['quote']}")
            if ev.get("section"):
                lines.append(f"  - _{ev['section']}_")
            lines.append("")
    if not any_evidence:
        lines += ["_No evidence recorded._", ""]

    # -- Related traits ------------------------------------------------------
    lines += ["## Related traits", ""]
    related = [r for r in outbound if r["predicate"] in _RELATED_PREDICATES]
    related_in = [r for r in inbound if r["predicate"] in _RELATED_PREDICATES]
    if related or related_in:
        for row in related:
            lines.append(f"- {row['predicate']} → {row['object_name']}")
        for row in related_in:
            lines.append(f"- {row['subject_name']} → {row['predicate']} → this trait")
    else:
        lines.append("- _none recorded_")
    lines.append("")

    # -- Open questions ------------------------------------------------------
    lines += ["## Open questions", ""]
    questions = _open_questions(trait, outbound)
    lines += [f"- {q}" for q in questions] if questions else ["- _none flagged_"]
    lines.append("")

    return "\n".join(lines)


def _open_questions(trait: dict[str, Any], outbound: list[dict[str, Any]]) -> list[str]:
    """Derive the open questions from the graph rather than from prose.

    Anything a reader would need to know before trusting this dossier should turn
    up here automatically, because the failure mode the PRD warns about (§2.2,
    §12) is a confident-looking record whose caveats live only in someone's head.
    """
    questions: list[str] = []

    for row in outbound:
        contradicting = [e for e in row["evidence"] if e["stance"] == "CONTRADICTS"]
        if contradicting:
            questions.append(
                f"**Contradicted**: `{row['predicate']} → {row['object_name']}` has "
                f"{len(contradicting)} contradicting finding(s); both sides are kept "
                "(PRD §9). See Evidence above."
            )

    genetic = [r for r in outbound if r["predicate"] in _GENETIC_PREDICATES]
    has_causal = any(
        e["stance"] == "SUPPORTS" and e["level"] in _CAUSAL_LEVELS
        for row in genetic
        for e in row["evidence"]
    )
    if genetic and not has_causal:
        questions.append(
            "No causal or functionally validated variant. Every genetic link here is "
            "association-level — do not read the table above as cause."
        )
    if not genetic:
        questions.append("No candidate gene or locus recorded yet.")

    if trait.get("unverified_labels"):
        questions.append(
            "Japanese orthography is unverified reconstruction, not sourced from the "
            "literature; needs a native-speaker pass before use as a display label."
        )

    pending = [
        r for r in outbound if r.get("review_status") == ReviewStatus.PENDING.value
    ]
    if pending:
        reasons = sorted({x for r in pending for x in (r.get("review_reasons") or [])})
        questions.append(
            f"{len(pending)} claim(s) awaiting human review"
            + (f" ({', '.join(reasons)})" if reasons else "")
            + "."
        )
    return questions
