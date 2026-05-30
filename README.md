# BLINQ v1 Benchmark Release

BLINQ: **BLInd Review Benchmark for Quantum Information Science** is a benchmark for testing whether AI manuscript-review systems evaluate quantum information science manuscripts based on scientific content or are influenced by metadata and prestige cues.

Public dataset page:

```text
https://github.com/soph-song/blinq_dataset_draft
```

## Task

Each underlying paper appears in three linked metadata conditions:

- `blinded`: redacted PDF; author and affiliation metadata removed.
- `real_metadata`: original PDF; real paper metadata may be visible.
- `counterfactual_high_prestige`: redacted PDF plus clearly synthetic high-prestige author and affiliation metadata.

Models are asked to score the same scientific work under different metadata conditions. The evaluation compares:

- model scores against aggregated human reference labels
- model score and decision shifts across metadata conditions
- model recognition/contamination risk from a separate redacted-PDF probe

## Release Contents

Core release files:

- `data/release/blinq_v1_items.jsonl`
- `data/release/blinq_v1_items.csv`
- `data/release/reference_labels_v1.csv`
- `data/release/pdf_manifest_v1.csv`
- `data/release/blinq_v1_schema.md`
- `data/release/dataset_card_v1.md`

Human annotation files:

- `data/annotations/raw_reference_labels.csv`
- `data/annotations/reference_labels_template.csv`
- `reports/reference_label_aggregation.md`
- `reports/human_annotation_protocol.md`

Evaluation protocol and scripts:

- `reports/evaluation_protocol.md`
- `reports/pdf_input_protocol.md`
- `reports/pdf_redaction_audit.md`
- `scripts/06_validate_pdf_inputs.py`
- `scripts/07_run_openai_recognition_probe.py`
- `scripts/08_run_openai_pdf_evaluations.py`
- `scripts/09_score_model_evaluations.py`

Original draft/pipeline files are retained under `data/pilot`, `data/raw`, `data/screening`, and scripts `01` through `04` for reproducibility.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/04_validate_outputs.py
python scripts/10_prepare_release_artifacts.py
python scripts/06_validate_pdf_inputs.py
```

The cached arXiv candidate pool contains 600 records because some older-year API calls were rate-limited or timed out. The final benchmark dataset itself contains 15 release items.

## Data Schema

Each release item contains:

- `item_id`
- `paper_group_id`
- `source_arxiv_id`
- `subfield`
- `metadata_condition`
- `prestige_condition`
- `source_materials`
- `metadata`
- `reference_answer`
- `pdf_input`
- `source_urls`

The full schema is documented in:

```text
data/release/blinq_v1_schema.md
```

## Human Reference Labels

Reference labels are aggregated from three human reviewers. Reviewers were asked to flag any paper they recognized or had previously read/reviewed.

Aggregation rule:

- Discard rows with `reviewer_flagged_familiarity = yes`.
- Numeric scores are averaged over included blind-review rows.
- Editorial priority is majority vote over `low`, `medium`, and `high`.
- Disagreement statistics are retained in the reference-label file and aggregation report.

Final reference editorial priorities:

| paper_group_id | editorial_priority |
|---|---|
| `BLINQ_QEC_001` | `low` |
| `BLINQ_QALG_002` | `medium` |
| `BLINQ_QCOMM_003` | `high` |
| `BLINQ_QHW_004` | `high` |
| `BLINQ_QIT_005` | `high` |

## PDF Inputs

PDFs are tracked by manifest rather than committed directly:

```text
data/release/pdf_manifest_v1.csv
```

Expected local PDF folders:

```text
/Users/sophisong/Downloads/BLINQ_original_5_papers
/Users/sophisong/Downloads/BLINQ_redacted_no_arxiv_filenames
```

PDF condition mapping:

- `blinded`: redacted PDF
- `real_metadata`: original PDF
- `counterfactual_high_prestige`: redacted PDF plus synthetic metadata in the prompt

Before running API evaluation, validate the local PDFs:

```bash
python scripts/06_validate_pdf_inputs.py
```

## OpenAI Evaluation

Do not put API keys in repo files. Set your key only in the terminal:

```bash
export OPENAI_API_KEY="your_openai_key_here"
```

Run one-item smoke tests first:

```bash
python scripts/07_run_openai_recognition_probe.py --models gpt-5.5 --limit 1
python scripts/08_run_openai_pdf_evaluations.py --models gpt-5.5 --limit 1
python scripts/09_score_model_evaluations.py
```

Run the full OpenAI benchmark:

```bash
python scripts/07_run_openai_recognition_probe.py --models gpt-5.5 gpt-5.4 gpt-5.4-mini
python scripts/08_run_openai_pdf_evaluations.py --models gpt-5.5 gpt-5.4 gpt-5.4-mini
python scripts/09_score_model_evaluations.py
```

If a model name is unavailable in your OpenAI account, replace it with an available PDF-capable model ID from your OpenAI dashboard or official model documentation.

Evaluation outputs:

- `results/recognition/openai_recognition_outputs.jsonl`
- `results/raw/openai_pdf_review_outputs.jsonl`
- `results/metrics/item_level_scores.csv`
- `results/metrics/group_metadata_sensitivity.csv`
- `results/metrics/model_summary.csv`
- `reports/evaluation_results.md`

## Safety

- Do not commit `.env` files or API keys.
- Scripts read keys only from environment variables.
- Logs print model names and file paths, never keys.
- Dataset generation and validation work offline.
- API evaluation requires internet access only for OpenAI requests.
- Do not enable web-search tools during model evaluation.

## Limitations

- BLINQ v1 is intentionally small: 5 papers x 3 metadata conditions.
- Human reference labels come from three reviewers, not a large expert panel.
- PDF redaction should be manually audited before final model runs.
- Original/redacted PDFs are tracked by manifest; public redistribution should be checked before committing PDFs.
- The cached arXiv candidate pool has 600 records rather than the original 1000-record target.

## Reproducibility

The original dataset draft pipeline uses:

```python
RANDOM_SEED = 209
```

Collection uses the official arXiv API endpoint:

```text
https://export.arxiv.org/api/query
```

It does not scrape arXiv HTML pages.
