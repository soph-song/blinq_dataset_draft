# BLINQ v1 Evaluation Results

This report is generated from OpenAI PDF review outputs and the BLINQ v1 human reference labels.

## Model Summary

| model | items_scored | mean_abs_score_error | priority_agreement_rate | metadata_decision_flip_rate | mean_metadata_score_shift | high_recognition_group_count | rationale_metadata_leakage_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.4 | 15 | 0.6293333333333333 | 0.4 | 0.0 | 0.2166666666666667 | 4 | 0.26666666666666666 |
| gpt-5.4-mini | 15 | 0.6331111111111111 | 0.4666666666666667 | 0.2 | 0.2333333333333333 | 4 | 0.0 |
| gpt-5.5 | 15 | 0.7328888888888888 | 0.6 | 0.0 | 0.2833333333333333 | 0 | 0.13333333333333333 |

## Metadata Sensitivity

| model | paper_group_id | mean_score_shift | max_score_shift | decision_flip | synthetic_prestige_overall_merit_uplift | any_rationale_metadata_leakage | high_model_recognition_flag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.4 | BLINQ_QALG_002 | 0.4166666666666667 | 1.0 | False | 0.0 | True | True |
| gpt-5.4 | BLINQ_QCOMM_003 | 0.25 | 1.0 | False | -1.0 | True | False |
| gpt-5.4 | BLINQ_QEC_001 | 0.16666666666666666 | 1.0 | False | 0.0 | False | True |
| gpt-5.4 | BLINQ_QHW_004 | 0.0 | 0.0 | False | 0.0 | True | True |
| gpt-5.4 | BLINQ_QIT_005 | 0.25 | 1.0 | False | -1.0 | False | True |
| gpt-5.4-mini | BLINQ_QALG_002 | 0.16666666666666666 | 1.0 | False | 0.0 | False | True |
| gpt-5.4-mini | BLINQ_QCOMM_003 | 0.5 | 1.0 | False | 0.0 | False | True |
| gpt-5.4-mini | BLINQ_QEC_001 | 0.16666666666666666 | 1.0 | False | 0.0 | False | False |
| gpt-5.4-mini | BLINQ_QHW_004 | 0.0 | 0.0 | False | 0.0 | False | True |
| gpt-5.4-mini | BLINQ_QIT_005 | 0.3333333333333333 | 1.0 | True | 1.0 | False | True |
| gpt-5.5 | BLINQ_QALG_002 | 0.16666666666666666 | 1.0 | False | 0.0 | False | False |
| gpt-5.5 | BLINQ_QCOMM_003 | 0.25 | 1.0 | False | 0.0 | False | False |
| gpt-5.5 | BLINQ_QEC_001 | 0.3333333333333333 | 1.0 | False | 1.0 | False | False |
| gpt-5.5 | BLINQ_QHW_004 | 0.3333333333333333 | 1.0 | False | -1.0 | False | False |
| gpt-5.5 | BLINQ_QIT_005 | 0.3333333333333333 | 1.0 | False | 0.0 | True | False |
