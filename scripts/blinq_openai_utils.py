"""Shared helpers for BLINQ OpenAI PDF evaluation scripts."""

from __future__ import annotations

import base64
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_JSONL = PROJECT_ROOT / "data" / "release" / "blinq_v1_items.jsonl"
PDF_MANIFEST = PROJECT_ROOT / "data" / "release" / "pdf_manifest_v1.csv"
RESULTS_DIR = PROJECT_ROOT / "results"

API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_pdf_manifest(path: Path = PDF_MANIFEST) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"PDF manifest not found: {path}")
    text = path.read_text(encoding="utf-8")
    if API_KEY_PATTERN.search(text):
        raise ValueError(f"Possible API key found in manifest: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_release_items(path: Path = RELEASE_JSONL) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Release dataset not found: {path}")
    return load_jsonl(path)


def require_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(f"{env_name} is not set. Export it in your shell before running API evaluation.")
    return api_key


def pdf_record_for(manifest: list[dict[str, str]], paper_group_id: str, pdf_condition: str) -> dict[str, str]:
    normalized = "redacted_pdf" if pdf_condition == "redacted_pdf_plus_synthetic_metadata" else pdf_condition
    for row in manifest:
        if row["paper_group_id"] == paper_group_id and row["pdf_condition"] == normalized:
            return row
    raise KeyError(f"No PDF manifest row for {paper_group_id} / {pdf_condition}")


def pdf_path_from_record(record: dict[str, str]) -> Path:
    return Path(record["expected_local_path"])


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


def parse_json_response(text: str) -> dict[str, Any]:
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


def call_openai_pdf_response(
    *,
    model: str,
    api_key: str,
    prompt: str,
    pdf_path: Path,
    schema_name: str,
    schema: dict[str, Any],
    timeout_seconds: int = 600,
    max_retries: int = 3,
    retry_sleep_seconds: int = 15,
) -> dict[str, Any]:
    pdf_bytes = pdf_path.read_bytes()
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    payload = {
        "model": model,
        "instructions": (
            "You are evaluating a benchmark item. Return only valid JSON matching the requested schema. "
            "Do not browse the web, do not use external tools, and do not include Markdown fences."
        ),
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_file",
                        "filename": pdf_path.name,
                        "file_data": f"data:application/pdf;base64,{encoded}",
                    },
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    }
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
            if response.status_code in {408, 409, 429} or response.status_code >= 500:
                last_error = RuntimeError(
                    f"retryable OpenAI API status {response.status_code}: {response.text[:500]}"
                )
                if attempt < max_retries:
                    print(
                        f"Retryable OpenAI error for model={model} pdf={pdf_path.name} "
                        f"attempt={attempt}/{max_retries}; sleeping {retry_sleep_seconds}s"
                    )
                    time.sleep(retry_sleep_seconds)
                    continue
            response.raise_for_status()
            return parse_json_response(extract_response_text(response.json()))
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries:
                print(
                    f"Transient OpenAI connection error for model={model} pdf={pdf_path.name} "
                    f"attempt={attempt}/{max_retries}: {exc}; sleeping {retry_sleep_seconds}s"
                )
                time.sleep(retry_sleep_seconds)
                continue
            raise RuntimeError(
                f"OpenAI API request failed after {max_retries} attempts for model={model}, pdf={pdf_path.name}: {exc}"
            ) from exc
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI API request failed for model {model}: HTTP {response.status_code} {response.text}"
            ) from exc

    raise RuntimeError(
        f"OpenAI API request failed after {max_retries} attempts for model={model}, pdf={pdf_path.name}: {last_error}"
    )
