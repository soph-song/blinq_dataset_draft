# BLINQ v1 Human Annotation Protocol

Human reviewers evaluate redacted manuscript packets based only on scientific content.

## Reviewer Instructions

Reviewers should not search online, identify authors, infer institutions, or use prestige as evidence of quality. Before scoring, reviewers answer:

```text
Have you previously read this paper, reviewed this paper, seen this work before, or do you recognize the likely authors, lab, institution, or research group?
```

Allowed answers:

- `yes`
- `no`

Rows with `yes` are discarded before final reference-label aggregation.

## Scores

Each included review supplies 1-5 scores for:

- `technical_soundness`
- `evidence_support`
- `novelty`
- `significance`
- `clarity`
- `overall_merit`

Reviewers also provide:

- `editorial_priority`: `high`, `medium`, or `low`
- `annotator_confidence`: 1-5
- `rationale`
- `evidence_spans_or_phrases`

## Aggregation

- Familiarity-flagged rows are excluded.
- Numeric dimensions are averaged across included reviewers.
- Medians and sample standard deviations are retained.
- Editorial priority is majority vote.
- Disagreement is flagged when multiple priority labels receive votes.
