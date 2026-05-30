# BLINQ v1 Schema

The canonical release dataset is `blinq_v1_items.jsonl`; the CSV version is a flattened convenience copy.

## Item Fields

- `item_id`: unique benchmark item id.
- `paper_group_id`: shared id linking the three metadata variants of the same underlying paper.
- `source_arxiv_id`: arXiv id for provenance; not shown in blinded prompts.
- `scientific_area`: fixed to `Quantum Information Science`.
- `subfield`: heuristic/manual QIS subfield.
- `paper_type`: broad paper-type label.
- `metadata_condition`: one of `blinded`, `real_metadata`, `counterfactual_high_prestige`.
- `prestige_condition`: one of `none`, `real`, `synthetic_high_prestige`.
- `source_materials`: title, abstract, curated methods/results summaries, figure note, and source notes.
- `metadata`: condition-specific author/affiliation metadata.
- `reference_answer`: aggregated human reference label.
- `evaluation_rubric`: metric names used by the benchmark.
- `source_urls`: arXiv abstract/PDF URLs for provenance.
- `pdf_input`: PDF condition and manifest linkage for OpenAI PDF evaluation.

## Reference Answer

`reference_answer` contains:

- `technical_soundness`
- `evidence_support`
- `novelty`
- `significance`
- `clarity`
- `overall_merit`
- `editorial_priority`
- `annotator_confidence`
- `included_reviewers`
- `discarded_familiarity_flagged`
- `priority_votes`
- `label_source`
- `aggregation_method`

Numeric dimensions are means over included human reviewers. Editorial priority is majority vote.

## PDF Manifest

`pdf_manifest_v1.csv` contains one `original_pdf` and one `redacted_pdf` record for each paper group. The repository tracks filenames, local source paths, SHA256 hashes, file sizes, rough page counts, and intended metadata conditions.
