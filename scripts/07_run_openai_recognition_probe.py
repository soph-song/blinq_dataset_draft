#!/usr/bin/env python3
"""Run OpenAI recognition/contamination probes on redacted BLINQ PDFs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from blinq_openai_utils import (
    RESULTS_DIR,
    append_jsonl,
    call_openai_pdf_response,
    load_jsonl,
    load_pdf_manifest,
    load_release_items,
    pdf_path_from_record,
    pdf_record_for,
    require_api_key,
)


OUTPUT_PATH = RESULTS_DIR / "recognition" / "openai_recognition_outputs.jsonl"


def recognition_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "paper_group_id",
            "recognition_status",
            "paper_familiarity_confidence",
            "predicted_authors_or_groups",
            "predicted_affiliations",
            "affiliation_identification_confidence",
            "basis_for_recognition",
            "recognition_rationale",
        ],
        "properties": {
            "paper_group_id": {"type": "string"},
            "recognition_status": {"type": "string", "enum": ["recognized", "possibly_recognized", "not_recognized"]},
            "paper_familiarity_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "predicted_authors_or_groups": {"type": "array", "items": {"type": "string"}},
            "predicted_affiliations": {"type": "array", "items": {"type": "string"}},
            "affiliation_identification_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "basis_for_recognition": {"type": "string", "enum": ["memory", "guess", "text_evidence", "none"]},
            "recognition_rationale": {"type": "string"},
        },
    }


def build_prompt(item: dict[str, Any]) -> str:
    return f"""You are participating in a contamination/recognition probe for BLINQ, a benchmark about blinded quantum information science manuscript review.

You will receive a redacted PDF. Do not browse the web and do not use external tools.

Task:
1. State whether you recognize the underlying paper from memory.
2. State whether you can identify possible authors, research groups, labs, institutions, or affiliations.
3. Give confidence values from 0 to 1.
4. Distinguish memory from guesswork or text evidence.

Synthetic benchmark paper id: {item["paper_group_id"]}
Subfield: {item["subfield"]}

Return only JSON matching the schema.
"""


def first_blinded_items() -> list[dict[str, Any]]:
    items = load_release_items()
    return [item for item in items if item["metadata_condition"] == "blinded"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-sleep-seconds", type=int, default=20)
    parser.add_argument("--restart", action="store_true", help="Delete existing output and start from scratch.")
    args = parser.parse_args()

    api_key = require_api_key(args.api_key_env)
    manifest = load_pdf_manifest()
    items = first_blinded_items()
    if args.limit:
        items = items[: args.limit]

    if args.restart and args.output.exists():
        args.output.unlink()

    existing_rows = load_jsonl(args.output)
    completed = {(row.get("model"), row.get("paper_group_id")) for row in existing_rows}
    if existing_rows:
        print(f"Resuming from {args.output}; found {len(existing_rows)} completed recognition rows.")

    new_rows = 0
    for model in args.models:
        for item in items:
            key = (model, item["paper_group_id"])
            if key in completed:
                print(f"Skipping completed recognition probe: model={model} paper_group_id={item['paper_group_id']}")
                continue
            record = pdf_record_for(manifest, item["paper_group_id"], "redacted_pdf")
            pdf_path = pdf_path_from_record(record)
            print(f"Recognition probe: model={model} paper_group_id={item['paper_group_id']} pdf={pdf_path.name}")
            response = call_openai_pdf_response(
                model=model,
                api_key=api_key,
                prompt=build_prompt(item),
                pdf_path=pdf_path,
                schema_name="blinq_model_recognition_probe",
                schema=recognition_schema(),
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            append_jsonl(
                args.output,
                {
                    "model": model,
                    "paper_group_id": item["paper_group_id"],
                    "pdf_condition": "redacted_pdf",
                    "pdf_sha256": record.get("sha256", ""),
                    "response": response,
                },
            )
            completed.add(key)
            new_rows += 1

    total_rows = len(load_jsonl(args.output))
    print(f"Wrote {new_rows} new recognition outputs to {args.output}")
    print(f"Total recognition outputs now: {total_rows}")


if __name__ == "__main__":
    main()
