# Offline pre-production gate

No provider calls, credential reads, paid execution, prompt edits, golden edits, config refreeze, commit or 100k run were performed for this gate. Project ledger remains $0.770076985 accounted against $10. Owner approval of 20% fallback is recorded for future 100k execution, pending this prompt decision; current config remains 10%.

## Decision: (a) proceed with the frozen prompt

Recommend keeping Jev-v3, confidence 0.60, margin 0 and the current persistent flag rules. Hash remains `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`. The approved 20% operational fallback control does not change it. **No calibration or analysis_10000 redo is required: zero new calls, $0 API cost and zero rerun wall-clock time.** This is a recommendation at a gate, not approval to execute the 100k.

This is not a claim that the labels have no rule errors. Independent development evidence confirms generic criticism assigned severity 1: IDs `00363dc8` (“Worst”), `06a45bd5` (“Worst app”), `8216dafb` (“sucks”), among others. Contract lines 39 and 44 explicitly support complaint / severity 2; human review 3 independently preferred verifier severity 2 for “sucks”. Human review 6 preferred playback over billing for a Premium customer unable to play, directly supporting contract line 36. These are legitimate rule-based development problems, independent of golden answers.

However, frozen Jev-v3 already encodes generic criticism/minor annoyance as severity 2, praise/neutral/unclear/pure request as severity 1, and explicitly says paid-plan mention alone is not billing. No tested wording change has demonstrated improved compliance without regressions. The 20 human verdicts include all four intent judgments favoring Jev, cautioning against broader Luna-style reinterpretation. Rewriting prompts solely to fit golden disagreement patterns would be leakage, not a validated improvement. Keep these measured limitations visible. A future fix would require development-only A/B evidence and a fresh held-out human sample; golden cannot validate its own suggested revision.

## Golden audit is isolated

`docs/golden-error-analysis.md` lists every topic/intent/exact-severity disagreement (35 fields, 22 IDs), pipeline → golden, with pattern and explicit-rule versus judgment assessment. It uses saved evaluation comparisons, not the human label CSV. Golden differences are evaluation findings only. Several pipeline answers follow explicit contract rules despite disagreement; some are clear or likely pipeline errors. No owner label is rewritten.

## Development patterns, independent of golden answers

`pipeline/development_patterns.py` reads final-hash Jev results and the two existing blinded verifier cohorts, excludes golden IDs **and exact texts**, excludes incomplete/terminal predictions, and chooses one row per distinct exact text. Result: **975 unique development texts**. This module never reads golden answer files or golden evaluation reports. `docs/development-pattern-evidence.json` retains inspectable texts/predictions and all 20 field-specific human cases.

The following are **overlapping lexical screening counts**, not semantic error rates. Denominators include agreeing texts. A keyword match only shows where to inspect; it does not prove the named problem or that Jev is wrong. Parentheses list topic / intent / exact-severity disagreement counts, which can overlap within a text:

- General evaluation: 106/405 have a target-field disagreement (66 / 15 / 39).
- Ads: 51/136 (25 / 10 / 23).
- Billing/Premium: 61/129 (29 / 13 / 28).
- Songs/recommendations/lyrics/podcasts: 85/211 (40 / 24 / 36); deliberately broad song vocabulary, not 85 proven catalog errors.
- Mixed-issue language: 50/117 (26 / 14 / 23); “but” is a screen, not proof of multiple supported issues.
- Stored non-English/not-understood language: 28/75 (8 / 20 / 9); model language judgment, not human-validated translation.
- Blocked/restricted-function language: 32/83 (16 / 7 / 12).
- Feature-request language: 25/53 (9 / 12 / 10).
- Boycott/unrelated vocabulary: 2/8 (0 / 1 / 1).
- Historical-resolution vocabulary: 1/1 (1 / 0 / 0); no independent human case and no explicit temporal-precedence contract rule.
- Other: 80/244 (31 / 29 / 39).

Manual cross-check of the independent human judgments: review 1 supported other over an inferred usability defect; review 6 supported playback despite Premium mention; reviews 11 and 16 preferred catalog for podcast/mixes mentions; review 3 confirmed the generic-criticism severity issue; review 8 preferred severity 3 rather than 4 for offline failure. Reviews 13 and 18 found both proposed severities wrong; these provide no corrected numeric target. Review 13's Hindi ad complaint and review 14's colloquial “Thik thak” also demonstrate non-English interpretation problems, but their verdicts apply only to severity and sentiment respectively, not translation/topic. Four needs_review judgments favored verifier false; expanding fallback cannot remove mandatory persistent missing-context/language signals and is not a flag-rule fix. Do not count a verdict on one field as correctness of all fields.

**Dependence caveat:** verifier and fallback are the **same Luna model**, using different blinded prompts. The verifier does not see Jev labels, but that is input independence, not model independence. The reported 82/115 → 51/115 disagreement reduction is partly self-agreement, not evidence of that much human-accuracy gain. The 20 owner verdicts are independent human evidence but are stratified disagreements, not a representative accuracy sample. Keep the already-approved 20% as a bounded operating choice, with no promised accuracy gain. No new routing evidence was extracted from golden labels.

## Eight-worker graceful stop implementation

`pipeline/graceful.py` wraps a prepared store and supplied Calls object; `python -m pipeline scope-run --plan PATH` is offline by default. Paid execution requires `--confirm-spend`, a concrete plan with execution approval and verified preflight, a matching frozen hash and an existing prepared state. The draft explicitly fails paid execution. No production store has been prepared or dispatched at this gate.

The stop watcher observes `OUTPUT/stop.request`, stops claiming new work, and lets already admitted requests, their bounded repairs/retries, validation and commits finish. It does **not** set the hard-failure Calls.stop event. No fallback selection is persisted from an unfinished Jev scoring pass. Existing fully persisted selection is reused after a voluntary pause. After draining, it writes immutable per-segment receipts plus `stop-receipt.json`; a drained user request is renamed to a segment-specific acknowledgement. Pending leases or reservations make the receipt `recovery_required`, not a safe user pause.

Resume preserves the same invocation ID/cap/fallback fraction/hash, saved stage results, attempt logs and separate classification/terminal/connection health windows. The SQLite ledger therefore sums spend across segments; it does not allocate a fresh cap. Budget latches cannot be cleared by the wrapper. Only a clean `stopped_user` state resumes through this path; a cap, integrity, auth or systemic failure requires its own gate/recovery. Stale requests and changed cap/config are rejected. All hard errors still drain executor work before the receipt and propagate as failures.

Regression tests exercise an eight-worker pause during Jev scoring, pause during routed completion, completion of a permitted repair after the stop request, unchanged selection, no resumed calls for completed IDs, saved health history, shared cap latching, stale request rejection, changed-cap rejection and offline/draft dispatch guards. All transports are mocked; no production throughput is inferred from tests. The older one-worker `stop_after` remains separate.

The 100k source selection/import, concrete approved plan, preflight receipts and local commit are still required before starting; the wrapper intentionally requires a prepared store rather than silently ingesting all source rows. See `docs/100k-run-plan-draft.md` for recording and checkpoint proof commands.

## Updated preflight and caching

User-reported figures: TypeSafe balance **$10.41**; OpenAI October spend **$0.18** against a $20 org limit, with **$9.82 prepaid credit**. Effective available OpenAI funds before unposted liabilities are min($19.82 org headroom, $9.82 credit) = **$9.82**. Recheck balances, unbilled usage and concurrent spend before execution. No dashboard reconciliation was performed. The separate project ledger is authoritative for the $10 project cap.

The unchanged 20% production estimate remains $4.852176 base / 1.89 hours, with a **proposed**, not yet approved, $7.28 shared invocation cap. Expected provider split: TypeSafe $3.705730, OpenAI $1.146446. At the entire invocation ceiling, project total would be $8.050076985. Disk is remeasured in the draft JSON; require 10 GiB free as an explicitly conservative allowance.

OpenAI's owner-reported prompt-cache hit rate is **0%**. Cache benefits reported by this project mean the exact-text **result cache** keyed by text hash and label_config, plus persisted stage reuse during resume. No provider prompt-cache savings are claimed, projected or implemented here. Existing conservative cache-write pricing in reservation bounds is a safety envelope, not evidence of prompt-cache use.

Stop at this gate. The prompt is unchanged; 20% is approved for the future 100k routing tranche but not applied to current config. No paid run is authorized by this offline work.

Validation: **154 pytest tests passed**; `ruff check pipeline tests` passed. Six new
graceful-wrapper regression tests use mock transports, including all eight workers
and an in-flight repair. Draft CLI inspection made no calls and confirmed paid
execution is disabled. Frozen hash matches; actual fallback control remains 0.10;
ledger still shows 770076985 nanodollars spent and zero reserved. Exclusions verified
for .env, full raw CSV, private notes and golden backup; tracked check showed only
.env.example. No private notes were opened and no commit/push was performed.
