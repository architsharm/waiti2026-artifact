# Per-row detector decisions: WAITI 2026

This is the data release for the paper *No Tier Wins Everywhere: Benchmarking Rules, Classifiers, a
Judgment Model and an LLM as Security Detectors for AI Agents* (Archit Sharma and Garima Mann, Nometria
Inc; WAITI 2026, workshop at ACSAC 2026). The system under test is
[AgentFox](https://github.com/architsharm/agentfox).

For every dataset row the paper scores, it gives the gold label and the decision of each tier whose
per-row outputs we can redistribute. The tiers in the paper are code (parser, patterns, rules or native
detector), PIGuard, ProtectAI DeBERTa-v3 v2, the judgment model (Jev, a hosted model from TypeSafe) and
the LLM (Claude Haiku 4.5). Each row also has the dev/test half used for threshold selection and, for
the injection sets, whether the row is in PIGuard's released training data.

**Per-row outputs of the hosted judgment model are not redistributed; aggregate results are in
`aggregates/`.** Its provider's terms do not clearly permit redistributing its outputs, so its scores
and verdicts are left out of every row file. Its per-dataset counts, rates, AUROCs, thresholds and
calibration results are in `aggregates/camera_ready.json` and the other aggregate files.

**No dataset text is included.** Rows are identified by the dataset's own ID where it has one.
Otherwise they are identified by the 0-based index in the exact source file plus that file's path,
and always by a SHA-256 of the row's text, so you can join the rows to your own copy. The source paths
refer to files in the [AgentFox repository](https://github.com/architsharm/agentfox) at commit
`723fcec`, which the paper's numbers were built from, or to the upstream release named (see
[Sources](#sources-and-licences)).

Run the check to confirm the release reproduces the paper:

```
python3 verify.py     # standard library only
```

It recomputes the paper's headline numbers from `rows/` and compares them with `paper_numbers.tex` (a
copy of the paper's generated macros) and with the per-dataset cells of `aggregates/camera_ready.json`,
the file the appendix tables are generated from. At release it prints `125 checks passed, 0 failed`.
The numbers recomputed from rows include:

- the SQL parser's counts and the AgentDojo counts;
- PIGuard and ProtectAI on NotInject and the external injection sets;
- the training-overlap counts;
- from the recomputed classifier scores: agreement with the stored flags, pooled and per-set AUROC, and TPR at 1% FPR;
- per-suite provenance totals against the summary file (aggregate level only);
- the wording-check macros against `aggregates/prompt_sensitivity.json` (aggregate level only);
- the PII counts and the native detector's rates;
- the LLM's SafePyramid accuracies by level;
- tp/pos/fp/neg for every released code, classifier and LLM cell of Table 7.

For the judgment model the checks are at the aggregate level: every judgment-model cell of
`camera_ready.json` must have the row count and positive/negative split of the released labels (and of
the released dev/test halves for SQL, agent actions, PII and policy rules), and the paper's
judgment-model numbers (SQL false positives, AUROCs, thresholds, PII and entitlement rates, ATBench
AUROCs) must equal those cells.

## Layout

| Path | What |
|---|---|
| `rows/*.jsonl` (`.jsonl.gz` above 5 MB) | One file per dataset, one JSON object per row |
| `aggregates/` | Numbers the paper reports where per-row data is not released (all judgment-model results) or was not stored, and the analysis outputs the tables are generated from (no text) |
| `audit/` | Appendix B, the SQL label audit: blind labels and notes (produced by an LLM coding assistant, as the paper discloses), the audit-id to row key, the result, and the sampling and scoring scripts. The blind sheet with the sampled SQL text is not included; `sql_audit_sample.py` rebuilds it from `benchmarks/action_safety/data/action_safety.json` in AgentFox at `723fcec` |
| `prompts.json` | Every judgment-model question and the LLM's policy-rule prompt, verbatim (our prompts) |
| `paper_numbers.tex` | The paper's generated numbers, as built |
| `manifest.json` | Row count, size and SHA-256 of every row file; the excluded datasets |
| `verify.py` | Recomputes headline numbers and checks them against the paper |
| `build_release.py` | The script that produced `rows/` from our result files, for reference. Some of its inputs (our raw result files, which include the judgment model's per-row outputs, and the third-party corpora below) are not in this repository; regenerating twice gives byte-identical files |
| `LICENSE` | Licence for our files; see [Licence](#licence) |
| `CITATION.cff` | How to cite the paper |

## Mapping to the paper

| Paper | Files |
|---|---|
| Table 1 (datasets) | row counts in `manifest.json` |
| Sec. 3.1, SQL; Table 7 rows 1-2 | `gretel_text_to_sql`, `payload_box`; `aggregates/sql_question_alignment.json`, `aggregates/sql_disagreement_taxonomy.json` |
| Appendix B (SQL label audit) | `audit/`; its key maps to `row_key` in `gretel_text_to_sql` |
| Sec. 3.2, AgentDojo; Table 7 row 3 | `agentdojo` (use `in_paper_unique_calls`), `aggregates/agentdojo_inferred_provenance_summary.json` |
| Table 3 (provenance by suite) | `aggregates/provenance_suites.json` (recomputed from the per-call decisions of the replay at `723fcec`; the per-call decisions themselves are not in this release) |
| Table 4 (injection tiers on identical rows) | `adaptive_attempts` (the 165 rows with `escaped_shipped_detectors`), `notinject`, `aggregates/injection_table.json` |
| Table 5 (external injection sets), Sec. 3.3 overlap and recomputed scores, Appendix C | `deepset`, `spml`, `yanismiraoui`, `trustairlab`, `notinject`; `aggregates/classifier_overlap.json`, `aggregates/dedup_injection.json`, `aggregates/classifier_scores.json` |
| Sec. 3.4, answerability, PII, entitlement | `kuq`, `presidio`, `gretel_pii`, `tab`, `privacylens` |
| Sec. 3.5, policy rules; Table 12 | `safepyramid` (one row per case and rule); `aggregates/camera_ready.json` under `policy_roles` |
| Sec. 3.6, trajectories; Fig. 1 | `atbench`, `atbench500`, `atbench_claw` (labels); judgment-model results in `aggregates/camera_ready.json` |
| Commitments | `refund_replies` |
| Table 7 (every dataset and tier), Tables 8 to 10, Fig. 2 |
| Table 11 and Sec. 7 (judgment-model wording check) | `prompt_paraphrases.json` (paraphrases and sample, stated before scoring), `aggregates/prompt_sensitivity.json`, `aggregates/prompt_sensitivity_ledger.json` (calls and cost); per-row outputs of this run are not released | all of the above; `aggregates/camera_ready.json`, `aggregates/calibration_split.json` |

**What is not per row.** All judgment-model results are aggregates only (see above), so the
`privacylens`, `atbench`, `atbench500`, `atbench_claw` and `refund_replies` files carry labels,
identifiers and halves but no judgment-model decision. In Table 4, per-row decisions exist only for the
shipped pattern detectors (on the escapes) and for PIGuard and ProtectAI on NotInject (from the
external-set run). The classifiers' and ensemble's decisions on the 165 escapes and the 467 held-out
benign prompts were stored only as counts. Those counts, and the judgment model's, are in
`aggregates/injection_table.json`.

The provenance results on AgentDojo were stored as task- and pair-level counts
(`aggregates/agentdojo_inferred_provenance_summary.json`). The per-call `provenance_replay` field
comes from the separate ground-truth replay of the 617 calls. The ensemble (PIGuard plus ProtectAI
at 0.92) needs ProtectAI's score, but the classifiers' outputs were stored as labels, so the ensemble
has no per-row column. In `aggregates/sql_disagreement_taxonomy.json` the individual example rows the
judgment model missed are replaced by their count (`other_examples_n`).

## Text hash

`text_sha256` is the SHA-256 of the UTF-8 bytes of `normalise(x)`:

```python
def normalise(x):
    if not isinstance(x, str):   # structured rows: canonical JSON
        x = json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    x = unicodedata.normalize("NFC", x).replace("\r\n", "\n").replace("\r", "\n")
    return x.strip()
```

Here `x` is the field below, taken as stored in the source file (after `json.load`):

| File | Hashed field |
|---|---|
| `gretel_text_to_sql` | `sql` (the statement as evaluated); `source_sql_sha256` hashes the original gretel statement a variant was derived from |
| `payload_box` | `value` |
| `agentdojo` | `{"function": ..., "args": ...}` of the call |
| injection sets | `text` |
| `adaptive_attempts` | `payload` |
| `kuq` | `question` |
| `presidio` / `gretel_pii` / `tab` | `full_text` / `text` / `text` |
| `privacylens` | `trajectory` |
| `safepyramid` | the case's `conversation` |
| `atbench` / `atbench500` / `atbench_claw` | `contents` / `content` / `trajectory` |
| `refund_replies` | `answer` |

## Fields

Common to every row:

| Field | Meaning |
|---|---|
| `dataset` | file name |
| `row_key` | the ID our result files use; unique within the file |
| `source_id` | the dataset's own ID where it has one (TAB `doc_id`, PrivacyLens `name`, AgentDojo suite/task/function, SafePyramid case `id`, ATBench `id`, ATBench500 `conv_id`), else `null` |
| `source_path`, `source_index` | file (in AgentFox at `723fcec`, or the upstream release named) and 0-based index in it |
| `text_sha256` | see above |
| `label` | gold label as standardised in the paper: `true` = should be flagged (Table 7 says what positive means per dataset) |
| `calib_split` | `dev` or `test`: the random half (seed 11) used to choose a judgment-model threshold (`dev`) and report it (`test`), per decision kind; `null` where no threshold is chosen. Policy rules are split by conversation |

Tier columns (present where the tier applies):

| Field | Tier |
|---|---|
| `code_parser_flag` | SQL parser / tool-call argument checks (SQL, payload-box, AgentDojo) |
| `code_patterns_flag` | shipped injection pattern detectors |
| `code_shipped_flag`, `escaped_shipped_detectors` | shipped detectors on adaptive attempts (escaped = not flagged) |
| `code_rules_flag` | shipped answerability rules |
| `code_native_flag` | shipped native PII detector |
| `code_authorised` | the refund rule computed from the request |
| `piguard_flag`, `protectai_flag` | the open classifiers at their shipped thresholds, as stored by the original run |
| `piguard_score_recomputed`, `protectai_score_recomputed` | injection-class probability recomputed after the run with the shipped adapter's input handling (first 4,000 characters, local model files, six decimals); at 0.5 it reproduces the stored flag on 5,342 (PIGuard) and 5,341 (ProtectAI) of 5,345 rows; `aggregates/classifier_scores.json` lists the others |
| `llm_flag` | Claude Haiku 4.5 says this rule is violated (SafePyramid 600-conversation subset only) |
| `provenance_replay` | AgentDojo: tool impact class and the capability-policy verdict in the ground-truth replay, detectors off and on |
| `in_piguard_train`, `in_jackhhao_train` | row text, normalised (NFKC, lower case, non-word runs to one space), occurs in PIGuard's released `datasets/train.json` (sha256 `806ded8bd85782a53d34faffe4fd92b3f2e0b3b431c43578ce77faea6b9ed911`), or in its `jailbreak-classification` part, which ProtectAI's card also lists |

There is no judgment-model column (no `jev_*` field) in any row file.

Dataset-specific fields:

| Dataset | Fields |
|---|---|
| `gretel_text_to_sql` | `gretel_split` (train/test of our split), `variant` (`natural_dml`, `natural_ddl`, `adversarial_tautology`, `adversarial_unbounded`; the adversarial variants are our rewrites of gretel statements) |
| `payload_box` | `primary_source`, `authored_by_us` (the negatives are values we wrote) |
| `agentdojo` | `source_list` (`injection` or `user`), `in_paper_unique_calls` (the 384 unique calls of the paper; the file lists each task once per AgentDojo version) |
| `deepset` | `deepset_split` |
| `adaptive_attempts` | `seed_id`, `attempt`, `surface`, `semantics`, `payload_sha16` |
| `kuq` | `label_category` (KUQ category) |
| PII | `types_present`, `has_any_labelled_span`, `in_paper_table` (positives, plus negatives with no labelled span of any type) |
| `safepyramid` | `rule`, `level`, `domain`, `rule_role` (from the SafePyramid rubric), `in_600_subset` (the subset used for the judgment-vs-LLM comparison), `llm_flag` |
| trajectories | `risk_source` (dataset field) |
| `refund_replies` | `template`, `request` (generated parameters) |

## Thresholds and calibration

- **Code and classifiers:** fixed. Code has no threshold; PIGuard and ProtectAI run at their shipped
  threshold, and their outputs were stored as labels.
- **Judgment model:** default 0.5. For each decision kind, a threshold was also chosen on the `dev`
  half and reported on the `test` half. The choice maximises Youden's J (TPR minus FPR) over the grid
  0.01 to 0.99, with ties going to the lowest threshold. A second threshold was chosen as the lowest
  grid value whose dev FPR is at most 1%. The halves are released per row (`calib_split`); the
  results are aggregates.
- **Thresholds chosen on dev (Youden):** SQL 0.81, agent actions 0.34, answerability 0.67, PII 0.95,
  trajectories 0.38, policy rules 0.45. Their range over 20 random splits, the test
  recall/FPR/precision and the test ECE are in `aggregates/camera_ready.json` under `thresholds`.
- **Leakage:** no threshold is selected on the rows it is scored on, and nothing is trained. The
  judgment model's injection question was chosen on NotInject (paper Sec. 3.3).
- **Excluded rows:** the dev halves in this release were drawn over the full sets, including the
  CoCoNot and R-Judge rows that are not released (see below).

## Sources and licences

Licences were checked on the dataset card or repository on 2026-10-23. Per-row labels and decisions
keyed by row index, with no text, are redistributed under each source's terms. Attribute the source
when you use its rows.

| File | Source | Licence | Path in AgentFox at `723fcec` |
|---|---|---|---|
| `gretel_text_to_sql` | [gretelai/synthetic_text_to_sql](https://huggingface.co/datasets/gretelai/synthetic_text_to_sql) | Apache-2.0 | `benchmarks/action_safety/results/*_predictions.json` (built from `benchmarks/action_safety/data/action_safety.json`) |
| `payload_box` | [payload-box/sql-injection-payload-list](https://github.com/payload-box/sql-injection-payload-list); negatives ours | MIT | `benchmarks/action_safety/results/payloadbox_*_predictions.json` |
| `agentdojo` | [ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo) v1.2.2 | MIT | `benchmarks/action_safety/data/agentdojo_calls.json` |
| `deepset` | [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) | Apache-2.0 | `benchmarks/data/{train,test}.json` |
| `spml` | [reshabhs/SPML_Chatbot_Prompt_Injection](https://huggingface.co/datasets/reshabhs/SPML_Chatbot_Prompt_Injection) | MIT | `benchmarks/data_generalization/spml_sample.json` |
| `yanismiraoui` | [yanismiraoui/prompt_injections](https://huggingface.co/datasets/yanismiraoui/prompt_injections) | Apache-2.0 | `benchmarks/data_generalization/yanismiraoui.json` |
| `trustairlab` | [TrustAIRLab/in-the-wild-jailbreak-prompts](https://huggingface.co/datasets/TrustAIRLab/in-the-wild-jailbreak-prompts) | MIT | `benchmarks/data_generalization/trustairlab.json` |
| `notinject` | [leolee99/NotInject](https://huggingface.co/datasets/leolee99/NotInject) | MIT | `benchmarks/data_generalization/notinject.json` |
| `adaptive_attempts` | ours (adaptive attacker output) | CC BY 4.0 (see [Licence](#licence)) | `benchmarks/adaptive/results/adaptive_attempts.json` |
| `kuq` | [amayuelas/KUQ](https://huggingface.co/datasets/amayuelas/KUQ) | MIT | `benchmarks/answerability/data/kuq.json` |
| `presidio` | [presidio-research](https://github.com/data-privacy-stack/presidio-research) `data/synth_dataset_v2.json` | MIT (the fake identities in its text are CC BY-SA 3.0 US; no text is included here) | `benchmarks/pii/data/synth_dataset_v2.json` |
| `gretel_pii` | [gretelai/synthetic_pii_finance_multilingual](https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual) | Apache-2.0 | `benchmarks/pii/data/gretel_multilingual_pii.json` |
| `tab` | [NorskRegnesentral/text-anonymization-benchmark](https://github.com/NorskRegnesentral/text-anonymization-benchmark) | MIT | `benchmarks/pii/data/tab_echr_test.json` |
| `privacylens` | [SALT-NLP/PrivacyLens](https://github.com/SALT-NLP/PrivacyLens) | MIT (GitHub); CC-BY-4.0 (Hugging Face card) | `benchmarks/entitlement/data/privacylens.json` |
| `safepyramid` | [ByteDance/SafePyramid](https://huggingface.co/datasets/ByteDance/SafePyramid) v1.1 `benchmark.json` | CC-BY-4.0 | not in AgentFox (third-party corpus; sha256 of the copy used `eb4059a80e4d4dcc08d71fa258407caf8cd8b10865f0eae2741d23958d5d3639`) |
| `atbench`, `atbench500` | [AI45Research/ATBench](https://huggingface.co/datasets/AI45Research/ATBench) (test split; ATBench500 release) | Apache-2.0 | not in AgentFox (sha256 of the copies used: test `80c534b5f3517c872b528a2e6b64e34495206968edd184f4aed563d39f0cca09`, ATBench500 `031285443c6b8ca64fc117bd995a4b4490c340467136506763aeed1b23c8f34c`) |
| `atbench_claw` | [AI45Research/ATBench-Claw](https://huggingface.co/datasets/AI45Research/ATBench-Claw) | Apache-2.0 | not in AgentFox (sha256 of the copy used `bc04db0db900fd63ac4c59ba651584be2dc8dbd51861c98ffeb21f13c9495c8b`) |
| `refund_replies` | ours (generated from templates; no personal data) | CC BY 4.0 (see [Licence](#licence)) | `benchmarks/judgment/data/jev_corpus.json` |

**Not released per row:**

- **CoCoNot** ([allenai/coconot](https://huggingface.co/datasets/allenai/coconot), 379 rows). The card
  names two different data licences: the AI2 ImpACT Low-Risk licence, whose linked text no longer
  resolves, and ODC-BY. Until that is clarified we do not redistribute derived rows.
- **R-Judge** ([Lordog/R-Judge](https://github.com/Lordog/R-Judge), 571 rows). The repository has no
  licence, so nothing grants redistribution.

The paper's aggregate numbers for both (Table 7, `aggregates/camera_ready.json`) are unchanged. The
dev/test halves of the answerability and trajectory kinds include their rows, so a recomputation from
this release alone covers KUQ and the three ATBench corpora only.

## Prompts

`prompts.json` holds the judgment model's questions for every decision kind and the LLM's policy-rule
prompt, as extracted from the run scripts and the detector source at AgentFox `723fcec`. Appendix D of
the paper prints the two policy-rule prompts.

## Licence

Our own files are released under two licences (full text in `LICENSE`):

- **Scripts** (`verify.py`, `build_release.py`, `audit/*.py`): MIT.
- **Data and documentation we created** (this README, `prompts.json`, `paper_numbers.tex`,
  `manifest.json`, `aggregates/`, the `audit/` labels, notes and results, and the rows of
  `adaptive_attempts` and `refund_replies`): CC BY 4.0.

Labels and other fields derived from third-party datasets remain under those datasets' licences, as
listed in [Sources and licences](#sources-and-licences); our licence covers only our own contribution
(identifiers, hashes, our detectors' decisions and our annotations). Attribute both us and the source
dataset when you use them.

## Citation

See `CITATION.cff`, or:

```
Archit Sharma and Garima Mann. No Tier Wins Everywhere: Benchmarking Rules, Classifiers, a Judgment
Model and an LLM as Security Detectors for AI Agents. In WAITI 2026, workshop at ACSAC 2026, 2026.
```
