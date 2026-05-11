#!/usr/bin/env python3
"""Collect a reproducible arXiv quant-ph candidate pool for BLINQ.

This script uses the official arXiv API endpoint and stores metadata only.
It intentionally avoids downloading PDFs or scraping arXiv HTML pages.
"""

from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd
import requests
from dateutil.parser import parse as parse_date


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_CSV = RAW_DIR / "quant_ph_candidate_pool_1000.csv"
SUMMARY_MD = REPORTS_DIR / "dataset_draft_summary.md"

ARXIV_API_URL = "https://export.arxiv.org/api/query"
RANDOM_SEED = 209
TARGET_POOL_SIZE = 1000
YEARS = list(range(2018, 2027))
FETCH_PER_YEAR = 150
API_DELAY_SECONDS = 3.2

OUTPUT_COLUMNS = [
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
]


def normalize_whitespace(text: str | None) -> str:
    """Collapse arXiv feed whitespace into readable single-line text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_arxiv_id(entry_id: str) -> str:
    """Return the base arXiv id without an arXiv version suffix."""
    raw_id = entry_id.rsplit("/abs/", 1)[-1].strip()
    return re.sub(r"v\d+$", "", raw_id)


def parse_feed_date(value: str | None) -> str:
    """Convert feed date strings to ISO-8601 when possible."""
    if not value:
        return ""
    try:
        return parse_date(value).isoformat()
    except (TypeError, ValueError):
        return str(value)


def extract_categories(entry: Any) -> tuple[str, list[str]]:
    tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
    primary = ""
    primary_obj = entry.get("arxiv_primary_category")
    if isinstance(primary_obj, dict):
        primary = primary_obj.get("term", "")
    if not primary and tags:
        primary = tags[0]
    return primary, tags


def extract_pdf_url(entry: Any, arxiv_id: str) -> str:
    for link in entry.get("links", []):
        if link.get("title") == "pdf" or link.get("type") == "application/pdf":
            return link.get("href", "")
    return f"https://arxiv.org/pdf/{arxiv_id}"


def entry_to_record(entry: Any, collection_query: str, collection_year: int) -> dict[str, Any]:
    arxiv_id = normalize_arxiv_id(entry.get("id", ""))
    primary_category, all_categories = extract_categories(entry)
    authors = [
        normalize_whitespace(author.get("name", ""))
        for author in entry.get("authors", [])
        if author.get("name")
    ]

    return {
        "arxiv_id": arxiv_id,
        "title": normalize_whitespace(entry.get("title", "")),
        "abstract": normalize_whitespace(entry.get("summary", "")),
        "authors": json.dumps(authors, ensure_ascii=False),
        "published": parse_feed_date(entry.get("published", "")),
        "updated": parse_feed_date(entry.get("updated", "")),
        "primary_category": primary_category,
        "all_categories": json.dumps(all_categories, ensure_ascii=False),
        "comments": normalize_whitespace(entry.get("arxiv_comment", "")),
        "journal_ref": normalize_whitespace(entry.get("arxiv_journal_ref", "")),
        "doi": normalize_whitespace(entry.get("arxiv_doi", "")),
        "abstract_url": entry.get("id", f"https://arxiv.org/abs/{arxiv_id}"),
        "pdf_url": extract_pdf_url(entry, arxiv_id),
        "collection_query": collection_query,
        "collection_year": collection_year,
    }


def fetch_year(year: int) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch one year-stratified arXiv page for quant-ph."""
    collection_query = f"cat:quant-ph AND submittedDate:[{year}01010000 TO {year}12312359]"
    params = {
        "search_query": collection_query,
        "start": 0,
        "max_results": FETCH_PER_YEAR,
        "sortBy": "submittedDate",
        "sortOrder": "ascending",
    }
    headers = {"User-Agent": "BLINQ dataset draft pipeline (educational benchmark)"}

    print(f"Fetching {year}: {collection_query}")
    try:
        response = requests.get(ARXIV_API_URL, params=params, headers=headers, timeout=45)
        response.raise_for_status()
    except requests.RequestException as exc:
        return [], f"{year}: API request failed: {exc}"

    feed = feedparser.parse(response.text)
    if getattr(feed, "bozo", False):
        print(f"Warning: feedparser reported a parse issue for {year}: {feed.bozo_exception}")

    records = [entry_to_record(entry, collection_query, year) for entry in feed.entries]
    print(f"  collected {len(records)} feed entries for {year}")
    return records, None


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by base arXiv id while preserving first-seen records."""
    seen: dict[str, dict[str, Any]] = {}
    for record in records:
        arxiv_id = record.get("arxiv_id", "")
        if arxiv_id and arxiv_id not in seen:
            seen[arxiv_id] = record
    return list(seen.values())


def sample_candidate_pool(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sample exactly TARGET_POOL_SIZE records when enough unique records exist."""
    if len(records) <= TARGET_POOL_SIZE:
        return sorted(records, key=lambda item: (item["collection_year"], item["published"], item["arxiv_id"]))

    rng = random.Random(RANDOM_SEED)
    sampled = rng.sample(records, TARGET_POOL_SIZE)
    return sorted(sampled, key=lambda item: (item["collection_year"], item["published"], item["arxiv_id"]))


def write_collection_report(df: pd.DataFrame, errors: list[str]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    year_counts = df["collection_year"].value_counts().sort_index() if not df.empty else pd.Series(dtype=int)

    lines = [
        "# BLINQ Dataset Draft Summary",
        "",
        "This interim summary was generated by `scripts/01_collect_arxiv_quant_ph.py`.",
        "Later pipeline stages refresh this file with screening and pilot statistics.",
        "",
        "## Collection Status",
        "",
        f"- Target candidate pool size: {TARGET_POOL_SIZE}",
        f"- Number of records collected: {len(df)}",
        f"- Random seed: {RANDOM_SEED}",
        f"- Years requested: {YEARS[0]}-{YEARS[-1]}",
        "",
        "## Year Distribution",
        "",
    ]

    if year_counts.empty:
        lines.append("- No records collected.")
    else:
        for year, count in year_counts.items():
            lines.append(f"- {int(year)}: {int(count)}")

    lines.extend(["", "## API Issues", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- None recorded.")

    if len(df) < TARGET_POOL_SIZE:
        lines.extend(
            [
                "",
                "## Shortfall Notice",
                "",
                (
                    f"Only {len(df)} unique records were saved. This can happen if the arXiv API "
                    "is temporarily unavailable or returns fewer records than requested."
                ),
            ]
        )

    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, year in enumerate(YEARS):
        if idx > 0:
            print(f"Sleeping {API_DELAY_SECONDS:.1f}s to be polite to arXiv...")
            time.sleep(API_DELAY_SECONDS)
        records, error = fetch_year(year)
        all_records.extend(records)
        if error:
            print(f"Warning: {error}")
            errors.append(error)

    unique_records = deduplicate_records(all_records)
    print(f"Unique records after deduplication: {len(unique_records)}")
    candidate_pool = sample_candidate_pool(unique_records)

    df = pd.DataFrame(candidate_pool, columns=OUTPUT_COLUMNS)
    df.to_csv(OUTPUT_CSV, index=False)
    write_collection_report(df, errors)

    print(f"Saved {len(df)} candidate records to {OUTPUT_CSV}")
    if len(df) < TARGET_POOL_SIZE:
        print(f"Warning: expected {TARGET_POOL_SIZE}, saved {len(df)}. See {SUMMARY_MD}")


if __name__ == "__main__":
    main()
