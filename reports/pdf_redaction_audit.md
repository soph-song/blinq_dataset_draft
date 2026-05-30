# BLINQ v1 PDF Redaction Audit

This audit records the redacted PDFs supplied for blinded and counterfactual OpenAI PDF evaluation.

## Automated Checks Performed

- Confirmed the expected five redacted PDF filenames are present in the local redacted folder.
- Recorded SHA256 hashes and rough page counts in `data/release/pdf_manifest_v1.csv`.
- Confirmed redacted filenames use BLINQ paper-group identifiers rather than arXiv identifiers.

## Manual Checks Still Recommended

- Open each redacted PDF and verify that author names, affiliations, acknowledgements, arXiv IDs, journal metadata, and obvious self-identifying text are removed.
- Check PDF document properties in a PDF viewer before running final model evaluation.
- If any redaction issue is found, replace the PDF and regenerate the manifest so hashes update.

## Redacted PDF Records

| paper_group_id | filename | bytes | sha256 prefix |
|---|---|---:|---|
| BLINQ_QEC_001 | BLINQ_QEC_001.pdf | 2280005 | 09bf41456bb1 |
| BLINQ_QALG_002 | BLINQ_QALG_002.pdf | 720788 | 4bcfba16fce4 |
| BLINQ_QCOMM_003 | BLINQ_QCOMM_003.pdf | 893215 | 21d244b20a1f |
| BLINQ_QHW_004 | BLINQ_QHW_004.pdf | 2012177 | e50c86e2ae81 |
| BLINQ_QIT_005 | BLINQ_QIT_005.pdf | 10992339 | 1beddce95524 |
