# BLINQ v1 Release Summary

BLINQ v1 is a 15-item benchmark release for studying metadata and prestige sensitivity in AI manuscript review for quantum information science.

## Release Contents

- Benchmark items: 15
- Underlying papers: 5
- Metadata conditions per paper: blinded, real_metadata, counterfactual_high_prestige
- Human reviewers used for reference labels: 3
- PDF manifest records: 10

## Final Editorial Priorities

- BLINQ_QEC_001: low (low:2, medium:1, high:0)
- BLINQ_QALG_002: medium (low:0, medium:2, high:1)
- BLINQ_QCOMM_003: high (low:0, medium:1, high:2)
- BLINQ_QHW_004: high (low:0, medium:0, high:3)
- BLINQ_QIT_005: high (low:0, medium:0, high:3)

## Known Limitations

- The release is intentionally small: 5 papers x 3 metadata conditions.
- Reference labels are aggregated from three human reviewers, not a large expert panel.
- PDF files are tracked by manifest and local access instructions; public redistribution should be checked before committing PDFs.
- Candidate-pool collection reached 600 arXiv records in the cached run because older-year API calls hit timeouts/rate limits.
- OpenAI model evaluations require user-supplied API access and are not run during release-file generation.
