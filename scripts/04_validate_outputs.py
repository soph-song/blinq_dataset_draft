#!/usr/bin/env python3
"""Validate BLINQ dataset-draft outputs."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "quant_ph_candidate_pool_1000.csv"
SCREENING_CSV = PROJECT_ROOT / "data" / "screening" / "candidate_screening_100.csv"
JSONL_OUT = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15.jsonl"
CSV_OUT = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15.csv"
RUBRIC_OUT = PROJECT_ROOT / "data" / "pilot" / "rubric_v1.md"
PROMPT_OUT = PROJECT_ROOT / "data" / "pilot" / "model_eval_prompt_template.md"
DATASET_CARD_OUT = PROJECT_ROOT / "data" / "pilot" / "dataset_card.md"
RELEASE_JSONL = PROJECT_ROOT / "data" / "release" / "blinq_v1_items.jsonl"
RELEASE_CSV = PROJECT_ROOT / "data" / "release" / "blinq_v1_items.csv"
REFERENCE_LABELS = PROJECT_ROOT / "data" / "release" / "reference_labels_v1.csv"
RAW_REFERENCE_LABELS = PROJECT_ROOT / "data" / "annotations" / "raw_reference_labels.csv"
PDF_MANIFEST = PROJECT_ROOT / "data" / "release" / "pdf_manifest_v1.csv"
RELEASE_SCHEMA = PROJECT_ROOT / "data" / "release" / "blinq_v1_schema.md"
RELEASE_DATASET_CARD = PROJECT_ROOT / "data" / "release" / "dataset_card_v1.md"
RELEASE_SUMMARY = PROJECT_ROOT / "reports" / "release_summary_v1.md"
REFERENCE_AGGREGATION_REPORT = PROJECT_ROOT / "reports" / "reference_label_aggregation.md"

TARGET_POOL_SIZE = 1000
SCREEN_SAMPLE_SIZE = 100
REQUIRED_CONDITIONS = {"blinded", "real_metadata", "counterfactual_high_prestige"}
REQUIRED_PDF_CONDITIONS = {"original_pdf", "redacted_pdf"}
EXPECTED_GROUPS = {
    "BLINQ_QEC_001",
    "BLINQ_QALG_002",
    "BLINQ_QCOMM_003",
    "BLINQ_QHW_004",
    "BLINQ_QIT_005",
}
ALLOWED_SYNTHETIC_AUTHORS = {
    "Synthetic High-Prestige Author A",
    "Synthetic High-Prestige Author B",
}
ALLOWED_SYNTHETIC_AFFILIATIONS = {
    "Synthetic High-Prestige Quantum Institute",
    "Synthetic Elite University Quantum Center",
}
EXPECTED_POOL_COLUMNS = {
    "arxiv_id",
    "title",
    "abstract",
    "authors",
    "published",
    "updated",
    "primary_category",
    "all_categories",
    "comments",
    "journal_ref",
    "doi",
    "abstract_url",
    "pdf_url",
    "collection_query",
    "collection_year",
}
EXPECTED_SCREENING_COLUMNS = EXPECTED_POOL_COLUMNS | {
    "screen_id",
    "qis_relevance_label",
    "qis_subfield",
    "paper_type",
    "screening_reason",
    "key_qis_terms",
    "selected_for_pilot",
    "recognition_flag",
    "manual_review_needed",
}
EXPECTED_REFERENCE_COLUMNS = {
    "paper_group_id",
    "source_arxiv_id",
    "included_reviewers",
    "discarded_familiarity_flagged",
    "editorial_priority_majority",
    "technical_soundness_mean",
    "evidence_support_mean",
    "novelty_mean",
    "significance_mean",
    "clarity_mean",
    "overall_merit_mean",
}
EXPECTED_PDF_MANIFEST_COLUMNS = {
    "paper_group_id",
    "source_arxiv_id",
    "title",
    "pdf_condition",
    "local_source_folder",
    "filename",
    "expected_local_path",
    "sha256",
    "file_size_bytes",
    "page_count_rough",
    "intended_metadata_condition",
    "redaction_status",
    "repository_distribution",
    "notes",
}
API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_number} is invalid JSON: {exc}") from exc
    return items


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def pass_(self, message: str) -> None:
        print(f"[PASS] {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def fail(self, message: str) -> None:
        self.errors.append(message)
        print(f"[FAIL] {message}")


def validate_pool(v: Validation, pool: pd.DataFrame) -> None:
    if not RAW_CSV.exists():
        v.fail(f"Candidate pool is missing: {RAW_CSV}")
        return
    missing = EXPECTED_POOL_COLUMNS - set(pool.columns)
    if missing:
        v.fail(f"Candidate pool is missing columns: {sorted(missing)}")
    else:
        v.pass_("Candidate pool exists and has expected columns.")

    if len(pool) == TARGET_POOL_SIZE:
        v.pass_(f"Candidate pool has expected {TARGET_POOL_SIZE} records.")
    elif len(pool) == 0:
        v.warn("Candidate pool exists but has 0 records, likely because collection could not run.")
    else:
        v.warn(f"Candidate pool has {len(pool)} records, not target {TARGET_POOL_SIZE}.")


def validate_screening(v: Validation, pool: pd.DataFrame, screening: pd.DataFrame) -> None:
    if not SCREENING_CSV.exists():
        v.fail(f"Screening table is missing: {SCREENING_CSV}")
        return
    missing = EXPECTED_SCREENING_COLUMNS - set(screening.columns)
    if missing and len(screening) > 0:
        v.fail(f"Screening table is missing columns: {sorted(missing)}")
    elif len(screening) == 0:
        v.warn("Screening table exists but has 0 rows.")
    else:
        v.pass_("Screening table exists and has expected columns.")

    expected_rows = min(SCREEN_SAMPLE_SIZE, len(pool))
    if len(pool) >= SCREEN_SAMPLE_SIZE and len(screening) != SCREEN_SAMPLE_SIZE:
        v.fail(f"Screening table has {len(screening)} rows, expected {SCREEN_SAMPLE_SIZE}.")
    elif len(pool) < SCREEN_SAMPLE_SIZE and len(screening) != expected_rows:
        v.warn(f"Screening table has {len(screening)} rows; source data supports {expected_rows}.")
    else:
        v.pass_(f"Screening row count is consistent with source data: {len(screening)}.")


def validate_pilot_files(v: Validation) -> list[dict[str, Any]]:
    for path in [JSONL_OUT, CSV_OUT, RUBRIC_OUT, PROMPT_OUT, DATASET_CARD_OUT]:
        if path.exists():
            v.pass_(f"Found {path.relative_to(PROJECT_ROOT)}.")
        else:
            v.fail(f"Missing {path.relative_to(PROJECT_ROOT)}.")
    try:
        return load_jsonl(JSONL_OUT)
    except ValueError as exc:
        v.fail(str(exc))
        return []


def validate_pilot_items(v: Validation, screening: pd.DataFrame, items: list[dict[str, Any]]) -> None:
    in_scope_count = (
        int((screening["qis_relevance_label"] == "in_scope").sum())
        if "qis_relevance_label" in screening.columns
        else 0
    )
    if in_scope_count >= 5 and len(items) != 15:
        v.fail(f"Pilot has {len(items)} items, expected 15 because at least 5 in-scope papers exist.")
    elif len(items) == 15:
        v.pass_("Pilot contains 15 items.")
    else:
        v.warn(f"Pilot contains {len(items)} items; fewer than 5 in-scope papers may be available.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[item.get("paper_group_id", "")].append(item)

    for group_id, group_items in groups.items():
        conditions = {item.get("metadata_condition") for item in group_items}
        if len(group_items) != 3:
            v.fail(f"{group_id} has {len(group_items)} items, expected 3.")
        elif conditions != REQUIRED_CONDITIONS:
            v.fail(f"{group_id} has conditions {sorted(conditions)}, expected {sorted(REQUIRED_CONDITIONS)}.")
        else:
            v.pass_(f"{group_id} has exactly the three required metadata conditions.")

    for item in items:
        condition = item.get("metadata_condition")
        metadata = item.get("metadata", {})
        if condition == "blinded":
            if metadata.get("authors") is not None or metadata.get("affiliations") is not None:
                v.fail(f"{item.get('item_id')} is blinded but has author or affiliation metadata.")
        if condition == "counterfactual_high_prestige":
            authors = metadata.get("authors") or []
            affiliations = metadata.get("affiliations") or []
            if set(authors) != ALLOWED_SYNTHETIC_AUTHORS:
                v.fail(f"{item.get('item_id')} has unexpected counterfactual authors: {authors}")
            if set(affiliations) != ALLOWED_SYNTHETIC_AFFILIATIONS:
                v.fail(f"{item.get('item_id')} has unexpected counterfactual affiliations: {affiliations}")
            if not all(str(author).startswith("Synthetic ") for author in authors):
                v.fail(f"{item.get('item_id')} uses real-looking counterfactual author names.")

        reference_answer = item.get("reference_answer", {})
        for key, value in reference_answer.items():
            if not (isinstance(value, str) and value.startswith("TBD")):
                v.fail(f"{item.get('item_id')} reference label {key} is not marked TBD: {value}")

    if items:
        v.pass_("Blinded metadata, synthetic metadata, and TBD reference-label checks completed.")


def validate_release_files(v: Validation) -> list[dict[str, Any]]:
    for path in [
        RELEASE_JSONL,
        RELEASE_CSV,
        REFERENCE_LABELS,
        RAW_REFERENCE_LABELS,
        PDF_MANIFEST,
        RELEASE_SCHEMA,
        RELEASE_DATASET_CARD,
        RELEASE_SUMMARY,
        REFERENCE_AGGREGATION_REPORT,
    ]:
        if path.exists():
            v.pass_(f"Found {path.relative_to(PROJECT_ROOT)}.")
        else:
            v.fail(f"Missing {path.relative_to(PROJECT_ROOT)}.")
    try:
        return load_jsonl(RELEASE_JSONL)
    except ValueError as exc:
        v.fail(str(exc))
        return []


def validate_release_items(v: Validation, items: list[dict[str, Any]]) -> None:
    if not items:
        v.fail("Release dataset is empty.")
        return
    if len(items) == 15:
        v.pass_("Release dataset contains 15 items.")
    else:
        v.fail(f"Release dataset contains {len(items)} items, expected 15.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[item.get("paper_group_id", "")].append(item)
    if set(groups) == EXPECTED_GROUPS:
        v.pass_("Release dataset contains the expected five paper groups.")
    else:
        v.fail(f"Release groups are {sorted(groups)}, expected {sorted(EXPECTED_GROUPS)}.")

    for group_id, group_items in groups.items():
        conditions = {item.get("metadata_condition") for item in group_items}
        if len(group_items) != 3 or conditions != REQUIRED_CONDITIONS:
            v.fail(f"Release group {group_id} has {len(group_items)} items and conditions {sorted(conditions)}.")
        else:
            v.pass_(f"Release group {group_id} has the three required metadata conditions.")

    for item in items:
        ref = item.get("reference_answer", {})
        for key in [
            "technical_soundness",
            "evidence_support",
            "novelty",
            "significance",
            "clarity",
            "overall_merit",
            "editorial_priority",
        ]:
            value = ref.get(key)
            if isinstance(value, str) and value.startswith("TBD"):
                v.fail(f"{item.get('item_id')} release reference field {key} is still TBD.")
            if value is None:
                v.fail(f"{item.get('item_id')} release reference field {key} is missing.")
        materials = item.get("source_materials", {})
        for key in ["methods_excerpt", "results_excerpt"]:
            value = materials.get(key)
            if not value or (isinstance(value, str) and value.startswith("TBD")):
                v.fail(f"{item.get('item_id')} release source_materials.{key} is incomplete.")
        if "demo_llm_reference_answer" in item:
            v.fail(f"{item.get('item_id')} contains demo_llm_reference_answer, which is not part of v1.")
    v.pass_("Release reference labels and methods/results summaries are populated.")


def validate_reference_labels(v: Validation) -> None:
    labels = load_csv(REFERENCE_LABELS)
    raw = load_csv(RAW_REFERENCE_LABELS)
    if labels.empty:
        v.fail("Reference labels file is empty or missing.")
        return
    missing = EXPECTED_REFERENCE_COLUMNS - set(labels.columns)
    if missing:
        v.fail(f"Reference labels missing columns: {sorted(missing)}")
    elif set(labels["paper_group_id"]) == EXPECTED_GROUPS and len(labels) == 5:
        v.pass_("Reference labels contain the expected five paper groups and required columns.")
    else:
        v.fail("Reference labels do not contain exactly the expected five paper groups.")
    if len(raw) == 15:
        v.pass_("Raw reference labels contain 15 reviewer rows.")
    else:
        v.fail(f"Raw reference labels contain {len(raw)} rows, expected 15.")


def validate_pdf_manifest(v: Validation) -> None:
    manifest = load_csv(PDF_MANIFEST)
    if manifest.empty:
        v.fail("PDF manifest is empty or missing.")
        return
    missing = EXPECTED_PDF_MANIFEST_COLUMNS - set(manifest.columns)
    if missing:
        v.fail(f"PDF manifest missing columns: {sorted(missing)}")
        return
    if len(manifest) == 10:
        v.pass_("PDF manifest contains 10 records.")
    else:
        v.fail(f"PDF manifest contains {len(manifest)} records, expected 10.")
    for group_id, group in manifest.groupby("paper_group_id"):
        conditions = set(group["pdf_condition"])
        if conditions == REQUIRED_PDF_CONDITIONS:
            v.pass_(f"PDF manifest group {group_id} has original and redacted PDF records.")
        else:
            v.fail(f"PDF manifest group {group_id} has conditions {sorted(conditions)}.")
    redacted = manifest[manifest["pdf_condition"] == "redacted_pdf"]
    for _, row in redacted.iterrows():
        if str(row["source_arxiv_id"]) in str(row["filename"]):
            v.fail(f"Redacted PDF filename contains arXiv id: {row['filename']}")


def validate_no_api_keys(v: Validation) -> None:
    scanned = 0
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", "__pycache__", ".pycache"} for part in path.parts):
            continue
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        if API_KEY_PATTERN.search(text):
            v.fail(f"Possible API key detected in {path.relative_to(PROJECT_ROOT)}.")
    if scanned:
        v.pass_(f"Scanned {scanned} text files for API-key-like secrets.")


def main() -> None:
    v = Validation()
    pool = load_csv(RAW_CSV)
    screening = load_csv(SCREENING_CSV)

    validate_pool(v, pool)
    validate_screening(v, pool, screening)
    items = validate_pilot_files(v)
    validate_pilot_items(v, screening, items)
    release_items = validate_release_files(v)
    validate_release_items(v, release_items)
    validate_reference_labels(v)
    validate_pdf_manifest(v)
    validate_no_api_keys(v)

    print("")
    print("Validation summary")
    print(f"- Errors: {len(v.errors)}")
    print(f"- Warnings: {len(v.warnings)}")
    print(f"- Candidate records: {len(pool)}")
    print(f"- Screening records: {len(screening)}")
    print(f"- Pilot items: {len(items)}")
    print(f"- Release items: {len(release_items)}")

    if v.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
