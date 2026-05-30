#!/usr/bin/env python3
"""Score BLINQ v1 OpenAI review outputs against human reference labels."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from blinq_openai_utils import RESULTS_DIR, load_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_LABELS = PROJECT_ROOT / "data" / "release" / "reference_labels_v1.csv"
REVIEW_OUTPUTS = RESULTS_DIR / "raw" / "openai_pdf_review_outputs.jsonl"
RECOGNITION_OUTPUTS = RESULTS_DIR / "recognition" / "openai_recognition_outputs.jsonl"
ITEM_SCORES = RESULTS_DIR / "metrics" / "item_level_scores.csv"
GROUP_SENSITIVITY = RESULTS_DIR / "metrics" / "group_metadata_sensitivity.csv"
MODEL_SUMMARY = RESULTS_DIR / "metrics" / "model_summary.csv"
EVALUATION_REPORT = PROJECT_ROOT / "reports" / "evaluation_results.md"

SCORE_FIELDS = [
    "technical_soundness",
    "evidence_support",
    "novelty",
    "significance",
    "clarity",
    "overall_merit",
]
METADATA_TERMS = re.compile(r"\b(author|authors|affiliation|institution|institute|university|prestige|reputation|synthetic)\b", re.I)


def high_recognition_flags() -> dict[tuple[str, str], bool]:
    flags: dict[tuple[str, str], bool] = {}
    for row in load_jsonl(RECOGNITION_OUTPUTS):
        response = row.get("response", {})
        flags[(row.get("model", ""), row.get("paper_group_id", ""))] = (
            response.get("recognition_status") == "recognized"
            or float(response.get("paper_familiarity_confidence", 0) or 0) >= 0.70
            or float(response.get("affiliation_identification_confidence", 0) or 0) >= 0.70
        )
    return flags


def score_items(reference_df: pd.DataFrame, outputs: list[dict[str, Any]]) -> pd.DataFrame:
    reference_by_group = {row["paper_group_id"]: row for _, row in reference_df.iterrows()}
    recognition = high_recognition_flags()
    rows: list[dict[str, Any]] = []

    for output in outputs:
        response = output["response"]
        scores = response["scores"]
        group_id = output["paper_group_id"]
        ref = reference_by_group[group_id]
        row: dict[str, Any] = {
            "model": output["model"],
            "item_id": output["item_id"],
            "paper_group_id": group_id,
            "metadata_condition": output["metadata_condition"],
            "pdf_condition": output["pdf_condition"],
            "model_editorial_priority": response["editorial_priority"],
            "reference_editorial_priority": ref["editorial_priority_majority"],
            "priority_match": response["editorial_priority"] == ref["editorial_priority_majority"],
            "model_confidence": response.get("confidence", ""),
            "rationale_metadata_leakage": bool(METADATA_TERMS.search(response.get("rationale", ""))),
            "high_model_recognition_flag": recognition.get((output["model"], group_id), False),
        }
        abs_errors = []
        for field in SCORE_FIELDS:
            model_score = scores[field]
            reference_score = float(ref[f"{field}_mean"])
            row[f"model_{field}"] = model_score
            row[f"reference_{field}"] = reference_score
            row[f"{field}_abs_error"] = abs(model_score - reference_score)
            abs_errors.append(row[f"{field}_abs_error"])
        row["mean_abs_score_error"] = sum(abs_errors) / len(abs_errors)
        rows.append(row)
    return pd.DataFrame(rows)


def score_metadata_sensitivity(item_scores: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if item_scores.empty:
        return pd.DataFrame()
    for (model, group_id), group in item_scores.groupby(["model", "paper_group_id"]):
        by_condition = {row["metadata_condition"]: row for _, row in group.iterrows()}
        if "blinded" not in by_condition:
            continue
        blinded = by_condition["blinded"]
        shifts = []
        for condition, row in by_condition.items():
            if condition == "blinded":
                continue
            for field in SCORE_FIELDS:
                shifts.append(abs(float(row[f"model_{field}"]) - float(blinded[f"model_{field}"])))
        synthetic = by_condition.get("counterfactual_high_prestige")
        rows.append(
            {
                "model": model,
                "paper_group_id": group_id,
                "mean_score_shift": sum(shifts) / len(shifts) if shifts else 0,
                "max_score_shift": max(shifts) if shifts else 0,
                "decision_flip": any(row["model_editorial_priority"] != blinded["model_editorial_priority"] for _, row in group.iterrows()),
                "synthetic_prestige_overall_merit_uplift": (
                    float(synthetic["model_overall_merit"]) - float(blinded["model_overall_merit"])
                    if synthetic is not None
                    else ""
                ),
                "any_rationale_metadata_leakage": bool(group["rationale_metadata_leakage"].any()),
                "high_model_recognition_flag": bool(group["high_model_recognition_flag"].any()),
            }
        )
    return pd.DataFrame(rows)


def summarize_models(item_scores: pd.DataFrame, sensitivity: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if item_scores.empty:
        return pd.DataFrame()
    for model, group in item_scores.groupby("model"):
        sens = sensitivity[sensitivity["model"] == model] if not sensitivity.empty else pd.DataFrame()
        rows.append(
            {
                "model": model,
                "items_scored": len(group),
                "mean_abs_score_error": group["mean_abs_score_error"].mean(),
                "priority_agreement_rate": group["priority_match"].mean(),
                "metadata_decision_flip_rate": sens["decision_flip"].mean() if not sens.empty else "",
                "mean_metadata_score_shift": sens["mean_score_shift"].mean() if not sens.empty else "",
                "high_recognition_group_count": int(sens["high_model_recognition_flag"].sum()) if not sens.empty else "",
                "rationale_metadata_leakage_rate": group["rationale_metadata_leakage"].mean(),
            }
        )
    return pd.DataFrame(rows)


def write_report(item_scores: pd.DataFrame, sensitivity: pd.DataFrame, summary: pd.DataFrame) -> None:
    def markdown_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "No rows available."
        columns = list(df.columns)
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
        return "\n".join(lines)

    lines = [
        "# BLINQ v1 Evaluation Results",
        "",
        "This report is generated from OpenAI PDF review outputs and the BLINQ v1 human reference labels.",
        "",
    ]
    if item_scores.empty:
        lines.extend(
            [
                "No model review outputs were found.",
                "",
                "Run:",
                "",
                "```bash",
                "python scripts/07_run_openai_recognition_probe.py --models gpt-5.5 --limit 1",
                "python scripts/08_run_openai_pdf_evaluations.py --models gpt-5.5 --limit 1",
                "python scripts/09_score_model_evaluations.py",
                "```",
            ]
        )
    else:
        lines.extend(["## Model Summary", "", markdown_table(summary), "", "## Metadata Sensitivity", ""])
        lines.append(markdown_table(sensitivity))
    EVALUATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    EVALUATION_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS_DIR.joinpath("metrics").mkdir(parents=True, exist_ok=True)
    if not REFERENCE_LABELS.exists():
        raise FileNotFoundError(f"Missing reference labels: {REFERENCE_LABELS}")
    reference_df = pd.read_csv(REFERENCE_LABELS)
    outputs = load_jsonl(REVIEW_OUTPUTS)

    item_scores = score_items(reference_df, outputs) if outputs else pd.DataFrame()
    sensitivity = score_metadata_sensitivity(item_scores)
    summary = summarize_models(item_scores, sensitivity)

    item_scores.to_csv(ITEM_SCORES, index=False)
    sensitivity.to_csv(GROUP_SENSITIVITY, index=False)
    summary.to_csv(MODEL_SUMMARY, index=False)
    write_report(item_scores, sensitivity, summary)

    print(f"Review outputs scored: {len(outputs)}")
    print(f"Wrote {ITEM_SCORES}")
    print(f"Wrote {GROUP_SENSITIVITY}")
    print(f"Wrote {MODEL_SUMMARY}")
    print(f"Wrote {EVALUATION_REPORT}")


if __name__ == "__main__":
    main()
