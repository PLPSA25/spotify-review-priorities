# Checkpoint 500 recovery gate — ready for owner review, October 14, 2026

500/500 enrichment records and 500/500 valid blinded verifier predictions are saved.
No terminal verifier failures, no golden evaluation and no further paid run. The
initial failed invocation and offline recovery provenance remain unchanged; see
checkpoint-500-gate.md for the original failure/quota audit. This document supersedes
its incomplete calibration/recovery status.

## Failure policy and measured recovery

Exhausted invalid-output repairs now produce a failed call and durable terminal verifier
status; exclude those IDs from calibration and continue. Enrichment already quarantined
isolated invalid outputs and continued. Both now use >5% terminal failures among the last
100 finalized items, checked after a minimum of 20. Exactly 5% does not halt. Count one
terminal/success outcome per item, not each retry; enrichment counts distinct-text jobs,
not duplicate aliases. New knobs are in controls, so operational policy does not change
label_config. Recovery seeds the window with prior valid verifier outcomes. Auth/model
errors, budget exhaustion, unknown billing and other mandatory integrity stops remain.

Regression tests prove failed verifier repair persists terminal status and allows later
valid work, a bad enrichment item quarantines while the next succeeds, duplicate outcome
notifications do not inflate rate, and the rolling threshold stops systemic failures.
Final checks: 85 tests passed; project ruff and pip check passed. Failure-policy controls
are editable; currently window=100, minimum=20, threshold=0.05.

Approved recovery count/cost bounds did not change: 104 maximum calls, $0.1537 envelope,
$0.154 invocation cap. Actual recovery: three succeeded Luna verify calls, no repairs,
$0.004499000, 51.036050 seconds. Reused all 399 existing valid predictions; no new
enrichment/group/memo calls. Project spend $0.065419278 / $10, zero reservations;
remaining headroom $9.934580722. Costs use reported usage/rates, receipts unreconciled.

Checkpoint plus recovery: 595 total attempted calls, API spend $0.058020893. Enrichment
102.027312 seconds at two workers, 4.900649 rows/s / 4.694821 distinct texts/s. Verifier
attempt timers total 561.067326 seconds across initial interruption and recovery,
excluding offline fix/setup time; do not claim an uninterrupted end-to-end pass. Pilot
one-worker end-to-end throughput 1.705832 rows/s has no saved enrichment-stage timer,
so no causal worker-speedup claim. Same cold result-cache condition; provider prompt
cache and input/verifier mix differ. All labels remain under the original frozen hash.

## Full 500-review verifier disagreement

This compares final stored enrichment labels with the independent model verifier,
not human accuracy. All 500 predictions are valid; zero terminal items are excluded.
Severity ±1 disagreement means absolute difference >1; sentiment sign uses negative,
exactly zero and positive. Entities and needs_review are excluded from label-error
endpoints. Zero non-English examples were observed; always-flag language policy remains.

Using actual final needs_review, 264 flagged / 236 unflagged. Each line gives
overall / flagged / unflagged disagreement counts and percentages:

- Topic: 54/500 (10.8%) / 41/264 (15.5%) / 13/236 (5.5%).
- Intent: 34/500 (6.8%) / 30/264 (11.4%) / 4/236 (1.7%).
- Severity exact: 60/500 (12.0%) / 57/264 (21.6%) / 3/236 (1.3%).
- Severity beyond ±1: 5/500 (1.0%) / 4/264 (1.5%) / 1/236 (0.4%).
- Sentiment sign: 37/500 (7.4%) / 24/264 (9.1%) / 13/236 (5.5%).
- Sentiment beyond 0.25: 54/500 (10.8%) / 32/264 (12.1%) / 22/236 (9.3%).

Full grid and field/group breakdown for every candidate:
../artifacts/checkpoint-500/calibration_fields.csv, calibration.csv and calibration.json.
The predeclared composite calibration endpoint remains topic/intent/severity exact or
sentiment >0.25; sign is an additional diagnostic, not a post-hoc selection replacement.

## Threshold recommendation and records

Recommend confidence **0.60**, margin **0** (disable the margin trigger), retaining
mandatory non-English/missing-context flags. It flags 181/500 (36.2%) from stored Jev
evidence. Final-label composite disagreement: 97/181 (53.6%) flagged versus 64/319
(20.1%) unflagged, difference 33.5 percentage points; exact-text cluster bootstrap
pointwise 95% interval 25.0–42.2 points. Original Jev comparison: 109/181 (60.2%) versus
64/319 (20.1%). No target flag rate was used. This pair maximizes the smaller lower
bound among candidates meeting group-size >=25, rate ratio >=1.5 and lower difference
>5 points against both original Jev and final labels. Intervals are exploratory and
not multiplicity-adjusted; model disagreement is not human ground truth.

For candidate .60/0, final-label field breakdown (overall counts above unchanged),
flagged 181 / unflagged 319:

- Topic: 39/181 (21.5%) / 15/319 (4.7%).
- Intent: 21/181 (11.6%) / 13/319 (4.1%).
- Severity exact: 43/181 (23.8%) / 17/319 (5.3%).
- Severity beyond ±1: 5/181 (2.8%) / 0/319 (0%).
- Sentiment sign: 14/181 (7.7%) / 23/319 (7.2%).
- Sentiment beyond .25: 20/181 (11.0%) / 34/319 (10.7%).

The rule discriminates categorical/severity disagreement much better than sentiment.
The 181 triage flags are an offline candidate analysis, not rewritten final flags or
counterfactual fallback results. Current confidence .75/margin .15 and record hash
b0cc1ce0b0a518f391490a61ac00a1e0c0f8181f6feb3c143a1f2890ea7e8318 remain unchanged.
Threshold-only proposed hash is
927b14d058d2ced85d5db45adde0ff634caedbe4966a4bc85051097311c92e6a.
Adding the proposed deterministic fallback policy/version will change it again;
freeze both together before scaling/10k/100k. Do not mix old checkpoint caches into
new-config outputs. Keeping old checkpoint evidence costs $0; a fresh checkpoint
enrichment, if requested, has a $0.384882072 conservative envelope under corrected
10% quota and requires separate approval. No automatic paid rerun is necessary merely
to keep a historical development checkpoint under its original config.

The original quota bug caused 57 fallback texts rather than 47. Scope isolation is
fixed, but history is retained. Current slot allocation is first admission and depends
on workers. Proposed deterministic rule: save all Jev results, choose eligible texts
by minimum confidence, then minimum Choice margin, then text hash/canonical source ID,
persist the selected quota/batches before dispatch. Freeze extension tranche rules.

## Does the course require analysis_10000?

GRADING_CONTRACT.md names analysis_10000.csv as a development checkpoint and says
"Measure 100, then 500, then 10,000 reviews before committing to the full run"
(line 120). COST_CALCULATOR.md says to refresh after 500 and 10,000 (line 49). These
call for a 10k measurement; they do not say the same 10k must run at every worker
count. The checker contains no filename/count test for this development checkpoint;
that does not erase the written requirement. Binding CHATGPT_PROMPT.md line 93
specifically requires checkpoint_500.csv then analysis_10000.csv. Therefore keep one
analysis_10000 run, and replace only the three full-file scaling repeats with smaller
development slices if approved. Three 1k slices alone would not satisfy that plan.

## Cheaper scaling proposal (offline prepared, not executed)

Prepared three disjoint 1,000-row/1,000-distinct-text CSVs from analysis_10000, excluding
all checkpoint text families and golden IDs. Seeded text-hash ordering, one original
ID per exact text; all source fields preserved. Files/manifests under
../artifacts/scaling-proposal/. This measures cold distinct-text enrichment, not
duplicate propagation. Disjoint inputs confound concurrency with text mix; disclose
length/language/routing differences and avoid isolated causal-speedup claims.

Existing-config estimates, not measured scaling results:

- 1 worker: modeled 7.10 minutes (10.65 with 50% slowdown); expected $0.0533,
  conservative mix $0.0800, byte/token/repair envelope $0.816265558.
- 2 workers: modeled 3.55 minutes (5.33 slow); expected $0.0533,
  conservative mix $0.0800, envelope $0.837037298.
- 8 workers: modeled 0.89 minutes (1.33 slow); expected $0.0533,
  conservative mix $0.0800, envelope $0.821094550.

Combined expected $0.159986699 / conservative mix $0.239980049; conservative admission
envelopes total $2.474397406. 3,000 initial Jev calls, capped 10% fallback, at most one
repair, one transient attempt; no verifier/group/memo calls in these scaling estimates.
1/8-worker times assume linear scaling from the measured 2-worker checkpoint and are
not guarantees; shared rate limits/contention may dominate. Long-text counts 84/95/87;
mean lengths 87.4/92.5/83.1 characters. Fresh saved-result cache for each slice; provider
prompt caching cannot be reset. Recalculate exact costs after routing/hash freeze.

Then run analysis_10000 once at the chosen worker count. If validated same-config
slice results can be imported with direct original call provenance, remaining work
is 7,000 rows / 5,448 distinct texts, estimated $0.290535846 enrichment. Without reuse,
8,448 texts estimate $0.450522545. Separately budget its verifier/group/memo work.
This replaces expensive full-file repeats while preserving the 10k gate. Disjoint
slice results are a practical capacity comparison; use a matched-input repeat only
if ambiguity justifies its additional separately approved cost.

Provisional 100k-scope runtime at currently measured throughput: enrichment 4.61 hours,
or 6.91 with 50% slowdown, plus approximately 9.35 minutes of historical interrupted/
recovered verifier attempt time and unmeasured fixed overhead. Refresh after scaling.
No paid scaling or 10k execution is approved by this gate report; stop for owner review.
