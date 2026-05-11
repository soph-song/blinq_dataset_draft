#!/usr/bin/env python3
"""Prepare or merge demo LLM reference labels for BLINQ pilot items.

This script keeps demo LLM labels separate from the future human reference
labels. It never overwrites `reference_answer`; instead it writes
`demo_llm_reference_answer` into a separate output JSONL/CSV.

Default mode writes one blinded labeling prompt per paper group. Optional modes:

- `--responses-input`: merge externally generated LLM JSON responses.
- `--labeler-command`: call a local/external command once per prompt. The command
  must read the prompt from stdin and print one JSON object to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_JSONL = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15.jsonl"
PROMPTS_OUT = PROJECT_ROOT / "data" / "pilot" / "demo_llm_reference_label_prompts.jsonl"
RESPONSES_TEMPLATE_OUT = PROJECT_ROOT / "data" / "pilot" / "demo_llm_reference_label_responses_template.jsonl"
LABELED_JSONL_OUT = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15_with_demo_llm_labels.jsonl"
LABELED_CSV_OUT = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15_with_demo_llm_labels.csv"

SCORE_FIELDS = [
    "technical_soundness",
    "evidence_support",
    "novelty",
    "significance",
    "clarity",
    "overall_merit",
]
PRIORITIES = {"high", "medium", "low"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def flatten_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    df = pd.json_normalize(rows)
    for column in df.columns:
        df[column] = df[column].map(
            lambda value: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list))
            else value
        )
    df.to_csv(path, index=False)


def first_blinded_item_by_group(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in items:
        if item.get("metadata_condition") == "blinded":
            groups[item["paper_group_id"]] = item
    return dict(sorted(groups.items()))


def usable_excerpt(value: str | None) -> str:
    if not value or value.startswith("TBD"):
        return ""
    return value


def build_prompt(item: dict[str, Any]) -> str:
    materials = item["source_materials"]
    methods = usable_excerpt(materials.get("methods_excerpt"))
    results = usable_excerpt(materials.get("results_excerpt"))

    optional_sections = ""
    if methods:
        optional_sections += f"\nMethods excerpt:\n{methods}\n"
    if results:
        optional_sections += f"\nResults excerpt:\n{results}\n"

    return f"""You are creating a DEMO LLM reference label for a quantum information science manuscript-review benchmark.

Important constraints:
- Use only the blinded scientific content below.
- Do not infer quality from authors, institutions, venue, arXiv id, or prestige.
- This is not a human expert label; mark uncertainty in the confidence value.
- Judge from title and abstract only unless excerpts are provided.

Rubric:
- technical_soundness: 1 weak/unsupported, 3 plausible with gaps, 5 technically robust from supplied content.
- evidence_support: 1 little support, 3 partial support, 5 strong direct support.
- novelty: 1 incremental/unclear, 3 somewhat new, 5 clearly original/nontrivial.
- significance: 1 limited/unclear impact, 3 useful but bounded, 5 likely important for QIS.
- clarity: 1 hard to evaluate, 3 mostly understandable with gaps, 5 clear and well structured.
- overall_merit: 1 weak, 3 mixed/promising, 5 strong.
- editorial_priority: high, medium, or low.

Paper group: {item["paper_group_id"]}
Subfield: {item.get("subfield", "")}
Paper type: {item.get("paper_type", "")}

Title:
{materials.get("title", "")}

Abstract:
{materials.get("abstract", "")}
{optional_sections}
Return exactly one JSON object with this schema:
{{
  "paper_group_id": "{item["paper_group_id"]}",
  "technical_soundness": 1,
  "evidence_support": 1,
  "novelty": 1,
  "significance": 1,
  "clarity": 1,
  "overall_merit": 1,
  "editorial_priority": "low",
  "confidence": 0.0,
  "rationale": "2-4 concise sentences grounded only in the supplied content.",
  "evidence_spans_or_phrases": ["short phrase from title or abstract"]
}}
"""


def build_prompt_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for group_id, item in first_blinded_item_by_group(items).items():
        rows.append(
            {
                "paper_group_id": group_id,
                "source_item_id": item["item_id"],
                "source_arxiv_id": item["source_arxiv_id"],
                "subfield": item["subfield"],
                "labeling_condition": "blinded",
                "prompt": build_prompt(item),
            }
        )
    return rows


def build_response_template(prompt_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "paper_group_id": row["paper_group_id"],
            "llm_reference_answer": {
                "technical_soundness": "TBD_llm_demo",
                "evidence_support": "TBD_llm_demo",
                "novelty": "TBD_llm_demo",
                "significance": "TBD_llm_demo",
                "clarity": "TBD_llm_demo",
                "overall_merit": "TBD_llm_demo",
                "editorial_priority": "TBD_llm_demo",
                "confidence": "TBD_llm_demo",
                "rationale": "TBD_llm_demo",
                "evidence_spans_or_phrases": [],
            },
        }
        for row in prompt_rows
    ]


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_label(raw: dict[str, Any], expected_group_id: str | None = None) -> dict[str, Any]:
    label = raw.get("llm_reference_answer", raw)
    if "response_text" in raw:
        label = extract_json_object(str(raw["response_text"]))
    if "response_json" in raw:
        label = raw["response_json"]

    group_id = label.get("paper_group_id") or raw.get("paper_group_id") or expected_group_id
    if expected_group_id and group_id != expected_group_id:
        raise ValueError(f"Response group id {group_id!r} does not match expected {expected_group_id!r}")

    normalized: dict[str, Any] = {}
    for field in SCORE_FIELDS:
        value = label.get(field)
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{group_id}: {field} must be an integer from 1 to 5, got {value!r}")
        normalized[field] = value

    priority = str(label.get("editorial_priority", "")).lower()
    if priority not in PRIORITIES:
        raise ValueError(f"{group_id}: editorial_priority must be one of {sorted(PRIORITIES)}, got {priority!r}")
    normalized["editorial_priority"] = priority

    confidence = label.get("confidence", label.get("annotator_confidence", 0.0))
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise ValueError(f"{group_id}: confidence must be a number from 0 to 1, got {confidence!r}")
    normalized["annotator_confidence"] = float(confidence)

    rationale = str(label.get("rationale", "")).strip()
    if not rationale:
        raise ValueError(f"{group_id}: rationale is required")
    normalized["rationale"] = rationale

    spans = label.get("evidence_spans_or_phrases", [])
    if not isinstance(spans, list):
        raise ValueError(f"{group_id}: evidence_spans_or_phrases must be a list")
    normalized["evidence_spans_or_phrases"] = [str(span) for span in spans]

    normalized["label_status"] = "demo_llm_generated_not_human_expert"
    normalized["labeling_condition"] = "blinded"
    normalized["label_note"] = (
        "Demo LLM label generated from blinded title/abstract packet; not a completed human expert label."
    )
    return normalized


def run_labeler_command(command: str, prompt_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    argv = shlex.split(command)
    for row in prompt_rows:
        group_id = row["paper_group_id"]
        print(f"Running labeler command for {group_id}...")
        result = subprocess.run(
            argv,
            input=row["prompt"],
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Labeler command failed for {group_id} with exit code {result.returncode}:\n{result.stderr}"
            )
        parsed = extract_json_object(result.stdout)
        labels[group_id] = normalize_label(parsed, expected_group_id=group_id)
    return labels


def label_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "paper_group_id",
            "technical_soundness",
            "evidence_support",
            "novelty",
            "significance",
            "clarity",
            "overall_merit",
            "editorial_priority",
            "confidence",
            "rationale",
            "evidence_spans_or_phrases",
        ],
        "properties": {
            "paper_group_id": {"type": "string"},
            "technical_soundness": {"type": "integer", "minimum": 1, "maximum": 5},
            "evidence_support": {"type": "integer", "minimum": 1, "maximum": 5},
            "novelty": {"type": "integer", "minimum": 1, "maximum": 5},
            "significance": {"type": "integer", "minimum": 1, "maximum": 5},
            "clarity": {"type": "integer", "minimum": 1, "maximum": 5},
            "overall_merit": {"type": "integer", "minimum": 1, "maximum": 5},
            "editorial_priority": {"type": "string", "enum": ["high", "medium", "low"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "evidence_spans_or_phrases": {"type": "array", "items": {"type": "string"}},
        },
    }


def extract_response_text(response_json: dict[str, Any]) -> str:
    if isinstance(response_json.get("output_text"), str):
        return response_json["output_text"]

    chunks: list[str] = []
    for output_item in response_json.get("output", []):
        for content in output_item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text", "")))
    if chunks:
        return "\n".join(chunks)
    raise ValueError(f"Could not find output text in OpenAI response: {response_json}")


def call_openai_response(prompt: str, model: str, api_key: str) -> dict[str, Any]:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "instructions": (
                "Return only valid JSON matching the requested schema. "
                "Do not include Markdown fences or extra commentary."
            ),
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "blinq_demo_llm_reference_label",
                    "strict": True,
                    "schema": label_schema(),
                }
            },
        },
        timeout=180,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"OpenAI API request failed: {response.status_code} {response.text}") from exc
    return extract_json_object(extract_response_text(response.json()))


def run_openai_labeler(prompt_rows: list[dict[str, Any]], model: str, api_key_env: str) -> dict[str, dict[str, Any]]:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"{api_key_env} is not set. Run: export {api_key_env}=\"your_api_key_here\""
        )

    labels: dict[str, dict[str, Any]] = {}
    for row in prompt_rows:
        group_id = row["paper_group_id"]
        print(f"Calling OpenAI model {model} for {group_id}...")
        parsed = call_openai_response(row["prompt"], model=model, api_key=api_key)
        labels[group_id] = normalize_label(parsed, expected_group_id=group_id)
    return labels


def load_response_labels(path: Path) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        group_id = row.get("paper_group_id")
        label = normalize_label(row, expected_group_id=group_id)
        labels[str(group_id)] = label
    return labels


def attach_labels(items: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    labeled_items = []
    for item in items:
        copy = json.loads(json.dumps(item))
        group_id = copy["paper_group_id"]
        if group_id in labels:
            copy["demo_llm_reference_answer"] = labels[group_id]
        labeled_items.append(copy)
    return labeled_items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PILOT_JSONL)
    parser.add_argument("--prompts-output", type=Path, default=PROMPTS_OUT)
    parser.add_argument("--responses-template-output", type=Path, default=RESPONSES_TEMPLATE_OUT)
    parser.add_argument("--responses-input", type=Path)
    parser.add_argument("--labeler-command", help="Local command that reads prompt from stdin and returns JSON.")
    parser.add_argument(
        "--openai-model",
        help="Call the OpenAI Responses API with this model, e.g. gpt-5.5. Reads API key from OPENAI_API_KEY.",
    )
    parser.add_argument("--openai-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--labeled-jsonl-output", type=Path, default=LABELED_JSONL_OUT)
    parser.add_argument("--labeled-csv-output", type=Path, default=LABELED_CSV_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    items = load_jsonl(args.input)
    prompt_rows = build_prompt_rows(items)
    write_jsonl(args.prompts_output, prompt_rows)
    write_jsonl(args.responses_template_output, build_response_template(prompt_rows))
    print(f"Wrote {len(prompt_rows)} blinded LLM-label prompts to {args.prompts_output}")
    print(f"Wrote response template to {args.responses_template_output}")

    labels: dict[str, dict[str, Any]] = {}
    if args.responses_input:
        labels.update(load_response_labels(args.responses_input))
    if args.labeler_command:
        labels.update(run_labeler_command(args.labeler_command, prompt_rows))
    if args.openai_model:
        labels.update(run_openai_labeler(prompt_rows, args.openai_model, args.openai_api_key_env))

    if labels:
        labeled_items = attach_labels(items, labels)
        write_jsonl(args.labeled_jsonl_output, labeled_items)
        flatten_to_csv(args.labeled_csv_output, labeled_items)
        print(f"Attached demo LLM labels for {len(labels)} paper groups.")
        print(f"Wrote {args.labeled_jsonl_output}")
        print(f"Wrote {args.labeled_csv_output}")
    else:
        print("No labels were merged. Use --responses-input or --labeler-command to create labeled demo files.")


if __name__ == "__main__":
    main()
