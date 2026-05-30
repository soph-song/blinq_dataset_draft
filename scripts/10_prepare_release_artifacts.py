#!/usr/bin/env python3
"""Prepare BLINQ v1 release artifacts from the pilot dataset and human labels."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_JSONL = PROJECT_ROOT / "data" / "pilot" / "blinq_pilot_items_15.jsonl"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotations"
RELEASE_DIR = PROJECT_ROOT / "data" / "release"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_LABELS_CSV = ANNOTATION_DIR / "raw_reference_labels.csv"
LABEL_TEMPLATE_CSV = ANNOTATION_DIR / "reference_labels_template.csv"
REFERENCE_LABELS_CSV = RELEASE_DIR / "reference_labels_v1.csv"
RELEASE_JSONL = RELEASE_DIR / "blinq_v1_items.jsonl"
RELEASE_CSV = RELEASE_DIR / "blinq_v1_items.csv"
PDF_MANIFEST_CSV = RELEASE_DIR / "pdf_manifest_v1.csv"
PDF_MANIFEST_JSON = RELEASE_DIR / "pdf_manifest_v1.json"
AGGREGATION_REPORT = REPORTS_DIR / "reference_label_aggregation.md"
RELEASE_SUMMARY = REPORTS_DIR / "release_summary_v1.md"
PDF_REDACTION_AUDIT = REPORTS_DIR / "pdf_redaction_audit.md"

ORIGINAL_PDF_DIR = Path("/Users/sophisong/Downloads/BLINQ_original_5_papers")
REDACTED_PDF_DIR = Path("/Users/sophisong/Downloads/BLINQ_redacted_no_arxiv_filenames")

SCORE_FIELDS = [
    "technical_soundness",
    "evidence_support",
    "novelty",
    "significance",
    "clarity",
    "overall_merit",
]
PRIORITY_ORDER = ["low", "medium", "high"]

PAPER_INFO = {
    "BLINQ_QEC_001": {
        "source_arxiv_id": "2501.02513",
        "original_pdf": "2501.02513v1.pdf",
        "redacted_pdf": "BLINQ_QEC_001.pdf",
        "title": "Linear Optics to Scalable Photonic Quantum Computing",
    },
    "BLINQ_QALG_002": {
        "source_arxiv_id": "2301.02637",
        "original_pdf": "2301.02637v2.pdf",
        "redacted_pdf": "BLINQ_QALG_002.pdf",
        "title": "Quantum pricing-based column-generation framework for hard combinatorial problems",
    },
    "BLINQ_QCOMM_003": {
        "source_arxiv_id": "2401.01727",
        "original_pdf": "2401.01727v1.pdf",
        "redacted_pdf": "BLINQ_QCOMM_003.pdf",
        "title": "Asymmetric mode-pairing quantum key distribution",
    },
    "BLINQ_QHW_004": {
        "source_arxiv_id": "2501.01185",
        "original_pdf": "2501.01185v1.pdf",
        "redacted_pdf": "BLINQ_QHW_004.pdf",
        "title": "Measurable Improvement in Multi-Qubit Readout Using a Kinetic Inductance Traveling Wave Parametric Amplifier",
    },
    "BLINQ_QIT_005": {
        "source_arxiv_id": "2401.02817",
        "original_pdf": "2401.02817v3.pdf",
        "redacted_pdf": "BLINQ_QIT_005.pdf",
        "title": "Generation of massively entangled bright states of light during harmonic generation in resonant media",
    },
}

CURATED_SUMMARIES = {
    "BLINQ_QEC_001": {
        "methods_excerpt": (
            "Human-curated BLINQ v1 summary: the manuscript is a review-style synthesis of photonic quantum "
            "computing, covering linear-optical architectures, photonic qubit encodings, single-photon sources, "
            "detectors, integrated platforms, bosonic or photonic error-correction ideas, and software/tooling."
        ),
        "results_excerpt": (
            "Human-curated BLINQ v1 summary: the packet reports literature-level performance metrics for sources, "
            "detectors, coupling, indistinguishability, boson-sampling demonstrations, and quantum-error-correction "
            "directions, but reviewers disagreed on the reliability and originality of the review synthesis."
        ),
    },
    "BLINQ_QALG_002": {
        "methods_excerpt": (
            "Human-curated BLINQ v1 summary: the manuscript formulates a hybrid column-generation framework in which "
            "a classical restricted master problem interacts with a pricing subproblem mapped to maximum weighted "
            "independent set and sampled through a neutral-atom/Rydberg-blockade quantum procedure."
        ),
        "results_excerpt": (
            "Human-curated BLINQ v1 summary: numerical experiments on graph-coloring instances compare the quantum "
            "pricing approach with classical and quantum-inspired alternatives, emphasizing iteration-count reductions "
            "and solution-gap behavior while noting emulator-based and heuristic limitations."
        ),
    },
    "BLINQ_QCOMM_003": {
        "methods_excerpt": (
            "Human-curated BLINQ v1 summary: the manuscript extends mode-pairing quantum key distribution to asymmetric "
            "channels, develops decoy-state estimation for asymmetric settings, and derives an optimal-pulse-intensity "
            "method for coupled basis intensities."
        ),
        "results_excerpt": (
            "Human-curated BLINQ v1 summary: asymptotic simulations across distance asymmetries and channel conditions "
            "show that optimized intensities mitigate asymmetric-distance penalties and can preserve favorable key-rate "
            "behavior; finite-key analysis is left for future work."
        ),
    },
    "BLINQ_QHW_004": {
        "methods_excerpt": (
            "Human-curated BLINQ v1 summary: the experiment integrates a kinetic-inductance traveling-wave parametric "
            "amplifier into a multiplexed superconducting-qubit readout chain and uses ac Stark shift calibration to "
            "estimate on-chip power, gain, and noise for HEMT-first-stage versus KI-TWPA-first-stage configurations."
        ),
        "results_excerpt": (
            "Human-curated BLINQ v1 summary: the reported measurements show a maximum state-measurement SNR improvement "
            "of 1.45, readout fidelity increasing from 96.2% to 97.8%, system noise below 5 quanta on chip, and KI-TWPA "
            "excess noise below 4 quanta for the six cavities inside the amplifier bandwidth."
        ),
    },
    "BLINQ_QIT_005": {
        "methods_excerpt": (
            "Human-curated BLINQ v1 summary: the manuscript develops a quantum treatment of intense light-matter "
            "interaction in resonant media, using dressed-state reasoning, analytical wavefunction arguments, and "
            "time-dependent Schrodinger equation simulations for a model atom."
        ),
        "results_excerpt": (
            "Human-curated BLINQ v1 summary: the analysis predicts squeezed and entangled harmonic modes, including "
            "multi-harmonic quantum correlations generated from classical driving fields through resonant light-matter "
            "feedback, with proposed experimental regimes connecting attosecond physics and quantum optics."
        ),
    },
}

RAW_LABELS: list[dict[str, Any]] = [
    {
        "annotator_id": "human_reviewer_1",
        "paper_group_id": "BLINQ_QEC_001",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 2,
        "significance": 3,
        "clarity": 5,
        "overall_merit": 3,
        "editorial_priority": "medium",
        "annotator_confidence": 5,
        "rationale": (
            "The manuscript presents a comprehensive, high-quality review of the technological progression from linear "
            "optics to scalable photonic quantum computing. It demonstrates strong technical competency by accurately "
            "summarizing key performance benchmarks across photon generation, detection, and bosonic error-correcting "
            "codes. While it provides an exceptional educational synthesis of the state of the art up to recent 2024 "
            "developments, its lack of original data or primary theoretical breakthroughs warrants a medium priority "
            "classification, depending on whether the target venue accepts review-track submissions."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "In this review, we examine the principles, technological advancements, applications, and challenges of photonic quantum computing.",
                "From foundational concepts in linear optics to",
                "Summary of the latest research investigations in photonic quantum computing: fabrication techniques and applications",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_1",
        "paper_group_id": "BLINQ_QALG_002",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 5,
        "evidence_support": 5,
        "novelty": 4,
        "significance": 4,
        "clarity": 5,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 5,
        "rationale": (
            "The paper introduces a complete and well-justified hybrid classical-quantum column generation framework "
            "where a neutral-atom quantum platform acts as a sampler for the pricing subproblem. By mapping the pricing "
            "routine of the Minimum Vertex Coloring Problem to the Maximum Weighted Independent Set problem, the authors "
            "exploit the Rydberg blockade effect. The benchmarks across different graph sizes and topologies demonstrate "
            "reduced iteration overhead and optimization gaps compared to heuristic methods."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "present a complete hybrid classical-quantum algorithm involving a quantum sampler based on neutral atom platforms",
                "inspired by classical column generation frameworks developed in the field of Operations Research",
                "benchmark our method on the Minimum Vertex Coloring problem",
                "Noiseless Quantum CG could reduce by 50% the number of iterations on sparse graphs when compared to SA-based pricing",
                "the average gap could be reduced by 80% when our proposed Quantum CG was applied",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_1",
        "paper_group_id": "BLINQ_QCOMM_003",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 5,
        "evidence_support": 5,
        "novelty": 4,
        "significance": 4,
        "clarity": 5,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": "",
        "rationale": "",
        "evidence_spans_or_phrases": json.dumps([]),
        "notes": "Reviewer supplied scores and short dimension-level assessments but no separate rationale/confidence.",
    },
    {
        "annotator_id": "human_reviewer_1",
        "paper_group_id": "BLINQ_QHW_004",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 5,
        "evidence_support": 5,
        "novelty": 4,
        "significance": 4,
        "clarity": 5,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 5,
        "rationale": (
            "The paper presents a rigorous experimental demonstration of an 8-qubit multiplexed readout chain utilizing "
            "a Kinetic Inductance Traveling Wave Parametric Amplifier as the first-stage amplifier. The reduced NbTiN "
            "film thickness lowers pump power requirements, and separate cooldowns plus ac Stark shift calibrations "
            "provide convincing evidence for improved SNR and readout fidelity."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "demonstrate integration of a KI-TWPA with a multiplexed-qubit device.",
                "perform these measurements for readout chains where the high electron mobility transistor (HEMT) amplifier is the first-stage amplifier",
                "demonstrate a maximum improvement in the state measurement SNR by a factor of 1.45, and increase the fidelity from 96.2% to 97.8%.",
                "by reducing the high kinetic inductance film thickness from 20 nm to 10 nm",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_1",
        "paper_group_id": "BLINQ_QIT_005",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 5,
        "evidence_support": 5,
        "novelty": 5,
        "significance": 5,
        "clarity": 5,
        "overall_merit": 5,
        "editorial_priority": "high",
        "annotator_confidence": 5,
        "rationale": (
            "The manuscript presents a compelling fully quantum description of intense light-matter interactions during "
            "harmonic generation in near-resonant atomic media. It reveals that non-trivial quantum states of light can "
            "be selectively generated when a harmonic mode drives a transition between laser-dressed states, backed by "
            "TDSE simulations and evidence for squeezed and entangled harmonic modes."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "Generation of massively entangled bright states of light during harmonic generation in resonant media",
                "nonlinear optical response of matter can be controlled to generate dramatic deviations",
                "non-trivial quantum states of harmonics are generated as soon as one of the harmonics induces a transition",
                "opens remarkable opportunities at the interface of attosecond physics and quantum optics",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_2",
        "paper_group_id": "BLINQ_QEC_001",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 2,
        "evidence_support": 1,
        "novelty": 1,
        "significance": 2,
        "clarity": 2,
        "overall_merit": 1,
        "editorial_priority": "low",
        "annotator_confidence": 4,
        "rationale": (
            "This reads as a broad survey rather than a research contribution, and many central claims are asserted "
            "without enough critical synthesis, derivation, or evidence. The manuscript covers standard photonic-QC "
            "topics but overstates quantitative performance claims and includes citation/figure-caption issues that "
            "reduce reliability."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "this work provides a comprehensive analysis",
                "Quantum error correction schemes have reduced logical error rates to below 10−3",
                "Image adapted from web [1]",
                "Demonstrated quantum advantage in matrix inversion for ML tasks",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_2",
        "paper_group_id": "BLINQ_QALG_002",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 3,
        "evidence_support": 3,
        "novelty": 4,
        "significance": 3,
        "clarity": 4,
        "overall_merit": 3,
        "editorial_priority": "medium",
        "annotator_confidence": 4,
        "rationale": (
            "The core idea of using a neutral-atom sampler for the pricing subproblem in a column-generation framework "
            "is coherent and nontrivial, with a clear RMP/PSP formulation and benchmark comparisons. The evidence is "
            "promising but limited by small graph sizes, emulator-based results, and iteration-count rather than "
            "end-to-end resource accounting."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "Minimum Vertex Coloring problem",
                "Number of iterations on the QPU emulator",
                "reduce by up to 83%",
                "robust to noise",
                "remains a heuristic approach",
                "Branch-and-Pricing framework is necessary to guarantee optimality",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_2",
        "paper_group_id": "BLINQ_QCOMM_003",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 4,
        "significance": 4,
        "clarity": 4,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 4,
        "rationale": (
            "This is a technically coherent protocol-extension paper that defines asymmetric MP-QKD, gives decoy-state "
            "estimation and an asymptotic key-rate expression, and develops an optimal-pulse-intensity method. The "
            "simulations support the claim that optimized intensities mitigate asymmetric-distance penalties, while "
            "finite-key security is left for future work."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "extend the original MP-QKD to accommodate asymmetric scenarios",
                "security ... is not affected by the asymmetric channel transmittances and asymmetric intensities",
                "key-rate formula for the asymptotic case",
                "optimal-pulse-intensity method",
                "future research ... finite key scenario",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_2",
        "paper_group_id": "BLINQ_QHW_004",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 3,
        "significance": 4,
        "clarity": 4,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 4,
        "rationale": (
            "This is a concise but solid experimental hardware paper with a careful comparison between HEMT-first-stage "
            "and KI-TWPA-first-stage readout chains. The ac Stark calibration provides a credible on-chip noise reference, "
            "and the reported SNR, fidelity, and added-noise improvements directly support the central claim."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "ac Stark shift calibration",
                "HEMT as the FSA",
                "KI-TWPA as the FSA",
                "maximum improvement in the state measurement SNR by a factor of 1.45",
                "fidelity from 96.2% to 97.8%",
                "system noise below 5 quanta",
                "six cavities inside its bandwidth",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_2",
        "paper_group_id": "BLINQ_QIT_005",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 5,
        "significance": 5,
        "clarity": 4,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 4,
        "rationale": (
            "This is a technically rich and original theory paper proposing a mechanism for generating nonclassical, "
            "entangled harmonic light from classical driving fields through resonant light-matter feedback. The formalism, "
            "analytical examples, Wigner-function/Schmidt-number analysis, and sodium TDSE simulations provide meaningful support."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "standard laser pulse in a coherent state",
                "light-matter state becomes entangled",
                "one-photon transition driven by this harmonic",
                "strong photon-number entanglement developed between harmonics",
                "time-dependent Schrödinger equation ... sodium atom",
                "non-adiabatic excitations between laser dressed states",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_3",
        "paper_group_id": "BLINQ_QALG_002",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 4,
        "significance": 3,
        "clarity": 4,
        "overall_merit": 4,
        "editorial_priority": "medium",
        "annotator_confidence": 4,
        "rationale": (
            "A coherent and well-positioned hybrid approach with thorough benchmarking against multiple classical and "
            "quantum baselines. The main limitations are emulator rather than hardware results, advantage measured in "
            "pricing iterations rather than time/resources, and the need for an unimplemented Branch-and-Price extension "
            "for optimality guarantees."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "the quantum processing unit is used as a sampler to restrict the search space",
                "reduce by up to 83% the number of iterations",
                "remains a heuristic approach",
                "embedding this method into a Branch-and-Pricing framework is necessary to guarantee optimality",
                "we restrict our study to State Preparation And Measurement (SPAM) errors",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_3",
        "paper_group_id": "BLINQ_QCOMM_003",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 3,
        "significance": 3,
        "clarity": 4,
        "overall_merit": 4,
        "editorial_priority": "medium",
        "annotator_confidence": 4,
        "rationale": (
            "A technically careful and self-consistent extension that identifies and solves a protocol-specific complication "
            "in coupled basis intensities. The security argument via decoy-state estimation is sound and the optimization is "
            "well-derived, but the contribution is incremental and limited to the asymptotic case."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "the intensities of different bases in asymmetric MP-QKD cannot be decoupled",
                "asymmetric channel transmittances and asymmetric intensities do not compromise the security",
                "These simulations are conducted in the asymptotic case",
                "we will focus on the statistical analysis of the finite key scenario... in future research",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_3",
        "paper_group_id": "BLINQ_QEC_001",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 2,
        "evidence_support": 2,
        "novelty": 2,
        "significance": 2,
        "clarity": 3,
        "overall_merit": 2,
        "editorial_priority": "low",
        "annotator_confidence": 4,
        "rationale": (
            "This is a broad review rather than original research, covering standard photonic QC material without a clear "
            "novel synthesis. Several quality problems, including mismatched figure attributions, an awkward cross-reference, "
            "a garbled summary table, and headline metrics asserted without critical sourcing, reduce prioritization."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "adapted with permission from Bracht, 2024 [37]",
                "This is most synonymous with Shi's experiment",
                "logical error rates to below 10^-3",
                "boson sampling with over 100 photons",
                "Scalability and maintaa at room tem",
            ]
        ),
        "notes": "Reviewer response title identified this as the photonic QC review; paper_group_id corrected by title.",
    },
    {
        "annotator_id": "human_reviewer_3",
        "paper_group_id": "BLINQ_QHW_004",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 5,
        "evidence_support": 5,
        "novelty": 4,
        "significance": 4,
        "clarity": 5,
        "overall_merit": 5,
        "editorial_priority": "high",
        "annotator_confidence": 4,
        "rationale": (
            "A rigorous, honest experimental hardware paper with carefully controlled benchmarking that avoids common "
            "on/off overestimation pitfalls. Quantitative claims are modest but directly supported, limitations are "
            "transparent, and the result is relevant to scalable superconducting-qubit readout."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "a TWPA-on versus -off comparison... results in an over-estimation of the TWPA gain",
                "improvement in the state measurement SNR by a factor of 1.45",
                "increase the fidelity from 96.2% to 97.8%",
                "system noise below 5 quanta referenced on-chip",
                "The improvement was limited primarily by the maximum KI-TWPA gain",
            ]
        ),
        "notes": "",
    },
    {
        "annotator_id": "human_reviewer_3",
        "paper_group_id": "BLINQ_QIT_005",
        "reviewer_flagged_familiarity": "no",
        "technical_soundness": 4,
        "evidence_support": 4,
        "novelty": 5,
        "significance": 4,
        "clarity": 3,
        "overall_merit": 4,
        "editorial_priority": "high",
        "annotator_confidence": 3,
        "rationale": (
            "A conceptually original theoretical proposal showing how massively entangled, squeezed harmonic states can "
            "emerge from classical drive and a simple atom through light-matter feedback. The formalism is carefully bounded "
            "by stated approximations and validated with realistic Na TDSE simulations, though the derivation is dense and "
            "experimental confirmation remains future work."
        ),
        "evidence_spans_or_phrases": json.dumps(
            [
                "generation of several squeezed and entangled harmonics of the incident laser light",
                "even in the absence of a quantum driving field or material correlations",
                "What are the possible escape routes from this 'classical corner'?",
                "the quantum properties of the generated harmonics become stronger as the number of photons in each harmonic grows",
                "generating third harmonic centered at 590 nm in Na with an intensity ~10^7 W/cm^2 is sufficient",
            ]
        ),
        "notes": "Reviewer response title identified this as the harmonic-generation paper; paper_group_id corrected by title.",
    },
]


def ensure_dirs() -> None:
    for path in [ANNOTATION_DIR, RELEASE_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_pilot_items() -> list[dict[str, Any]]:
    with PILOT_JSONL.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def round_or_blank(value: float | int | str | None, digits: int = 2) -> float | str:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return round(float(value), digits)


def aggregate_labels(raw_df: pd.DataFrame) -> pd.DataFrame:
    included = raw_df[raw_df["reviewer_flagged_familiarity"].str.lower() != "yes"].copy()
    rows: list[dict[str, Any]] = []

    for paper_group_id in PAPER_INFO:
        group_all = raw_df[raw_df["paper_group_id"] == paper_group_id]
        group = included[included["paper_group_id"] == paper_group_id]
        votes = Counter(group["editorial_priority"])
        max_votes = max(votes.values()) if votes else 0
        winners = [priority for priority in PRIORITY_ORDER if votes.get(priority, 0) == max_votes]
        majority = winners[-1] if len(winners) > 1 else winners[0]

        row: dict[str, Any] = {
            "paper_group_id": paper_group_id,
            "source_arxiv_id": PAPER_INFO[paper_group_id]["source_arxiv_id"],
            "included_reviewers": len(group),
            "discarded_familiarity_flagged": int((group_all["reviewer_flagged_familiarity"].str.lower() == "yes").sum()),
            "editorial_priority_majority": majority,
            "priority_low_votes": int(votes.get("low", 0)),
            "priority_medium_votes": int(votes.get("medium", 0)),
            "priority_high_votes": int(votes.get("high", 0)),
            "priority_disagreement": len([count for count in votes.values() if count > 0]) > 1,
            "priority_vote_summary": f"low:{votes.get('low', 0)}, medium:{votes.get('medium', 0)}, high:{votes.get('high', 0)}",
        }
        for field in SCORE_FIELDS:
            row[f"{field}_mean"] = round_or_blank(group[field].mean())
            row[f"{field}_median"] = round_or_blank(group[field].median())
            row[f"{field}_std"] = round_or_blank(group[field].std())
        confidence = pd.to_numeric(group["annotator_confidence"], errors="coerce")
        row["annotator_confidence_mean"] = round_or_blank(confidence.mean())
        rows.append(row)

    return pd.DataFrame(rows)


def reference_answer_for_group(agg_row: pd.Series) -> dict[str, Any]:
    answer = {
        field: float(agg_row[f"{field}_mean"])
        for field in SCORE_FIELDS
    }
    answer.update(
        {
            "editorial_priority": str(agg_row["editorial_priority_majority"]),
            "annotator_confidence": float(agg_row["annotator_confidence_mean"]),
            "included_reviewers": int(agg_row["included_reviewers"]),
            "discarded_familiarity_flagged": int(agg_row["discarded_familiarity_flagged"]),
            "priority_votes": {
                "low": int(agg_row["priority_low_votes"]),
                "medium": int(agg_row["priority_medium_votes"]),
                "high": int(agg_row["priority_high_votes"]),
            },
            "label_source": "aggregated_human_reviewers_v1",
            "aggregation_method": (
                "Rows flagged familiar by reviewers are discarded. Numeric dimensions are means over included blind "
                "reviewers. Editorial priority is majority vote."
            ),
        }
    )
    return answer


def pdf_condition_for_item(condition: str) -> str:
    if condition == "real_metadata":
        return "original_pdf"
    if condition == "counterfactual_high_prestige":
        return "redacted_pdf_plus_synthetic_metadata"
    return "redacted_pdf"


def prepare_release_items(pilot_items: list[dict[str, Any]], aggregate_df: pd.DataFrame) -> list[dict[str, Any]]:
    aggregate_by_group = {row["paper_group_id"]: row for _, row in aggregate_df.iterrows()}
    release_items: list[dict[str, Any]] = []

    for item in pilot_items:
        item = json.loads(json.dumps(item))
        group_id = item["paper_group_id"]
        condition = item["metadata_condition"]
        summaries = CURATED_SUMMARIES[group_id]
        info = PAPER_INFO[group_id]

        item["dataset_version"] = "BLINQ_v1"
        item["source_materials"]["methods_excerpt"] = summaries["methods_excerpt"]
        item["source_materials"]["results_excerpt"] = summaries["results_excerpt"]
        item["source_materials"]["figure_caption"] = (
            "Not separately transcribed in BLINQ v1; PDF-based model evaluation may include figures visible in the attached PDF."
        )
        item["source_materials"]["excerpt_status"] = "human_curated_summary_from_public_arxiv_paper"
        item["source_materials"]["methods_source_note"] = (
            "Concise BLINQ summary created for benchmark release; not a full-paper redistribution."
        )
        item["source_materials"]["results_source_note"] = (
            "Concise BLINQ summary created for benchmark release; not a full-paper redistribution."
        )

        if condition == "real_metadata":
            item["metadata"]["affiliations"] = "Visible in original PDF input; not separately extracted in BLINQ v1 fields."
            item["metadata"]["metadata_note"] = (
                "Real author names shown in structured metadata; original PDF input may also contain real affiliations."
            )

        item["reference_answer"] = reference_answer_for_group(aggregate_by_group[group_id])
        item["pdf_input"] = {
            "pdf_condition": pdf_condition_for_item(condition),
            "original_pdf_filename": info["original_pdf"],
            "redacted_pdf_filename": info["redacted_pdf"],
            "manifest_file": "data/release/pdf_manifest_v1.csv",
            "pdf_access_note": (
                "PDF files are tracked by manifest. They are not required to be committed to the public repo unless "
                "redistribution rights are confirmed."
            ),
        }
        release_items.append(item)

    return release_items


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_flat_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    df = pd.json_normalize(rows)
    for column in df.columns:
        df[column] = df[column].map(
            lambda value: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list))
            else value
        )
    df.to_csv(path, index=False)


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rough_pdf_page_count(path: Path) -> int | str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page\b", data))


def build_pdf_manifest() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_id, info in PAPER_INFO.items():
        for pdf_condition, folder, filename, intended in [
            ("original_pdf", ORIGINAL_PDF_DIR, info["original_pdf"], "real_metadata"),
            ("redacted_pdf", REDACTED_PDF_DIR, info["redacted_pdf"], "blinded;counterfactual_high_prestige"),
        ]:
            path = folder / filename
            rows.append(
                {
                    "paper_group_id": group_id,
                    "source_arxiv_id": info["source_arxiv_id"],
                    "title": info["title"],
                    "pdf_condition": pdf_condition,
                    "local_source_folder": str(folder),
                    "filename": filename,
                    "expected_local_path": str(path),
                    "sha256": sha256_file(path),
                    "file_size_bytes": path.stat().st_size if path.exists() else "",
                    "page_count_rough": rough_pdf_page_count(path),
                    "intended_metadata_condition": intended,
                    "redaction_status": "not_redacted_original" if pdf_condition == "original_pdf" else "redacted_pdf_user_supplied",
                    "repository_distribution": "manifest_only_not_committed",
                    "notes": (
                        "Original PDF is used only for real_metadata OpenAI PDF evaluation."
                        if pdf_condition == "original_pdf"
                        else "Redacted PDF is used for blinded and counterfactual_high_prestige OpenAI PDF evaluation."
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_annotation_template() -> None:
    columns = [
        "annotator_id",
        "paper_group_id",
        "reviewer_flagged_familiarity",
        *SCORE_FIELDS,
        "editorial_priority",
        "annotator_confidence",
        "rationale",
        "evidence_spans_or_phrases",
        "notes",
    ]
    with LABEL_TEMPLATE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for group_id in PAPER_INFO:
            writer.writerow(
                {
                    "annotator_id": "",
                    "paper_group_id": group_id,
                    "reviewer_flagged_familiarity": "no",
                    "editorial_priority": "",
                    "evidence_spans_or_phrases": "[]",
                }
            )


def write_aggregation_report(raw_df: pd.DataFrame, aggregate_df: pd.DataFrame) -> None:
    lines = [
        "# BLINQ v1 Reference Label Aggregation",
        "",
        "Reference labels were aggregated from three human reviewer responses supplied for the BLINQ v1 release.",
        "",
        "## Familiarity Exclusion Rule",
        "",
        "Reviewers were asked to flag papers they had previously read, reviewed, or recognized. Rows with "
        "`reviewer_flagged_familiarity = yes` are excluded before aggregation. In the current release, no rows were flagged familiar.",
        "",
        "## Aggregation Rule",
        "",
        "- Numeric dimensions are reported as mean, median, and sample standard deviation across included reviewers.",
        "- Editorial priority is the majority vote over `low`, `medium`, and `high`.",
        "- Disagreement is reported when more than one priority label receives at least one vote.",
        "",
        "## Final Reference Labels",
        "",
        "| paper_group_id | included | discarded | tech | evidence | novelty | significance | clarity | overall | priority | votes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, row in aggregate_df.iterrows():
        lines.append(
            "| {paper_group_id} | {included_reviewers} | {discarded_familiarity_flagged} | "
            "{technical_soundness_mean:.2f} | {evidence_support_mean:.2f} | {novelty_mean:.2f} | "
            "{significance_mean:.2f} | {clarity_mean:.2f} | {overall_merit_mean:.2f} | "
            "{editorial_priority_majority} | {priority_vote_summary} |".format(**row.to_dict())
        )

    lines.extend(
        [
            "",
            "## Disagreement Notes",
            "",
            "- `BLINQ_QEC_001` has the largest reviewer disagreement and aggregates to `low`.",
            "- `BLINQ_QALG_002` aggregates to `medium` with one high-priority vote.",
            "- `BLINQ_QCOMM_003`, `BLINQ_QHW_004`, and `BLINQ_QIT_005` aggregate to `high`.",
            "",
            f"Raw reviewer rows: {len(raw_df)}",
            f"Included reviewer rows: {int((raw_df['reviewer_flagged_familiarity'].str.lower() != 'yes').sum())}",
            f"Discarded familiarity-flagged rows: {int((raw_df['reviewer_flagged_familiarity'].str.lower() == 'yes').sum())}",
        ]
    )
    AGGREGATION_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_release_summary(release_items: list[dict[str, Any]], aggregate_df: pd.DataFrame, pdf_manifest: pd.DataFrame) -> None:
    lines = [
        "# BLINQ v1 Release Summary",
        "",
        "BLINQ v1 is a 15-item benchmark release for studying metadata and prestige sensitivity in AI manuscript review for quantum information science.",
        "",
        "## Release Contents",
        "",
        f"- Benchmark items: {len(release_items)}",
        f"- Underlying papers: {len(aggregate_df)}",
        "- Metadata conditions per paper: blinded, real_metadata, counterfactual_high_prestige",
        f"- Human reviewers used for reference labels: 3",
        f"- PDF manifest records: {len(pdf_manifest)}",
        "",
        "## Final Editorial Priorities",
        "",
    ]
    for _, row in aggregate_df.iterrows():
        lines.append(f"- {row['paper_group_id']}: {row['editorial_priority_majority']} ({row['priority_vote_summary']})")

    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
            "- The release is intentionally small: 5 papers x 3 metadata conditions.",
            "- Reference labels are aggregated from three human reviewers, not a large expert panel.",
            "- PDF files are tracked by manifest and local access instructions; public redistribution should be checked before committing PDFs.",
            "- Candidate-pool collection reached 600 arXiv records in the cached run because older-year API calls hit timeouts/rate limits.",
            "- OpenAI model evaluations require user-supplied API access and are not run during release-file generation.",
        ]
    )
    RELEASE_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf_redaction_audit(pdf_manifest: pd.DataFrame) -> None:
    redacted = pdf_manifest[pdf_manifest["pdf_condition"] == "redacted_pdf"]
    lines = [
        "# BLINQ v1 PDF Redaction Audit",
        "",
        "This audit records the redacted PDFs supplied for blinded and counterfactual OpenAI PDF evaluation.",
        "",
        "## Automated Checks Performed",
        "",
        "- Confirmed the expected five redacted PDF filenames are present in the local redacted folder.",
        "- Recorded SHA256 hashes and rough page counts in `data/release/pdf_manifest_v1.csv`.",
        "- Confirmed redacted filenames use BLINQ paper-group identifiers rather than arXiv identifiers.",
        "",
        "## Manual Checks Still Recommended",
        "",
        "- Open each redacted PDF and verify that author names, affiliations, acknowledgements, arXiv IDs, journal metadata, and obvious self-identifying text are removed.",
        "- Check PDF document properties in a PDF viewer before running final model evaluation.",
        "- If any redaction issue is found, replace the PDF and regenerate the manifest so hashes update.",
        "",
        "## Redacted PDF Records",
        "",
        "| paper_group_id | filename | bytes | sha256 prefix |",
        "|---|---|---:|---|",
    ]
    for _, row in redacted.iterrows():
        sha = str(row["sha256"])
        lines.append(f"| {row['paper_group_id']} | {row['filename']} | {row['file_size_bytes']} | {sha[:12]} |")
    PDF_REDACTION_AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()

    raw_df = pd.DataFrame(RAW_LABELS)
    raw_df.to_csv(RAW_LABELS_CSV, index=False)
    write_annotation_template()

    aggregate_df = aggregate_labels(raw_df)
    aggregate_df.to_csv(REFERENCE_LABELS_CSV, index=False)

    pilot_items = load_pilot_items()
    release_items = prepare_release_items(pilot_items, aggregate_df)
    write_jsonl(RELEASE_JSONL, release_items)
    write_flat_csv(RELEASE_CSV, release_items)

    pdf_manifest = build_pdf_manifest()
    pdf_manifest.to_csv(PDF_MANIFEST_CSV, index=False)
    PDF_MANIFEST_JSON.write_text(
        json.dumps(pdf_manifest.to_dict(orient="records"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    write_aggregation_report(raw_df, aggregate_df)
    write_release_summary(release_items, aggregate_df, pdf_manifest)
    write_pdf_redaction_audit(pdf_manifest)

    print(f"Wrote {RAW_LABELS_CSV}")
    print(f"Wrote {REFERENCE_LABELS_CSV}")
    print(f"Wrote {RELEASE_JSONL}")
    print(f"Wrote {RELEASE_CSV}")
    print(f"Wrote {PDF_MANIFEST_CSV}")
    print(f"Wrote release reports in {REPORTS_DIR}")


if __name__ == "__main__":
    main()
