# BLINQ Dataset Draft Pipeline

BLINQ: BLInd Review Benchmark for Quantum Information Science is a draft benchmark pipeline for testing whether AI manuscript reviewers evaluate quantum information science papers based on scientific content or are influenced by prestige cues such as author names and institutional affiliations.

This repository draft builds:

- a 1000-paper arXiv `quant-ph` candidate pool when the arXiv API returns enough records
- a reproducible random sample of 100 candidate papers
- a heuristic QIS relevance-screening table
- a 15-item pilot dataset made from 5 papers x 3 metadata conditions
- a draft rubric, prompt templates, dataset card, and summary report

## Setup and Run

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/01_collect_arxiv_quant_ph.py
python scripts/02_sample_and_screen.py
python scripts/03_build_pilot_items.py
python scripts/04_validate_outputs.py
```

The collector uses the official arXiv API endpoint:

```text
https://export.arxiv.org/api/query
```

It does not scrape arXiv HTML pages and does not download PDFs.

## Output Files

- `data/raw/quant_ph_candidate_pool_1000.csv`: arXiv `quant-ph` candidate metadata with title, abstract, authors, categories, comments, journal reference, DOI, abstract URL, PDF URL, collection query, and collection year.
- `data/screening/candidate_screening_100.csv`: reproducible sample of 100 candidates plus heuristic QIS screening fields.
- `data/pilot/blinq_pilot_items_15.jsonl`: nested pilot benchmark items for model evaluation.
- `data/pilot/blinq_pilot_items_15.csv`: flattened CSV copy of the pilot benchmark items.
- `data/pilot/rubric_v1.md`: draft scoring rubric and fairness/stability metrics.
- `data/pilot/model_eval_prompt_template.md`: blinded and metadata-visible model-evaluation prompt templates.
- `data/pilot/dataset_card.md`: dataset card for the pilot draft.
- `reports/dataset_draft_summary.md`: collection, screening, and pilot-selection summary.

## Inspect the Pilot Dataset

```bash
python -c "import pandas as pd; df = pd.read_csv('data/pilot/blinq_pilot_items_15.csv'); print(df[['item_id', 'paper_group_id', 'metadata_condition', 'source_arxiv_id', 'subfield']])"
```

For the JSONL version:

```bash
python -c "import json; print(json.dumps(json.loads(open('data/pilot/blinq_pilot_items_15.jsonl').readline()), indent=2))"
```

## Reproducibility Controls

The pipeline uses:

```python
RANDOM_SEED = 209
```

To modify the random seed, edit the `RANDOM_SEED` constant in:

- `scripts/01_collect_arxiv_quant_ph.py`
- `scripts/02_sample_and_screen.py`
- `scripts/03_build_pilot_items.py`

To modify the year range, edit the `YEARS` constant in:

- `scripts/01_collect_arxiv_quant_ph.py`

The default collection window is 2018 through 2026. Collection is year-stratified so the candidate pool is not just the newest papers.

## Screening Warning

The QIS relevance labels are draft heuristic labels based on title and abstract keyword scoring. They are not completed human expert labels and must be manually checked before using the dataset for scientific conclusions.

Reference labels in the pilot items are intentionally initialized as `TBD_human_annotation`. Methods and results excerpts are placeholders marked `TBD_manual_excerpt`.

## Demo LLM Reference Labels

For a class demo, keep LLM-generated labels separate from future human labels. Do not overwrite `reference_answer`; use `demo_llm_reference_answer` in a separate output file.

Generate one blinded labeling prompt per paper group:

```bash
python scripts/05_prepare_demo_llm_reference_labels.py
```

This writes:

- `data/pilot/demo_llm_reference_label_prompts.jsonl`
- `data/pilot/demo_llm_reference_label_responses_template.jsonl`

To automate with a local LLM command that reads a prompt from stdin and prints JSON to stdout:

```bash
python scripts/05_prepare_demo_llm_reference_labels.py --labeler-command "ollama run qwen2.5:14b-instruct"
```

To automate with the OpenAI API, export your key in the shell where you will run the script:

```bash
export OPENAI_API_KEY="your_api_key_here"
python scripts/05_prepare_demo_llm_reference_labels.py --openai-model gpt-5.5
```

Do not paste API keys into dataset files or Python source files.

To merge responses created elsewhere, fill one JSON object per line in a responses file and run:

```bash
python scripts/05_prepare_demo_llm_reference_labels.py --responses-input data/pilot/demo_llm_reference_label_responses.jsonl
```

The labeled demo files are written to:

- `data/pilot/blinq_pilot_items_15_with_demo_llm_labels.jsonl`
- `data/pilot/blinq_pilot_items_15_with_demo_llm_labels.csv`

These labels are for demonstration only and are not human expert reference labels.
