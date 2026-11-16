#!/usr/bin/env python3
"""Local RM bookmark lookup and bounded, source-attributed PDF excerpts."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

try:
    import pypdfium2 as pdfium
except ModuleNotFoundError as exc:
    if exc.name != "pypdfium2":
        raise
    raise SystemExit(
        "Missing pypdfium2. Install with: python -m pip install -r "
        f'"{Path(__file__).with_name("requirements.txt")}"'
    ) from exc


SCHEMA_VERSION = 1
BACKEND_VERSION = importlib.metadata.version("pypdfium2")
DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "SoC_material"
NOTICE = (
    "PDF pages are 1-based; PDF labels may differ from printed page numbers. "
    "Bookmark ranges include the next boundary page and may contain adjacent sections. "
    "Plain text does not preserve figures or guarantee table layout; verify those in the PDF."
)


class RMError(RuntimeError):
    pass


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RMError(f"Invalid generated cache {path}: {exc}. Remove that cache file and retry.") from exc


def sidecar(pdf: Path) -> Path:
    return pdf.with_name(pdf.name + ".index")


def catalog(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise RMError(f"RM root is not a directory: {root}")
    return [
        {"chip": path.parent.parent.name, "pdf_path": str(path.resolve()),
         "pdf_name": path.name, "size_bytes": path.stat().st_size}
        for path in sorted(root.glob("*/RM/*.pdf"))
        if path.is_file()
    ]


def resolve_pdf(target: str, root: Path) -> Path:
    explicit = Path(target).expanduser()
    if explicit.is_file():
        if explicit.suffix.casefold() != ".pdf":
            raise RMError(f"Expected a PDF file: {explicit}")
        return explicit.resolve()
    if explicit.suffix.casefold() == ".pdf" or any(char in target for char in "\\/"):
        raise RMError(f"PDF not found: {explicit}")
    matches = [item for item in catalog(root) if item["chip"].casefold() == target.casefold()]
    if not matches:
        raise RMError(f"No RM for {target!r} under {root}; use list or an explicit PDF path.")
    if len(matches) != 1:
        raise RMError(
            f"Ambiguous RM for {target!r}; select an explicit PDF path:\n"
            + "\n".join(item["pdf_path"] for item in matches)
        )
    return Path(matches[0]["pdf_path"])


def words(text: str) -> set[str]:
    words = set(re.findall(r"[a-z]+|[^\W\d_a-z]+", text.casefold()))
    return words - {
        "a", "an", "and", "are", "can", "does", "for", "how", "in", "is", "of",
        "on", "the", "to", "what", "with",
    }


def terms(text: str) -> set[str]:
    expanded_terms = words(text)
    for abbreviation, expanded in (
        ("clk", "clock"), ("ext", "external"), ("irq", "interrupt"), ("iomux", "multiplexing"),
        ("pad", "pin"),
    ):
        if abbreviation in expanded_terms:
            expanded_terms.add(expanded)
    return expanded_terms


def index_sections(document: pdfium.PdfDocument) -> tuple[list[dict[str, Any]], int]:
    sections: list[dict[str, Any]] = []
    ancestors: list[tuple[int, str]] = []
    pending: list[dict[str, Any]] = []
    skipped = 0
    # Populate PDFium's page-directory cache before resolving thousands of destinations.
    for number in range(len(document)):
        document.get_page_size(number)
    for ordinal, bookmark in enumerate(document.get_toc(max_depth=64), 1):
        title = bookmark.get_title().strip()
        while ancestors and ancestors[-1][0] >= bookmark.level:
            ancestors.pop()
        breadcrumb = " > ".join([entry[1] for entry in ancestors] + [title])
        ancestors.append((bookmark.level, title))
        destination = bookmark.get_dest()
        page_index = destination.get_index() if destination is not None else None
        if page_index is None or not 0 <= page_index < len(document):
            skipped += 1
            continue
        match = re.match(r"^(?:Chapter\s+)?(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)(?:[.\s]+|$)", title)
        entry = {
            "id": match.group(1) if match else f"bookmark-{ordinal}",
            "title": title, "path": breadcrumb, "level": bookmark.level,
            "page_start": page_index + 1, "page_end": len(document),
        }
        while pending and pending[-1]["level"] >= bookmark.level:
            previous = pending.pop()
            if entry["page_start"] < previous["page_start"]:
                previous["range_error"] = "Bookmarks are out of reading order; use explicit --pages."
                previous["page_end"] = previous["page_start"]
            else:
                # The boundary page can contain the end of the preceding section.
                previous["page_end"] = entry["page_start"]
        pending.append(entry)
        sections.append(entry)
    return sections, skipped


def ensure_index(pdf: Path, force: bool = False) -> tuple[dict[str, Any], bool]:
    fingerprint = file_hash(pdf)
    destination = sidecar(pdf) / "index.json"
    if destination.exists() and not force:
        cached = read_json(destination)
        if not isinstance(cached, dict):
            raise RMError(f"Invalid index {destination}; run build --force.")
        if (
            cached.get("schema_version") == SCHEMA_VERSION
            and cached.get("sha256") == fingerprint
            and cached.get("backend_version") == BACKEND_VERSION
            and cached.get("pdf_path") == str(pdf)
        ):
            sections = cached.get("sections")
            page_count = cached.get("page_count")
            if not isinstance(page_count, int) or page_count < 1 or not isinstance(sections, list):
                raise RMError(f"Invalid index {destination}; run build --force.")
            for entry in sections:
                if (
                    not isinstance(entry, dict)
                    or not all(isinstance(entry.get(key), str) for key in ("id", "title", "path"))
                    or not all(isinstance(entry.get(key), int) for key in ("level", "page_start", "page_end"))
                    or not 1 <= entry["page_start"] <= entry["page_end"] <= page_count
                ):
                    raise RMError(f"Invalid section in {destination}; run build --force.")
            return cached, True
    with pdfium.PdfDocument(pdf) as document:
        if len(document) == 0:
            raise RMError(f"PDF has no pages: {pdf}")
        sections, skipped = index_sections(document)
        index = {
            "schema_version": SCHEMA_VERSION, "backend_version": BACKEND_VERSION,
            "pdf_path": str(pdf), "sha256": fingerprint, "size_bytes": pdf.stat().st_size,
            "page_count": len(document), "sections": sections, "unresolved_bookmarks": skipped,
        }
    if file_hash(pdf) != fingerprint:
        raise RMError(f"PDF changed while indexing: {pdf}; retry with a stable file.")
    contents = [f"# {pdf.name}", "", f"SHA-256: `{fingerprint}`", "", NOTICE, ""]
    contents.extend(
        f'{"  " * row["level"]}- {row["title"]} '
        f'(PDF {row["page_start"]}-{row["page_end"]}; id: {row["id"]})'
        for row in sections
    )
    if not sections:
        contents.append("No navigable bookmarks; use explicit PDF page ranges.")
    atomic_write(sidecar(pdf) / "CONTENTS.generated.md", "\n".join(contents) + "\n")
    write_json(destination, index)
    return index, False


def identity(index: dict[str, Any]) -> dict[str, Any]:
    return {key: index[key] for key in ("pdf_path", "sha256", "page_count")}


def select_pages(
    index: dict[str, Any], section: str | None, pages: str | None, context: int, maximum: int,
) -> tuple[int, int]:
    if (section is None) == (pages is None):
        raise RMError("Select exactly one section id or --pages START:END (1-based PDF pages).")
    if section is not None:
        matches = [entry for entry in index["sections"] if entry["id"] == section]
        if len(matches) != 1:
            raise RMError(f"Section {section!r} has {len(matches)} matches; use toc or explicit --pages.")
        if matches[0].get("range_error"):
            raise RMError(matches[0]["range_error"])
        start, end = matches[0]["page_start"], matches[0]["page_end"]
    else:
        if pages is None or re.fullmatch(r"\d+(?::\d+)?", pages) is None:
            raise RMError("--pages must be N or START:END using 1-based PDF page numbers.")
        first, _, last = pages.partition(":")
        start, end = int(first), int(last or first)
    if not 1 <= start <= end <= index["page_count"]:
        raise RMError(f"PDF page range must satisfy 1 <= start <= end <= {index['page_count']}.")
    start, end = max(1, start - context), min(index["page_count"], end + context)
    if end - start + 1 > maximum:
        raise RMError(
            f"Selection spans {end - start + 1} pages (limit {maximum}); "
            "choose a smaller section/--pages range or explicitly increase --max-pages."
        )
    return start, end


def read_pages(pdf: Path, index: dict[str, Any], start: int, end: int) -> list[dict[str, Any]]:
    pages: dict[int, dict[str, Any]] = {}
    missing: list[int] = []
    for number in range(start, end + 1):
        cached_path = sidecar(pdf) / "pages" / f"{number:05d}.json"
        if cached_path.exists():
            cached = read_json(cached_path)
            if not isinstance(cached, dict):
                raise RMError(f"Invalid page cache {cached_path}; remove that cache file and retry.")
            if (
                cached.get("sha256") == index["sha256"]
                and cached.get("backend_version") == BACKEND_VERSION
                and cached.get("schema_version") == SCHEMA_VERSION
            ):
                if (
                    cached.get("pdf_page") != number or not isinstance(cached.get("text"), str)
                    or not isinstance(cached.get("page_label"), str)
                ):
                    raise RMError(f"Invalid page cache {cached_path}; remove that cache file and retry.")
                pages[number] = cached
                continue
        missing.append(number)
    if missing:
        with pdfium.PdfDocument(pdf) as document:
            for number in missing:
                with closing(document.get_page(number - 1)) as page:
                    with closing(page.get_textpage()) as text_page:
                        text = text_page.get_text_bounded(errors="strict").replace("\r\n", "\n")
                pages[number] = {
                    "sha256": index["sha256"], "backend_version": BACKEND_VERSION,
                    "schema_version": SCHEMA_VERSION,
                    "pdf_page": number, "page_label": document.get_page_label(number - 1),
                    "text": text,
                }
        if file_hash(pdf) != index["sha256"]:
            raise RMError(f"PDF changed while extracting: {pdf}; retry with a stable file.")
        for number in missing:
            write_json(sidecar(pdf) / "pages" / f"{number:05d}.json", pages[number])
    return [
        {key: pages[number][key] for key in ("pdf_page", "page_label", "text")}
        for number in range(start, end + 1)
    ]


def lookup(index: dict[str, Any], query: str, limit: int) -> tuple[list[dict[str, Any]], int]:
    query_terms = terms(query)
    if not query_terms:
        raise RMError("Query must contain searchable words, not only numbers or punctuation.")
    rows = [(row, terms(row["title"]), terms(row["path"])) for row in index["sections"]]
    frequencies = {
        term: sum(term in title_terms for _, title_terms, _ in rows)
        for term in words(query)
    }
    candidates = [term for term, count in frequencies.items() if count]
    if not candidates:
        frequencies = {
            term: sum(term in title_terms for _, title_terms, _ in rows)
            for term in query_terms
        }
        candidates = [term for term, count in frequencies.items() if count]
    instances = re.findall(r"(?<![a-z0-9])([a-z]+)(\d+)(?![a-z0-9])", query.casefold())
    primary_candidates = [family for family, _ in instances if frequencies.get(family)] or candidates
    primary = (
        min(primary_candidates, key=lambda term: (frequencies[term], -len(term), term))
        if primary_candidates else ""
    )
    matches = []
    for section, title_terms, path_terms in rows:
        conflict = False
        for family, number in instances:
            found = set(re.findall(
                rf"(?<![a-z0-9]){re.escape(family)}(\d+)(?![a-z0-9])",
                section["path"].casefold(),
            ))
            if found and number not in found:
                conflict = True
                break
        if conflict:
            continue
        title_hits = query_terms & title_terms
        path_hits = query_terms & path_terms
        if not path_hits:
            continue
        score = len(title_hits) * 4 + len(path_hits)
        matched_by = "companion"
        if primary in title_terms:
            score += 40
            matched_by = "primary-title"
            if re.fullmatch(r"\d+|[A-Z]", section["id"]):
                score += 40
                matched_by = "owner-chapter"
        elif primary in path_terms:
            score += 20
            matched_by = "primary-path"
        matches.append({
            **section, "score": score, "matched_terms": sorted(path_hits),
            "primary_term": primary, "matched_by": matched_by,
        })
    matches.sort(key=lambda entry: (-entry["score"], entry["level"], entry["page_start"]))
    if not matches:
        raise RMError("No matching bookmark titles; use toc or search within an explicit page range.")
    return matches[:limit], len(matches)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "list":
        return {"root": str(args.root.resolve()), "documents": catalog(args.root)}
    if args.command == "build":
        targets = (
            [Path(item["pdf_path"]) for item in catalog(args.root)]
            if args.target == "all" else [resolve_pdf(args.target, args.root)]
        )
        if not targets:
            raise RMError(f"No PDFs found under {args.root}.")
        documents = []
        for pdf in targets:
            index, hit = ensure_index(pdf, args.force)
            documents.append({
                **identity(index), "section_count": len(index["sections"]),
                "unresolved_bookmarks": index["unresolved_bookmarks"], "index_cache_hit": hit,
                "index_path": str(sidecar(pdf) / "index.json"),
            })
        return {"documents": documents}
    pdf = resolve_pdf(args.target, args.root)
    index, hit = ensure_index(pdf)
    result = {**identity(index), "index_cache_hit": hit, "notice": NOTICE}
    if args.command == "lookup":
        matches, total = lookup(index, args.query, args.limit)
        return {**result, "query": args.query, "matches": matches, "total_matches": total}
    if args.command == "toc":
        sections = [row for row in index["sections"] if row["level"] < args.depth]
        if args.query:
            selected = terms(args.query)
            if not selected:
                raise RMError("TOC query must contain searchable words.")
            sections = [row for row in sections if selected & terms(row["path"])]
        return {
            **result, "sections": sections[:args.limit], "total_matches": len(sections),
            "unresolved_bookmarks": index["unresolved_bookmarks"],
        }
    start, end = select_pages(
        index, args.section, args.pages, args.context_pages, args.max_pages,
    )
    pages = read_pages(pdf, index, start, end)
    empty_pages = [row["pdf_page"] for row in pages if not row["text"].strip()]
    if len(empty_pages) == len(pages):
        raise RMError("Selected pages contain no text layer; inspect the original PDF. OCR is not provided.")
    result.update({
        "pdf_page_start": start, "pdf_page_end": end, "text_layer_missing_pages": empty_pages,
    })
    if args.command == "extract":
        return {**result, "pages": pages}
    matches = []
    total = 0
    for page in pages:
        for match in re.finditer(re.escape(args.query), page["text"], flags=re.IGNORECASE):
            total += 1
            if len(matches) < args.limit:
                snippet = page["text"][max(0, match.start() - 80):match.end() + 80]
                matches.append({
                    "pdf_page": page["pdf_page"], "page_label": page["page_label"],
                    "snippet": " ".join(snippet.split()),
                })
    return {**result, "query": args.query, "matches": matches, "total_matches": total}


def positive(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def nonnegative(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="SoC_material directory")
    common.add_argument("--json", action="store_true", help="emit source-attributed JSON")
    commands = command.add_subparsers(dest="command", required=True)
    commands.add_parser("list", parents=[common], help="list local */RM/*.pdf candidates")
    build = commands.add_parser("build", parents=[common], help="build or reuse bookmark indexes")
    build.add_argument("target", help="chip id, PDF path, or all")
    build.add_argument("--force", action="store_true")
    for name in ("toc", "lookup", "extract", "search"):
        sub = commands.add_parser(name, parents=[common])
        sub.add_argument("target", help="chip directory name or explicit PDF path")
        if name in {"toc", "lookup", "search"}:
            sub.add_argument("query", nargs="?" if name == "toc" else None, default="")
            sub.add_argument("--limit", type=positive, default=20 if name != "lookup" else 8)
        if name == "toc":
            sub.add_argument("--depth", type=positive, default=2, help="bookmark levels to include")
        if name in {"extract", "search"}:
            if name == "extract":
                sub.add_argument("section", nargs="?", help="section id from toc/lookup")
                sub.add_argument("--pages", help="1-based PDF page N or START:END")
            else:
                selection = sub.add_mutually_exclusive_group(required=True)
                selection.add_argument("--section", help="section id from toc/lookup")
                selection.add_argument("--pages", help="1-based PDF page N or START:END")
            sub.add_argument("--context-pages", type=nonnegative, default=0)
            sub.add_argument("--max-pages", type=positive, default=20)
    return command


def render(result: dict[str, Any]) -> str:
    if "documents" in result:
        rows = result["documents"]
        if not rows:
            return "No local RM PDFs found."
        return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    lines = [
        f'PDF: {result["pdf_path"]}', f'SHA-256: {result["sha256"]}', result["notice"],
    ]
    for row in result.get("sections", result.get("matches", [])):
        if "title" in row:
            lines.append(f'{row["id"]}  PDF {row["page_start"]}-{row["page_end"]}  {row["path"]}')
        else:
            lines.append(f'PDF {row["pdf_page"]} (label: {row["page_label"] or "not supplied"}): {row["snippet"]}')
    for page in result.get("pages", []):
        lines.extend([
            f'\n--- PDF page {page["pdf_page"]}; label: {page["page_label"] or "not supplied"} ---',
            page["text"],
        ])
    if result.get("text_layer_missing_pages"):
        lines.append(f'WARNING: no text layer on PDF pages {result["text_layer_missing_pages"]}.')
    if "total_matches" in result:
        shown = len(result.get("sections", result.get("matches", [])))
        lines.append(f'{shown} shown / {result["total_matches"]} matches')
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if hasattr(args, "query") and args.command != "toc" and not args.query.strip():
            raise RMError("Query must not be empty.")
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
        return 0
    except (RMError, OSError, pdfium.PdfiumError) as exc:
        print(f"imx-rm: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
