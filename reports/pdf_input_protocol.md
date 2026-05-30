# BLINQ v1 PDF Input Protocol

BLINQ v1 uses PDF inputs for OpenAI model evaluation.

## Local PDF Folders

```text
/Users/sophisong/Downloads/BLINQ_original_5_papers
/Users/sophisong/Downloads/BLINQ_redacted_no_arxiv_filenames
```

The manifest is:

```text
data/release/pdf_manifest_v1.csv
```

## Metadata Condition Mapping

- `blinded`: attach redacted PDF.
- `real_metadata`: attach original PDF.
- `counterfactual_high_prestige`: attach redacted PDF and include synthetic high-prestige metadata in the prompt.

## Redaction Expectations

Redacted PDFs should remove author names, affiliations, arXiv identifiers, acknowledgements, journal metadata, and obvious self-identifying cues where possible. The model should not receive source URLs or arXiv IDs in the blinded prompt.

## Validation

Run:

```bash
python scripts/06_validate_pdf_inputs.py
```

This checks manifest structure, file existence, size, SHA256 hashes, and redacted filename conventions.
