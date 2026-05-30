# BLINQ v1 Reference Label Aggregation

Reference labels were aggregated from three human reviewer responses supplied for the BLINQ v1 release.

## Familiarity Exclusion Rule

Reviewers were asked to flag papers they had previously read, reviewed, or recognized. Rows with `reviewer_flagged_familiarity = yes` are excluded before aggregation. In the current release, no rows were flagged familiar.

## Aggregation Rule

- Numeric dimensions are reported as mean, median, and sample standard deviation across included reviewers.
- Editorial priority is the majority vote over `low`, `medium`, and `high`.
- Disagreement is reported when more than one priority label receives at least one vote.

## Final Reference Labels

| paper_group_id | included | discarded | tech | evidence | novelty | significance | clarity | overall | priority | votes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BLINQ_QEC_001 | 3 | 0 | 2.67 | 2.33 | 1.67 | 2.33 | 3.33 | 2.00 | low | low:2, medium:1, high:0 |
| BLINQ_QALG_002 | 3 | 0 | 4.00 | 4.00 | 4.00 | 3.33 | 4.33 | 3.67 | medium | low:0, medium:2, high:1 |
| BLINQ_QCOMM_003 | 3 | 0 | 4.33 | 4.33 | 3.67 | 3.67 | 4.33 | 4.00 | high | low:0, medium:1, high:2 |
| BLINQ_QHW_004 | 3 | 0 | 4.67 | 4.67 | 3.67 | 4.00 | 4.67 | 4.33 | high | low:0, medium:0, high:3 |
| BLINQ_QIT_005 | 3 | 0 | 4.33 | 4.33 | 5.00 | 4.67 | 4.00 | 4.33 | high | low:0, medium:0, high:3 |

## Disagreement Notes

- `BLINQ_QEC_001` has the largest reviewer disagreement and aggregates to `low`.
- `BLINQ_QALG_002` aggregates to `medium` with one high-priority vote.
- `BLINQ_QCOMM_003`, `BLINQ_QHW_004`, and `BLINQ_QIT_005` aggregate to `high`.

Raw reviewer rows: 15
Included reviewer rows: 15
Discarded familiarity-flagged rows: 0
