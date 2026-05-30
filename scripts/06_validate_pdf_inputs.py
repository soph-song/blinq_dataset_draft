#!/usr/bin/env python3
"""Validate BLINQ v1 local PDF manifest and release inputs."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from blinq_openai_utils import PDF_MANIFEST, RELEASE_JSONL, load_pdf_manifest, load_release_items, pdf_path_from_record


EXPECTED_GROUPS = {
    "BLINQ_QEC_001",
    "BLINQ_QALG_002",
    "BLINQ_QCOMM_003",
    "BLINQ_QHW_004",
    "BLINQ_QIT_005",
}
EXPECTED_PDF_CONDITIONS = {"original_pdf", "redacted_pdf"}
API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-files", action="store_true", default=True, help="Require local PDF files to exist.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not RELEASE_JSONL.exists():
        errors.append(f"Missing release dataset: {RELEASE_JSONL}")
    else:
        items = load_release_items()
        groups = {item["paper_group_id"] for item in items}
        conditions = {}
        for item in items:
            conditions.setdefault(item["paper_group_id"], set()).add(item["metadata_condition"])
        if len(items) != 15:
            errors.append(f"Release dataset has {len(items)} items, expected 15.")
        if groups != EXPECTED_GROUPS:
            errors.append(f"Release groups are {sorted(groups)}, expected {sorted(EXPECTED_GROUPS)}.")
        for group_id, group_conditions in conditions.items():
            if group_conditions != {"blinded", "real_metadata", "counterfactual_high_prestige"}:
                errors.append(f"{group_id} has metadata conditions {sorted(group_conditions)}.")

    if not PDF_MANIFEST.exists():
        errors.append(f"Missing PDF manifest: {PDF_MANIFEST}")
    else:
        manifest_text = PDF_MANIFEST.read_text(encoding="utf-8")
        if API_KEY_PATTERN.search(manifest_text):
            errors.append("Possible API key detected in PDF manifest.")
        rows = load_pdf_manifest()
        by_group: dict[str, set[str]] = {}
        for row in rows:
            by_group.setdefault(row["paper_group_id"], set()).add(row["pdf_condition"])
            path = pdf_path_from_record(row)
            if args.require_files and not path.exists():
                errors.append(f"Missing local PDF: {path}")
                continue
            if path.exists():
                actual_size = path.stat().st_size
                expected_size = int(row["file_size_bytes"]) if row.get("file_size_bytes") else actual_size
                if actual_size != expected_size:
                    errors.append(f"Size mismatch for {path}: manifest {expected_size}, actual {actual_size}")
                expected_sha = row.get("sha256", "")
                if expected_sha and sha256_file(path) != expected_sha:
                    errors.append(f"SHA256 mismatch for {path}")
                if row["pdf_condition"] == "redacted_pdf" and row["source_arxiv_id"] in row["filename"]:
                    errors.append(f"Redacted filename contains arXiv id: {row['filename']}")
        if set(by_group) != EXPECTED_GROUPS:
            errors.append(f"PDF manifest groups are {sorted(by_group)}, expected {sorted(EXPECTED_GROUPS)}.")
        for group_id, conditions in by_group.items():
            if conditions != EXPECTED_PDF_CONDITIONS:
                errors.append(f"PDF manifest {group_id} has conditions {sorted(conditions)}.")

    print("PDF input validation summary")
    print(f"- Errors: {len(errors)}")
    print(f"- Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[FAIL] {error}")
    if not errors:
        print("[PASS] PDF manifest and release dataset are valid for local OpenAI PDF evaluation.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
