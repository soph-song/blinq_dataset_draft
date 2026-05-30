# Dataset Card: BLINQ v1

## Dataset Name

BLINQ v1: BLInd Review Benchmark for Quantum Information Science.

## Purpose

BLINQ v1 evaluates whether AI manuscript-review systems change their scientific assessment of the same quantum information science paper when metadata and prestige cues vary.

## Data Source

The five underlying papers come from arXiv `quant-ph` metadata collected through the official arXiv API. PDFs are tracked by local manifest for OpenAI PDF evaluation. The public release does not require committing full PDFs.

## Dataset Size

- 5 underlying papers.
- 3 metadata conditions per paper.
- 15 benchmark items.

## Metadata Conditions

- `blinded`: redacted PDF.
- `real_metadata`: original PDF.
- `counterfactual_high_prestige`: redacted PDF plus synthetic high-prestige metadata.

## Reference Labels

Reference labels are aggregated from three human reviewers. Rows flagged familiar by reviewers are discarded before aggregation. No rows were discarded in BLINQ v1.

## Intended Use

- Evaluating AI review score agreement with human reference labels.
- Measuring metadata sensitivity across linked paper variants.
- Measuring recognition/contamination risk with a separate model probe.

## Limitations

- Small v1 release.
- Human labels are from three reviewers.
- Redacted PDFs require manual audit before final model runs.
- The cached candidate pool contains 600 records because arXiv API calls were partially rate-limited.

## Ethical and Legal Considerations

Do not use BLINQ to rank real authors, labs, institutions, or individual papers. Counterfactual metadata is synthetic and only intended for controlled prestige-sensitivity testing. Full PDFs should not be publicly redistributed without checking rights and redaction quality.
