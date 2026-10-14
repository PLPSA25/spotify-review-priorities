# Checkpoint 500 proposal — awaiting explicit yes, 2026-10-14

No paid checkpoint calls have been made. Machine-readable evidence and exact pilot
Luna call IDs/review-ID lists are in checkpoint-500-proposal.json. The audit script
reads only saved pilot predictions/calls, development text and original golden IDs;
it never reads the human golden labels.

## Paid scope and bounds

Cold empty result cache, two workers, unchanged enrichment label_config. Deliberately
do not reuse the 100 pilot texts, to match the pilot's cold-cache condition. There are
500 rows, 479 distinct nonempty texts and 38 texts longer than 240 characters. One
Jev initial call per distinct text. At most 47 fallback IDs (floor(479 × 10%)) and
38 extraction IDs, with overlap reducing the 85-ID upper bound. Enrichment batches
remain at most 20. Worker count changes only the controls, not the label hash.

Blinded Luna verification covers all 500 checkpoint IDs, with zero golden-ID overlap:
10 initial batches of 50. This is the Phase 5 500-review verifier sample. Send original
text plus rubric only; no Jev/fallback prediction is sent. Use a separate verifier
payload with a 10,000 output-token cap (200 per review), 24,000 input-token admission
bound and singleton 200-output/10,000-input repair bounds. The enrichment output cap
and hash remain unchanged. If a 50-review batch exceeds its input bound, stop and
request a revised proposal rather than silently increase calls or caps.

Use one transient attempt (as in the pilot), and at most one invalid-output repair.
A known transient rejection stops that item's attempt; unknown outcomes retain their
reservation and stop the run. No group/memo calls are included in this checkpoint
enrichment/verification approval. Initial calls: 479 Jev + up to 85 Luna enrichment
calls + 10 verifier calls = at most 574. Batched enrichment should use fewer calls;
the exact routing is not known until Jev results arrive. Maximum including repairs:
958 Jev + 170 Luna enrichment + 510 verifier = 1,638 calls.

Worst-case rate-based admission envelope: Jev $0.229476072; Luna enrichment
$0.155406000; verification $0.755000000; total **$1.139882072**. The envelope uses
singleton enrichment requests, the largest 85 singleton Luna costs, byte-count input
bounds plus protocol overhead and 1,024 extra repair bytes, and maximum output caps.
Enforce those bounds before dispatch; exceeding them stops rather than spends.
Reserve Luna input at max($0.10, $0.125)/million, output $0.50/million, Jev input
$0.042/million. No cache discount is assumed. These are confirmed planning rates,
not reconciled receipts. Approval must include a checkpoint run cap of $1.14,
above the default $0.50 invocation cap. With the entire envelope spent, accounted
project spend would be $1.147280457; currently reserved spend is zero. The $10
project cap stays unchanged. No automatic resume/retry spending after the gate.

## Pilot routing and flags

The four succeeded Luna enrich calls were one fallback batch covering 10 IDs and
three extraction batches covering 2, 3 and 1 IDs. Fallback was triggered by Jev
confidence below 0.75 or top-two margin below 0.15, admitted up to the 10% quota.
Extraction-only was triggered by text longer than 240 characters and absence of an
admitted fallback; it returns entities/quote while retaining Jev labels. Batches
formed separately within queue windows, hence three small extraction calls.
The reported one fallback is one call, not one review: measured fallback rate is
10/100 distinct texts = 10%; extraction-only rate is 6/100 = 6%.

The $4.406184/$6.604568 project estimates extrapolate the measured enrichment cost
per text, including that 10% fallback and 6% extraction mix. They include actual
spend, remaining development/scope text union, 1,500 future verifier reviews and
three future group/memo runs. Conservative multiplies variable enrichment/verification
cost by 1.5; it does not mean a 15% fallback routing quota. They assume unchanged-config
cache transfer and now need refreshing for this intentionally cold checkpoint repeat.

Recount from saved final records: 54/100 needs_review. Overlapping Jev trigger counts
among those flagged: low confidence 54, low margin 14, non-English 0, missing context 0,
other/unexplained 0. Exclusive partition: confidence only 40, confidence plus margin
14, margin only 0, non-English/other 0. Before fallback, Jev flagged 64; fallback
cleared ten flags. Thus these reasons describe original Jev evidence for final flags,
not a stored final explanation field (none exists).

## Older conservative estimate and actual ledger behavior

$10.3525283725 uses the 84,366-text development/scope union, the synthetic 1,003-token
Jev baseline plus one token per extra byte, all long reviews plus a disjoint full
10% fallback allowance (16,949 Luna reviews), 20-review batch overhead, 200 output
tokens per Luna review, no cache savings, $0.125/M Luna input, 1,510 verifier reviews,
four group/memo runs, then 50% retry cost on all projected stages plus spent $0.007398385.
Components before retries: Jev $3.82558995, Luna enrichment $2.611614375,
verify $0.434125, fixed roles $0.025424; retry allowance $3.4483766625.
It is a sensitivity scenario, not a measured bill or obsolete guarantee; retain it.
Its synthetic-only limitation is stale now that the real pilot exists.

The ledger does not read project_budget.json or reserve the whole $10.353 forecast.
It transactionally checks spent + outstanding reservations + next request against
both project and invocation caps. Therefore that forecast itself cannot block a run;
actual admission can stop midway if those sums exceed a cap. Each settled request
releases its excess reservation; unknown charges retain reservations. Reported actual
cost above its request reservation also stops execution. No spend guarantees follow
from a cheaper statistical forecast.

## Exact label_config identity

SHA-256 over UTF-8 canonical JSON (sorted keys, compact separators):

- models: jev, luna, effort, service_tier, allow_flex, allow_batch,
  flag_returned_model_change, output_token_cap.
- routing (the entire enrichment section): jev_prompt, batch_size,
  luna_input_token_bound, luna_output_tokens_per_review, confidence_threshold,
  probability_margin_threshold, short_review_chars, entity_terms.
- prompts: full literal file contents of the selected jev-v2.json and luna-enrich-v1.txt.
- schema_version = record-v1; extractor = exact-v1; simulated = false.

Controls (including max_workers and fallback_fraction), pilot, verifier, scope, rates
and provider limits do not feed the hash. An offline perturbation confirmed worker
count/fallback cap leave the hash unchanged. Both confidence and margin changes
change the hash. Batch size/input/output bounds also feed it, although operational.
Current hash: b0cc1ce0b0a518f391490a61ac00a1e0c0f8181f6feb3c143a1f2890ea7e8318.

Raw Jev responses retain every confidence/probability, language and missing-context
value. Recompute candidate Jev flags offline from them without paid calls. Parsed
stage results retain only combined low_confidence/nonenglish, not numeric minima.
Fallback final flags are independent Luna predictions; preserve those and separately
report candidate Jev triage flags. Recomputing flags does not recreate counterfactual
fallback classifications or silently authorize relabeling completed records.

## Calibration and next gate

Keep checkpoint records under the frozen pilot config. After verification, compare
predeclared confidence candidates 0.40/0.50/0.60/0.65/0.70/0.75/0.80 and margins
0/0.05/0.10/0.15/0.20. Keep non-English always flagged and missing_context >= 0.5
flagged. For every pair report flagged/unflagged counts, flag rate, topic/intent/severity
disagreement rates and sentiment differences above tolerance 0.25, with uncertainty
and small-group warnings. Treat verifier disagreement as a proxy, not ground truth;
exclude entities and needs_review from the semantic-disagreement endpoint to avoid
using the flag itself as its target. Report against both original Jev labels and final
fallback-adjusted labels to expose routing selection effects. Cluster uncertainty by
exact text because repeated reviews are not independent. No target flag percentage.

Recommend a pair only if flagged records are materially more disagreement-prone,
with counts and effect size supporting it. Otherwise recommend retaining settings
or collecting development evidence; do not manufacture a useful threshold.
No golden evaluation is authorized. Validate-only result: 50/50 valid.

If new thresholds are recommended, do not mutate checkpoint records/config or mix
caches. At the gate show old versus proposed hash and evaluate offline replay from
stored raw responses with validated provenance. A flags-only analysis copy costs $0,
but cannot serve as unchanged-config grading/cache evidence. A straightforward fresh
checkpoint enrichment under new thresholds would cost at most $0.384882072 under
this same conservative 10%/38-long-text envelope; separately re-verifying would add
up to $0.755. Exact selected-policy costs will be recalculated before any new approval.
Freeze the final decision before analysis_10000 and 100k execution.

Measure checkpoint enrichment and verification times separately. Compare cold input
throughput with the pilot's recorded 1.705832 rows/s, disclosing different input size
and verifier size, and that pilot stage-specific enrichment timing is unavailable.
Do not describe that comparison as an isolated worker speedup. At the gate plan
analysis_10000 matched-input 1→2→8-worker experiments under identical cache settings;
any repeated cold work needs separate cost approval. Project 100k wall time from
measured distinct-text enrichment and verifier throughput, adding measured fixed
overhead once. Stop at the checkpoint gate before analysis_10000 or reruns.
