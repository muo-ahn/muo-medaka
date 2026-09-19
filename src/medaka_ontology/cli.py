"""Command-line entry point."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import DOSSIER_DIR, EXPORT_DIR, SEED_DIR
from .db import Neo4jUnavailableError, graph_counts, install_schema, session_scope
from .dossier import render_trait
from .ingest import ingest_bundle, unprocessed_papers
from .loader import SeedValidationError, load_dir
from .models import slugify
from .queries import disputed_claims, list_traits, review_queue, search, shared_genes


def _use_utf8_output() -> None:
    """Dossiers carry em dashes, arrows and -- for traits whose Japanese labels
    are recorded -- kana and kanji. On a Windows console still defaulting to a
    legacy code page, writing any of that raises UnicodeEncodeError and takes the
    command down mid-render. A terminal that cannot show UTF-8 cannot show this
    data at all, so the stream is switched rather than the content flattened.

    Runs before `Console()` is constructed, since rich captures the encoding of
    the stream it is given.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_use_utf8_output()

app = typer.Typer(
    help="Evidence-backed ornamental trait ontology for medaka.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


@app.command()
def validate(
    seed_dir: Path = typer.Option(SEED_DIR, help="Directory of seed YAML files"),
) -> None:
    """Parse and cross-check the seed files. Touches no database."""
    try:
        bundle = load_dir(seed_dir)
    except SeedValidationError as exc:
        _fail(f"seed validation failed:\n{exc}")
        return
    console.print(
        f"[green]OK[/green] {len(bundle.papers)} papers, "
        f"{len(bundle.entities)} entities, {len(bundle.claims)} claims"
    )
    disputed = [c for c in bundle.claims if c.is_disputed]
    if disputed:
        console.print(f"[yellow]{len(disputed)} claim(s) carry contradicting evidence[/yellow]")
        for claim in disputed:
            console.print(
                f"  - {claim.subject.name} --{claim.predicate.value}--> {claim.object.name}"
            )


@app.command()
def init() -> None:
    """Create Neo4j constraints and indexes. Idempotent."""
    try:
        with session_scope() as session:
            applied = install_schema(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]schema installed[/green] ({len(applied)} statements)")


@app.command()
def load(
    seed_dir: Path = typer.Option(SEED_DIR, help="Directory of seed YAML files"),
) -> None:
    """Validate the seed files and ingest them. Safe to re-run."""
    try:
        bundle = load_dir(seed_dir)
    except SeedValidationError as exc:
        _fail(f"seed validation failed:\n{exc}")
        return
    try:
        with session_scope() as session:
            install_schema(session)
            report = ingest_bundle(session, bundle)
            counts = graph_counts(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return

    console.print("[bold]Run report[/bold]")
    console.print(
        f"  ingested: {report.papers} papers, {report.entities} entities, "
        f"{report.claims} claims, {report.evidence} evidence"
    )
    console.print(f"  graph now: {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}")
    console.print(f"  pending review: {report.pending_review}")
    if report.disputed_claims:
        console.print(f"[yellow]  disputed claims ({len(report.disputed_claims)}):[/yellow]")
        for line in report.disputed_claims:
            console.print(f"    - {line}")


@app.command()
def status() -> None:
    """Node counts and unprocessed-paper backlog."""
    try:
        with session_scope() as session:
            counts = graph_counts(session)
            backlog = unprocessed_papers(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("label", "count")
    for label, count in sorted(counts.items()):
        table.add_row(label, str(count))
    console.print(table)
    console.print(f"papers not yet full-text processed: {len(backlog)}")


@app.command()
def traits() -> None:
    """List every ornamental trait with its claim count."""
    try:
        with session_scope() as session:
            rows = list_traits(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("trait", "category", "composite", "claims")
    for row in rows:
        table.add_row(
            row["name"],
            row.get("category") or "",
            "yes" if row.get("is_composite") else "",
            str(row["claims"]),
        )
    console.print(table)


@app.command()
def dossier(
    name: str = typer.Argument(..., help="Trait name, e.g. hikari"),
    out: Path | None = typer.Option(None, help="Write to this file instead of stdout"),
) -> None:
    """Render the human-readable trait dossier. PRD §13."""
    try:
        with session_scope() as session:
            text = render_trait(session, name)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    except KeyError as exc:
        _fail(str(exc))
        return
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        console.print(f"[green]wrote[/green] {out}")
    else:
        console.print(text, markup=False, highlight=False)


@app.command("dossier-all")
def dossier_all(
    out_dir: Path = typer.Option(DOSSIER_DIR, help="Directory to write dossiers into"),
) -> None:
    """Render a dossier for every trait."""
    try:
        with session_scope() as session:
            names = [row["name"] for row in list_traits(session)]
            out_dir.mkdir(parents=True, exist_ok=True)
            for name in names:
                # Slugged, because trait names include spaces and parentheses
                # ("panda (pa) lab mutant") and those make for filenames that are
                # awkward in a shell and in a diff. The trait's own name is the
                # first line of every file.
                path = out_dir / f"{slugify(name)}.md"
                path.write_text(render_trait(session, name), encoding="utf-8")
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]wrote {len(names)} dossiers[/green] to {out_dir}")


@app.command()
def review() -> None:
    """Show the human-review queue. PRD §12."""
    try:
        with session_scope() as session:
            rows = review_queue(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("[green]review queue empty[/green]")
        return
    table = Table("subject", "predicate", "object", "sup", "con", "reasons", "note")
    for row in rows:
        table.add_row(
            row["subject"],
            row["predicate"],
            row["object"],
            str(row["supports"]),
            str(row["contradicts"]),
            ", ".join(row.get("reasons") or []),
            row.get("note") or "",
        )
    console.print(table)
    console.print(f"{len(rows)} claim(s) pending")
    console.print(
        "Set `review_status` and `review_note` on a :Claim to record a decision; "
        "the loader never overwrites either. Claim content comes from the seed "
        "files and is rewritten on every load."
    )


@app.command()
def disputed() -> None:
    """Claims with evidence on both sides. PRD §9."""
    try:
        with session_scope() as session:
            rows = disputed_claims(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no disputed claims")
        return
    table = Table("subject", "predicate", "object", "reasons")
    for row in rows:
        table.add_row(
            row["subject"], row["predicate"], row["object"], ", ".join(row.get("reasons") or [])
        )
    console.print(table)


@app.command("shared-genes")
def shared_genes_cmd() -> None:
    """Traits that share a gene. PRD §1.

    Pairs related by subsumption are excluded: an umbrella class and its member
    share a locus by construction, not by biology.
    """
    try:
        with session_scope() as session:
            rows = shared_genes(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no shared genes recorded")
        return
    table = Table("trait A", "trait B", "shared genes", "contested")
    for row in rows:
        table.add_row(
            row["trait_a"],
            row["trait_b"],
            ", ".join(row["shared_genes"]),
            "yes" if row["contested"] else "",
        )
    console.print(table)
    console.print(
        "Pairs related by subsumption are excluded, and a link with no supporting "
        "evidence is not a shared gene. 'contested' means at least one of the two "
        "links also carries contradicting evidence."
    )


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Free-text query over entity names and aliases"),
    limit: int = typer.Option(20),
) -> None:
    """Full-text search over entity names and aliases."""
    try:
        with session_scope() as session:
            rows = search(session, query, limit=limit)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("label", "name", "score")
    for row in rows:
        table.add_row(row["label"], row["name"], f"{row['score']:.2f}")
    console.print(table)


@app.command()
def export(
    out_dir: Path = typer.Option(EXPORT_DIR, help="Directory to write the dump into"),
) -> None:
    """Dump the whole graph to JSONL.

    The knowledge must not be trapped in a Docker volume; this is the backup path
    the storage ADR promises.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    nodes_path = out_dir / f"nodes-{stamp}.jsonl"
    rels_path = out_dir / f"relationships-{stamp}.jsonl"
    try:
        with session_scope() as session:
            with nodes_path.open("w", encoding="utf-8") as fh:
                for record in session.run(
                    "MATCH (n) RETURN labels(n) AS labels, properties(n) AS props"
                ):
                    fh.write(
                        json.dumps(
                            {"labels": record["labels"], "properties": record["props"]},
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n"
                    )
            with rels_path.open("w", encoding="utf-8") as fh:
                for record in session.run(
                    "MATCH (a)-[r]->(b) "
                    "RETURN a.id AS start, type(r) AS type, b.id AS end, "
                    "properties(r) AS props"
                ):
                    fh.write(
                        json.dumps(dict(record), ensure_ascii=False, default=str) + "\n"
                    )
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]exported[/green] {nodes_path.name}, {rels_path.name}")


if __name__ == "__main__":
    app()
