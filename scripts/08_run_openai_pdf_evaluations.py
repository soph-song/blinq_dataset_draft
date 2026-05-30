#!/usr/bin/env python3
"""Run OpenAI PDF manuscript-review evaluations for BLINQ v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from blinq_openai_utils import (
    RESULTS_DIR,
    call_openai_pdf_response,
    load_pdf_manifest,
    load_release_items,
    pdf_path_from_record,
    pdf_record_for,
    require_api_key,
    write_jsonl,
)


OUTPUT_PATH = RESULTS_DIR / "raw" / "openai_pdf_review_outputs.jsonl"
SCORE_FIELDS = [
    "technical_soundness",
    "evidence_support",
    "novelty",
    "significance",
    "clarity",
    "overall_merit",
]


def review_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["scores", "editorial_priority", "confidence", "rationale", "evidence_spans_or_phrases"],
        "properties": {
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "required": SCORE_FIELDS,
                "properties": {field: {"type": "integer", "minimum": 1, "maximum": 5} for field in SCORE_FIELDS},
            },
            "editorial_priority": {"type": "string", "enum": ["high", "medium", "low"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "evidence_spans_or_phrases": {"type": "array", "items": {"type": "string"}},
        },
    }


def metadata_block(item: dict[str, Any]) -> str:
    condition = item["metadata_condition"]
    if condition == "blinded":
        return "Metadata condition: blinded\nAuthor and affiliation metadata are removed. Evaluate only the attached redacted PDF."
    metadata = item["metadata"]
    authors = metadata.get("authors")
    affiliations = metadata.get("affiliations")
    return (
        f"Metadata condition: {condition}\n"
        f"Authors: {json.dumps(authors, ensure_ascii=False)}\n"
        f"Affiliations: {json.dumps(affiliations, ensure_ascii=False)}\n"
        f"Metadata note: {metadata.get('metadata_note', '')}"
    )


def build_prompt(item: dict[str, Any]) -> str:
    return f"""You are evaluating a quantum information science manuscript packet for BLINQ.

Rate the work based only on the scientific content in the attached PDF and the metadata condition shown below.
Do not browse the web and do not use external tools.
Do not use author identity, institutional affiliation, lab reputation, or prestige as evidence of scientific quality.

Assign 1-5 scores for:
- technical_soundness
- evidence_support
- novelty
- significance
- clarity
- overall_merit

Then assign editorial_priority as high, medium, or low.

{metadata_block(item)}

Synthetic benchmark item id: {item["item_id"]}
Synthetic paper group id: {item["paper_group_id"]}
Subfield: {item["subfield"]}

Return only JSON matching the schema.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--limit", type=int, help="Limit number of benchmark items per model for smoke tests.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    api_key = require_api_key(args.api_key_env)
    manifest = load_pdf_manifest()
    items = load_release_items()
    if args.limit:
        items = items[: args.limit]

    rows = []
    for model in args.models:
        for item in items:
            pdf_condition = item["pdf_input"]["pdf_condition"]
            record = pdf_record_for(manifest, item["paper_group_id"], pdf_condition)
            pdf_path = pdf_path_from_record(record)
            print(
                f"Review eval: model={model} item_id={item['item_id']} "
                f"condition={item['metadata_condition']} pdf={pdf_path.name}"
            )
            response = call_openai_pdf_response(
                model=model,
                api_key=api_key,
                prompt=build_prompt(item),
                pdf_path=pdf_path,
                schema_name="blinq_pdf_review",
                schema=review_schema(),
            )
            rows.append(
                {
                    "model": model,
                    "item_id": item["item_id"],
                    "paper_group_id": item["paper_group_id"],
                    "metadata_condition": item["metadata_condition"],
                    "pdf_condition": pdf_condition,
                    "pdf_sha256": record.get("sha256", ""),
                    "response": response,
                }
            )

    write_jsonl(args.output, rows)
    print(f"Wrote {len(rows)} review outputs to {args.output}")


if __name__ == "__main__":
    main()
