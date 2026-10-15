# Human-accuracy gate — completed prediction/evaluation and verdicts

Frozen config remains `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`. The original cost proposal below was prepared without human-label access. Subsequently approved collection completed all 50 predictions for $0.002603841, followed by evaluation-only comparison; all 20 development verdicts are saved. See `docs/golden-final-evaluation-gate.md` for current measured results. The 100k run remains draft-only. Golden source IDs/texts come from the unchanged, unlabeled `data/golden_50_to_label.csv` only.

## Original golden prediction cost proposal (executed after approval)

There are 50 IDs / 49 distinct texts. Six IDs (five distinct texts) reuse completed final-hash results from analysis by exact text. Forty-four IDs need 44 new distinct-text Jev classifications. Three new texts are long; frozen 10% fallback quota is four, so at most seven unique texts need Luna extraction/fallback (overlap reduces this). No new verifier, group or memo calls.

Worst-case reservations at the pinned planning rates: Jev **$0.045916248**, Luna **$0.029639500**, total **$0.075555748**. The proposed invocation cap equals that total. Conservative maximum is 176 Jev attempts + 28 Luna singleton attempts = **204 requests**, including up to four total calls per item/stage (max three uncertain attempts and one permitted output repair within the total limit). Initial calls: 44 Jev plus up to seven Luna input IDs, normally batched where possible. Bounds use UTF-8 bytes + protocol overhead + repair allowance, and the highest input/cache-write rate; no unmeasured cache discount.

Use eight workers, per-worker persistent HTTPS, 15s connect/60s read timeouts, shared rate/spend controls and the existing terminal/systemic policy. Result-cache reuse/imported provenance is not logged as new paid work. New golden results will also be reusable by the future 100k run under this unchanged hash. Current project spend $0.767473144; maximum after this proposal $0.843028892 / $10. Future 100k is separately gated.

Actual implemented commands (collection is complete; do **not** repeat the paid command):

```powershell
# Offline plan only, no human-label access or paid calls:
.venv/Scripts/python.exe -m pipeline golden-predictions

# Only after the owner approves this exact proposal:
.venv/Scripts/python.exe -m pipeline golden-predictions --approved-plan docs/golden-final-proposal.json --confirm-spend

# Only after prediction collection reaches its gate; offline evaluation-only reader:
.venv/Scripts/python.exe -m pipeline evaluate-golden
```

After approved prediction collection, save the 50-ID prediction/status snapshot, its hash and call evidence. Only then does evaluation code validate/read `evals/golden_50_human.csv`. It writes `evals/golden-final-evaluation/report.json` with agreement numerator/denominator, missing counts, per-ID disagreements, severity MAE and sentiment MAE/tolerance. Confusion CSVs cover topic, intent, severity 1–5, severity within ±1, sentiment negative/neutral/positive, and needs_review false/true (human rows / prediction columns, explicit missing column). All 50 remain in agreement denominators, including terminal/missing predictions. MAE reports its available-prediction denominator separately. No threshold, prompt, routing, model, or hash revision follows automatically from results.

**Entities are excluded:** they were not hand-labeled; empty arrays are by design. Exact-substring quote validation is not semantic quote-support accuracy. Four golden labels were revised after an AI-assisted check against contract rules; the final labels are the owner's decisions, as already disclosed in README.

## Interactive verifier disagreement review — zero API cost

The implemented command uses final-hash operational Jev labels before fallback versus the already blinded checkpoint verifier. It excludes golden IDs **and exact golden texts**, plus terminal records. Selection is deterministic by field strata, one text per case: 20 cases, four each for topic, intent, severity exact, sentiment sign and needs_review. Other disagreements are shown for context; the verdict concerns the displayed target field only. No model output is treated as human truth.

```powershell
.venv/Scripts/python.exe -m pipeline review-disagreements
```

For each review, the command displays the original text and Jev/verifier labels, then accepts `1`/`Jev right`, `2`/`verifier right`, `3`/`both wrong`, or `4`/`unclear`. `q`, EOF or Ctrl+C stops safely without saving an unfinished answer. Each completed verdict is atomically saved in `evals/verifier-human-review.json`; rerun the same command to resume. The sibling `evals/verifier-human-review-summary.json` reports selected/reviewed/remaining counts and verdict totals overall/by field. A lock prevents concurrent writers. It makes no API calls and never changes records, golden answers or the frozen config.

For chat-assisted review, `--next` shows one pending case without answering; `--verdict ... --case-id ...` saves only that exact pending case and rejects stale answers. Chat review has started; consult the saved summary for the live reviewed/remaining counts. Do not interpret unanswered or preselected UI options as verdicts. The final summary is a stratified disagreement-only adjudication, **not corpus accuracy**.

## Next boundary

See `docs/100k-run-plan-draft.md` for the proposed eight-worker 20% fallback / $7.28 cap (not applied), pre-run local commit, balance/disk preflight, and recorded graceful interruption/resume evidence. That document is a draft; the eight-worker graceful-stop production wrapper remains an explicit implementation prerequisite. No 100k or downstream paid work is authorized by this golden proposal.
