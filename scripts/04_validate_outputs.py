#!/usr/bin/env python3
"""Validate BLINQ dataset-draft outputs."""

from __future__ import annotations

import json
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

TARGET_POOL_SIZE = 1000
SCREEN_SAMPLE_SIZE = 100
REQUIRED_CONDITIONS = {"blinded", "real_metadata", "counterfactual_high_prestige"}
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


def main() -> None:
    v = Validation()
    pool = load_csv(RAW_CSV)
    screening = load_csv(SCREENING_CSV)

    validate_pool(v, pool)
    validate_screening(v, pool, screening)
    items = validate_pilot_files(v)
    validate_pilot_items(v, screening, items)

    print("")
    print("Validation summary")
    print(f"- Errors: {len(v.errors)}")
    print(f"- Warnings: {len(v.warnings)}")
    print(f"- Candidate records: {len(pool)}")
    print(f"- Screening records: {len(screening)}")
    print(f"- Pilot items: {len(items)}")

    if v.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
