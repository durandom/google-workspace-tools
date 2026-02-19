#!/usr/bin/env python3
"""Scratch prototype: Read Google Docs suggestions (Änderungsvorschläge).

Uses the existing gwt authentication infrastructure to fetch a document
with suggestionsViewMode=SUGGESTIONS_INLINE and extract all pending suggestions.

Usage:
    uv run python docs/research/suggestions_prototype.py <document_url_or_id>
"""

import json
import re
import sys
from collections import defaultdict

from googleapiclient.discovery import build

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter


def extract_document_id(url_or_id: str) -> str:
    """Extract document ID from a Google Docs URL or return as-is if already an ID."""
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url_or_id)
    return match.group(1) if match else url_or_id


def fetch_doc_with_suggestions(doc_id: str) -> dict:
    """Fetch a Google Doc with suggestions visible inline."""
    config = GoogleDriveExporterConfig()
    exporter = GoogleDriveExporter(config)

    # Trigger authentication via existing gwt infrastructure
    creds = exporter._authenticate()
    docs_service = build("docs", "v1", credentials=creds)

    # Fetch with SUGGESTIONS_INLINE to see all pending suggestions
    doc = (
        docs_service.documents()
        .get(
            documentId=doc_id,
            suggestionsViewMode="SUGGESTIONS_INLINE",
        )
        .execute()
    )

    return doc


def extract_suggestions(doc: dict) -> list[dict]:
    """Walk the document body and extract all suggestions.

    Returns a list of suggestion dicts with:
      - suggestion_id: The suggestion ID
      - type: "insertion", "deletion", or "style_change"
      - content: The text content affected
      - paragraph_context: Surrounding paragraph text for context
    """
    suggestions = []
    body = doc.get("body", {})
    content = body.get("content", [])

    for element in content:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue

        # Build full paragraph text for context
        para_text = ""
        for pe in paragraph.get("elements", []):
            text_run = pe.get("textRun", {})
            para_text += text_run.get("content", "")

        para_text = para_text.strip()

        for pe in paragraph.get("elements", []):
            text_run = pe.get("textRun", {})
            content_text = text_run.get("content", "")

            # Suggested insertions
            insertion_ids = text_run.get("suggestedInsertionIds", [])
            for sid in insertion_ids:
                suggestions.append(
                    {
                        "suggestion_id": sid,
                        "type": "insertion",
                        "content": content_text,
                        "paragraph_context": para_text,
                    }
                )

            # Suggested deletions
            deletion_ids = text_run.get("suggestedDeletionIds", [])
            for sid in deletion_ids:
                suggestions.append(
                    {
                        "suggestion_id": sid,
                        "type": "deletion",
                        "content": content_text,
                        "paragraph_context": para_text,
                    }
                )

            # Suggested style changes
            style_changes = text_run.get("suggestedTextStyleChanges", {})
            for sid, change in style_changes.items():
                suggestions.append(
                    {
                        "suggestion_id": sid,
                        "type": "style_change",
                        "content": content_text,
                        "style": change.get("textStyle", {}),
                        "paragraph_context": para_text,
                    }
                )

        # Paragraph-level suggestion changes
        para_style_changes = paragraph.get("suggestedParagraphStyleChanges", {})
        for sid, change in para_style_changes.items():
            suggestions.append(
                {
                    "suggestion_id": sid,
                    "type": "paragraph_style_change",
                    "content": para_text,
                    "style": change.get("paragraphStyle", {}),
                    "paragraph_context": para_text,
                }
            )

        para_bullet_changes = paragraph.get("suggestedBulletChanges", {})
        for sid, change in para_bullet_changes.items():
            suggestions.append(
                {
                    "suggestion_id": sid,
                    "type": "bullet_change",
                    "content": para_text,
                    "bullet": change.get("bullet", {}),
                    "paragraph_context": para_text,
                }
            )

    return suggestions


def print_suggestions(suggestions: list[dict]) -> None:
    """Pretty-print suggestions grouped by suggestion ID."""
    if not suggestions:
        print("\n  No pending suggestions found in this document.")
        return

    # Group by suggestion_id
    grouped = defaultdict(list)
    for s in suggestions:
        grouped[s["suggestion_id"]].append(s)

    print(f"\n  Found {len(suggestions)} suggestion(s) across {len(grouped)} suggestion ID(s):\n")

    for sid, items in grouped.items():
        print(f"  Suggestion: {sid}")
        print(f"  {'─' * 60}")
        for item in items:
            type_icon = {
                "insertion": "+ INSERT",
                "deletion": "- DELETE",
                "style_change": "~ STYLE",
                "paragraph_style_change": "~ PARA STYLE",
                "bullet_change": "~ BULLET",
            }.get(item["type"], "? UNKNOWN")

            print(f"    [{type_icon}] {item['content']!r}")
            if item["type"] == "style_change":
                print(f"             Style: {item.get('style', {})}")
            if item.get("paragraph_context") and item["paragraph_context"] != item["content"]:
                ctx = item["paragraph_context"][:80]
                print(f"             Context: {ctx}...")
        print()


def compare_versions(doc_id: str) -> None:
    """Fetch and compare the document in all three suggestion view modes."""
    config = GoogleDriveExporterConfig()
    exporter = GoogleDriveExporter(config)
    creds = exporter._authenticate()
    docs_service = build("docs", "v1", credentials=creds)

    modes = [
        ("SUGGESTIONS_INLINE", "With suggestions inline"),
        ("PREVIEW_WITHOUT_SUGGESTIONS", "Without suggestions (original)"),
        ("PREVIEW_SUGGESTIONS_ACCEPTED", "With all suggestions accepted"),
    ]

    texts = {}
    for mode, label in modes:
        doc = (
            docs_service.documents()
            .get(
                documentId=doc_id,
                suggestionsViewMode=mode,
            )
            .execute()
        )

        # Extract plain text
        plain = ""
        for element in doc.get("body", {}).get("content", []):
            para = element.get("paragraph")
            if para:
                for pe in para.get("elements", []):
                    plain += pe.get("textRun", {}).get("content", "")

        texts[mode] = plain
        print(f"\n  === {label} ({mode}) ===")
        print(f"  Length: {len(plain)} chars")

    # Show diff between original and accepted
    if texts["PREVIEW_WITHOUT_SUGGESTIONS"] != texts["PREVIEW_SUGGESTIONS_ACCEPTED"]:
        print("\n  === DIFF: Original vs Accepted ===")
        orig_lines = texts["PREVIEW_WITHOUT_SUGGESTIONS"].splitlines()
        accepted_lines = texts["PREVIEW_SUGGESTIONS_ACCEPTED"].splitlines()

        max_lines = max(len(orig_lines), len(accepted_lines))
        for i in range(max_lines):
            orig = orig_lines[i] if i < len(orig_lines) else ""
            acc = accepted_lines[i] if i < len(accepted_lines) else ""
            if orig != acc:
                print(f"  Line {i + 1}:")
                print(f"    - {orig!r}")
                print(f"    + {acc!r}")
    else:
        print("\n  No difference between original and accepted (no pending suggestions).")


def dump_raw(doc: dict, output_path: str = "scratch_doc_raw.json") -> None:
    """Dump the raw document JSON for inspection."""
    with open(output_path, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"\n  Raw document JSON saved to: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scratch_suggestions.py <document_url_or_id> [--raw] [--compare]")
        sys.exit(1)

    url_or_id = sys.argv[1]
    flags = sys.argv[2:]

    doc_id = extract_document_id(url_or_id)
    print(f"  Document ID: {doc_id}")

    # Fetch document with suggestions inline
    print("  Fetching document with SUGGESTIONS_INLINE...")
    doc = fetch_doc_with_suggestions(doc_id)
    print(f"  Title: {doc.get('title', 'Untitled')}")

    # Extract and display suggestions
    suggestions = extract_suggestions(doc)
    print_suggestions(suggestions)

    # Optional: dump raw JSON
    if "--raw" in flags:
        dump_raw(doc)

    # Optional: compare all three view modes
    if "--compare" in flags:
        compare_versions(doc_id)


if __name__ == "__main__":
    main()
