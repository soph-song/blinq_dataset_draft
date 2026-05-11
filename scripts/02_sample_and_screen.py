#!/usr/bin/env python3
"""Sample 100 quant-ph candidates and apply a transparent QIS relevance screen."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = PROJECT_ROOT / "data" / "raw" / "quant_ph_candidate_pool_1000.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "screening" / "candidate_screening_100.csv"

RANDOM_SEED = 209
SCREEN_SAMPLE_SIZE = 100

SCREENING_FIELDS = [
    "screen_id",
    "qis_relevance_label",
    "qis_subfield",
    "paper_type",
    "screening_reason",
    "key_qis_terms",
    "selected_for_pilot",
    "recognition_flag",
    "manual_review_needed",
]

IN_SCOPE_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "quantum_error_correction": [
        ("quantum error correction", 5),
        ("quantum error correcting", 5),
        ("error correction", 3),
        ("surface code", 5),
        ("fault tolerance", 4),
        ("fault tolerant", 4),
        ("stabilizer code", 4),
        ("quantum code", 3),
        ("logical qubit", 3),
        ("quantum decoder", 4),
        ("decoding", 2),
        ("syndrome", 3),
    ],
    "quantum_algorithms": [
        ("quantum algorithm", 5),
        ("quantum algorithms", 5),
        ("quantum speedup", 4),
        ("quantum advantage", 4),
        ("hamiltonian simulation", 4),
        ("phase estimation", 4),
        ("amplitude estimation", 4),
        ("quantum walk", 4),
        ("grover", 4),
        ("shor", 4),
        ("variational quantum", 4),
        ("vqe", 3),
        ("qaoa", 3),
        ("bqp", 4),
        ("quantum query", 3),
        ("quantum optimization", 3),
        ("quantum circuit", 3),
    ],
    "quantum_communication_cryptography": [
        ("quantum communication", 5),
        ("quantum cryptography", 5),
        ("quantum key distribution", 5),
        ("qkd", 5),
        ("secure communication", 3),
        ("device independent", 4),
        ("randomness expansion", 4),
        ("randomness generation", 3),
        ("quantum secret sharing", 4),
        ("quantum teleportation", 3),
        ("private quantum", 3),
        ("cryptographic", 3),
    ],
    "quantum_hardware_systems": [
        ("quantum processor", 5),
        ("quantum computer", 4),
        ("quantum computing", 3),
        ("qubit", 3),
        ("qubits", 3),
        ("quantum gate", 4),
        ("gate fidelity", 4),
        ("readout", 3),
        ("control pulse", 3),
        ("superconducting", 3),
        ("trapped ion", 3),
        ("ion trap", 3),
        ("spin qubit", 4),
        ("neutral atom", 3),
        ("photonic qubit", 4),
        ("nisq", 4),
        ("noisy intermediate scale", 4),
    ],
    "quantum_information_theory": [
        ("quantum information", 5),
        ("quantum information theory", 5),
        ("quantum channel", 5),
        ("channel capacity", 4),
        ("quantum capacity", 4),
        ("entanglement as a resource", 5),
        ("resource theory", 5),
        ("quantum resource", 4),
        ("entanglement theory", 4),
        ("mutual information", 3),
        ("von neumann entropy", 3),
        ("quantum entropy", 3),
        ("quantum state discrimination", 4),
        ("quantum tomography", 3),
        ("quantum measurement", 3),
        ("coherence", 2),
    ],
    "quantum_machine_learning": [
        ("quantum machine learning", 5),
        ("quantum neural network", 5),
        ("quantum neural networks", 5),
        ("quantum classifier", 4),
        ("quantum kernel", 4),
        ("quantum generative", 4),
        ("quantum enhanced learning", 4),
        ("learning quantum", 3),
        ("qnn", 3),
    ],
    "quantum_networks": [
        ("quantum network", 5),
        ("quantum networks", 5),
        ("quantum internet", 5),
        ("distributed quantum", 4),
        ("entanglement distribution", 4),
        ("quantum repeater", 5),
        ("network protocol", 3),
        ("network node", 3),
    ],
}

BORDERLINE_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "borderline_foundations": [
        ("bell test", 4),
        ("bell inequality", 4),
        ("nonlocality", 4),
        ("contextuality", 4),
        ("hidden variable", 3),
        ("leggett garg", 3),
        ("quantum foundations", 4),
        ("chsh", 3),
        ("measurement problem", 3),
    ],
    "borderline_many_body": [
        ("many body", 4),
        ("condensed matter", 4),
        ("phase transition", 3),
        ("topological phase", 3),
        ("spin chain", 3),
        ("ising", 3),
        ("hubbard", 3),
        ("thermalization", 3),
        ("tensor network", 3),
        ("entanglement spectrum", 3),
        ("area law", 3),
        ("many body localization", 4),
    ],
}

OUT_OF_SCOPE_KEYWORDS: list[tuple[str, int]] = [
    ("spectroscopy", 4),
    ("molecular", 3),
    ("chemical reaction", 4),
    ("high energy", 3),
    ("black hole", 3),
    ("cosmology", 3),
    ("gravitational", 3),
    ("nuclear", 3),
    ("scattering", 3),
    ("education", 4),
    ("history", 4),
    ("popular", 4),
    ("bose einstein condensate", 3),
]


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = lowered.replace("-", " ").replace("/", " ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def match_terms(text: str, weighted_terms: Iterable[tuple[str, int]]) -> tuple[int, list[str]]:
    score = 0
    matches: list[str] = []
    for term, weight in weighted_terms:
        normalized_term = normalize_text(term)
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])"
        if re.search(pattern, text):
            score += weight
            matches.append(term)
    return score, matches


def choose_paper_type(text: str, subfield: str) -> str:
    if any(term in text for term in ["review", "survey", "overview"]):
        return "review_or_survey"
    if any(term in text for term in ["experiment", "experimental", "demonstration", "demonstrate"]):
        if subfield == "quantum_hardware_systems":
            return "experimental_hardware"
        return "experimental_or_demonstration"
    if any(term in text for term in ["algorithm", "complexity", "bqp", "query"]):
        return "algorithmic_or_complexity"
    if any(term in text for term in ["protocol", "cryptography", "key distribution", "communication"]):
        return "protocol_or_communication"
    if any(term in text for term in ["theorem", "bound", "proof", "capacity"]):
        return "theory"
    if any(term in text for term in ["device", "processor", "qubit", "gate", "readout"]):
        return "hardware_or_systems"
    if "simulation" in text:
        return "simulation_or_methods"
    return "theory_or_methods"


def screen_record(row: pd.Series) -> dict[str, object]:
    title = str(row.get("title", ""))
    abstract = str(row.get("abstract", ""))
    text = normalize_text(f"{title} {abstract}")

    in_scores: dict[str, int] = {}
    in_matches: dict[str, list[str]] = {}
    for subfield, terms in IN_SCOPE_KEYWORDS.items():
        score, matches = match_terms(text, terms)
        in_scores[subfield] = score
        in_matches[subfield] = matches

    borderline_scores: dict[str, int] = {}
    borderline_matches: dict[str, list[str]] = {}
    for subfield, terms in BORDERLINE_KEYWORDS.items():
        score, matches = match_terms(text, terms)
        borderline_scores[subfield] = score
        borderline_matches[subfield] = matches

    out_score, out_matches = match_terms(text, OUT_OF_SCOPE_KEYWORDS)
    top_subfield = max(in_scores, key=in_scores.get)
    top_score = in_scores[top_subfield]
    second_score = sorted(in_scores.values(), reverse=True)[1] if len(in_scores) > 1 else 0
    top_borderline = max(borderline_scores, key=borderline_scores.get)
    top_borderline_score = borderline_scores[top_borderline]

    manual_review_needed = False
    if top_score >= 5 and top_score >= top_borderline_score and out_score < 6:
        label = "in_scope"
        subfield = top_subfield
        if top_score - max(second_score, top_borderline_score) <= 1:
            manual_review_needed = True
    elif top_score >= 3 and top_score > top_borderline_score and out_score < 4:
        label = "in_scope"
        subfield = top_subfield
        manual_review_needed = True
    elif top_borderline_score >= 3 or top_score >= 2:
        label = "borderline"
        subfield = top_borderline if top_borderline_score >= top_score else top_subfield
        manual_review_needed = True
    else:
        label = "out_of_scope"
        subfield = "out_of_scope_other"

    if label == "out_of_scope" and out_score >= 3:
        evidence = out_matches[:4]
    elif subfield in in_matches and in_matches[subfield]:
        evidence = in_matches[subfield][:5]
    elif subfield in borderline_matches and borderline_matches[subfield]:
        evidence = borderline_matches[subfield][:5]
    else:
        evidence = []

    if evidence:
        screening_reason = (
            f"Heuristic matched {label.replace('_', ' ')} evidence for {subfield}: "
            f"{', '.join(evidence[:3])}."
        )
    else:
        screening_reason = "No strong QIS task, protocol, resource, or hardware terms were matched in title/abstract."

    return {
        "qis_relevance_label": label,
        "qis_subfield": subfield,
        "paper_type": choose_paper_type(text, subfield),
        "screening_reason": screening_reason,
        "key_qis_terms": json.dumps(evidence, ensure_ascii=False),
        "selected_for_pilot": False,
        "recognition_flag": False,
        "manual_review_needed": manual_review_needed,
    }


def make_empty_screening_file() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=SCREENING_FIELDS).to_csv(OUTPUT_CSV, index=False)
    print(f"Saved empty screening file to {OUTPUT_CSV}")


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not INPUT_CSV.exists():
        print(f"Input candidate pool does not exist: {INPUT_CSV}")
        make_empty_screening_file()
        return

    pool = pd.read_csv(INPUT_CSV)
    if pool.empty:
        print(f"Input candidate pool is empty: {INPUT_CSV}")
        make_empty_screening_file()
        return

    sample_size = min(SCREEN_SAMPLE_SIZE, len(pool))
    sampled = pool.sample(n=sample_size, random_state=RANDOM_SEED).reset_index(drop=True)
    print(f"Sampled {sample_size} records from {len(pool)} candidates with RANDOM_SEED={RANDOM_SEED}")

    screening_rows = []
    for idx, row in sampled.iterrows():
        screened = screen_record(row)
        screening_rows.append({"screen_id": f"SCREEN_{idx + 1:03d}", **screened})

    screening_df = pd.concat([sampled, pd.DataFrame(screening_rows)], axis=1)
    screening_df.to_csv(OUTPUT_CSV, index=False)

    label_counts = screening_df["qis_relevance_label"].value_counts().to_dict()
    print(f"Saved screening table to {OUTPUT_CSV}")
    print(f"QIS screening counts: {label_counts}")


if __name__ == "__main__":
    main()
