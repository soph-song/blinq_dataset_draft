# Dataset Card: BLINQ Pilot Dataset Draft v1

## Dataset Name

BLINQ pilot dataset draft v1.

## Purpose

BLINQ is a benchmark draft for studying whether AI-assisted manuscript reviewers evaluate quantum information science manuscripts based on scientific content or are influenced by prestige cues such as author names and institutional affiliations.

## Data Source

Candidate papers are collected from the official arXiv API endpoint `https://export.arxiv.org/api/query` using the broad `quant-ph` category. The draft stores metadata fields only: title, abstract, authors, categories, comments, journal reference, DOI, abstract URL, and PDF URL.

## Collection Procedure

The collection script queries years 2018 through 2026 using year-stratified submitted-date windows. It fetches approximately 150 records per year, deduplicates by arXiv id, and samples exactly 1000 candidates with `RANDOM_SEED = 209` when enough unique records are available. The script waits at least three seconds between repeated API calls.

## Screening Procedure

The screening script samples 100 candidate papers with `RANDOM_SEED = 209` and applies transparent keyword heuristics over title and abstract. Labels are `in_scope`, `borderline`, and `out_of_scope`. These are draft heuristic labels and must be manually checked before any scientific claims are made.

## Item Construction

The pilot builder selects five underlying papers, preferring in-scope QIS papers and attempting to cover at least four QIS subfields. Each selected paper is represented under three linked metadata conditions: `blinded`, `real_metadata`, and `counterfactual_high_prestige`. Counterfactual metadata uses clearly synthetic labels and is not real attribution.

## Intended Use

This draft is intended for class-project prototyping, benchmark design review, and pilot model-evaluation experiments focused on metadata sensitivity in manuscript review.

## Limitations

The pilot uses title and abstract only. Methods and results excerpts are placeholders pending manual extraction. QIS screening labels are heuristic, not expert labels. Human reference answers are initialized as `TBD_human_annotation`. Real affiliations are not extracted automatically. The arXiv `quant-ph` category is broader than QIS.

## Ethical and Legal Considerations

The dataset should not be used to rank real authors, institutions, or papers. Counterfactual prestige metadata is synthetic and must be presented as synthetic. The draft avoids redistributing full PDFs and uses arXiv metadata and URLs. Any downstream analysis should focus on model behavior, not claims about individual researchers.

## Current Status

Draft only. This is not a final expert-labeled dataset.
