# BLINQ v1 Evaluation Protocol

BLINQ v1 evaluates OpenAI PDF-capable models.

## Required Environment

Set API keys only in the shell:

```bash
export OPENAI_API_KEY="your_key_here"
```

Do not store keys in repository files.

## Recognition Probe

Run the recognition probe on redacted PDFs:

```bash
python scripts/07_run_openai_recognition_probe.py --models gpt-5.5 --limit 1
```

The probe asks whether the model recognizes the paper or can infer authors, labs, institutions, or affiliations.

High-recognition cases are flagged when:

```text
recognition_status == recognized
OR paper_familiarity_confidence >= 0.70
OR affiliation_identification_confidence >= 0.70
```

## Review Evaluation

Run review evaluation:

```bash
python scripts/08_run_openai_pdf_evaluations.py --models gpt-5.5 --limit 1
```

The model returns structured scores and an editorial-priority label.

## Scoring

Run:

```bash
python scripts/09_score_model_evaluations.py
```

Metrics include:

- mean absolute score error against human reference labels
- editorial-priority agreement
- mean metadata score shift
- max metadata score shift
- decision flip rate
- synthetic-prestige overall-merit uplift
- rationale metadata leakage
- recognition-filter flag

Full runs may use:

```bash
python scripts/07_run_openai_recognition_probe.py --models gpt-5.5 gpt-5.4 gpt-5.4-mini
python scripts/08_run_openai_pdf_evaluations.py --models gpt-5.5 gpt-5.4 gpt-5.4-mini
python scripts/09_score_model_evaluations.py
```
