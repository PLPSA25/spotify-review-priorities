# V3 verifier transfer gate — October 14, 2026

The approved 500-row sample is fully verified: 500 valid, zero terminal failures,
274.445 seconds, 11 Luna requests (ten 50-row batches and one singleton repair),
measured cost **$0.026800925**, versus the approved $0.755 maximum. One initial
item had a quote that was not an exact source substring; valid siblings persisted,
and its permitted repair succeeded. The partially valid batch is logged succeeded
with its per-item validation error. No whole-call failures or unresolved charges.
Project ledger: **$0.266722386 / $10**, zero reserved.

Inputs were original texts plus rubric and independent language/context questions;
no first labels, no golden IDs or human golden answers. Enrichment config and all
3,000 saved slice records remain frozen and unchanged. Nothing below was applied.
Remaining analysis_10000, reprocessing and golden evaluation were not dispatched.

Evidence: `artifacts/scaling/transfer-verifier/report.json`, `verifier.json`,
`measurements.json`, `calls.jsonl`, `core-calibration.csv` (all 35 pairs),
`core-calibration-fields.csv`, and `calibration_items.json`. Reproduce comparisons
offline with `python -m pipeline.transfer_report`; it cannot make API calls.

## Endpoints and method

Composite disagreement is any topic/intent/severity exact mismatch or sentiment
absolute difference >0.25. Entities, needs_review and language are excluded from
this composite; language confirmation is reported separately. This is independent
model agreement, not human accuracy. Overall composite disagreements are
219/500 (43.8%) for Jev and 201/500 (40.2%) for final stored enrichment.

Final per-field disagreements: topic 77/500 (15.4%); intent 51/500 (10.2%);
severity exact 57/500 (11.4%); severity beyond ±1 4/500 (0.8%);
sentiment sign 51/500 (10.2%); sentiment difference >.25 80/500 (16.0%).
Jev corresponding counts are 86 / 58 / 70 / 6 / 48 / 82.

Core confidence is the minimum of topic, intent, severity and sentiment confidence.
Margin is the minimum top-two probability gap for topic, intent and severity.
Language confidence and missing-context judgments are excluded from this grid.
The same 7 confidence values (.4, .5, .6, .65, .7, .75, .8) × 5 margins
(0, .05, .1, .15, .2) produce 35 comparisons. Bootstrap: 1,000 fixed-seed
unique-text resamples; all sampled texts are distinct. Material separation requires
at least 25 items per group, lower pointwise 95% difference bound >5 percentage
points, and flagged/unflagged ratio >=1.5, for both Jev and final comparisons.
Intervals are exploratory and not adjusted for searching 35 pairs.

31 pairs qualify. Retain the predeclared **confidence .60 / margin 0**:
it transfers, so no new threshold search is needed to replace it.
Core flags 219/500 (43.8%); Jev disagreements 143/219 (65.3%) versus
76/281 (27.0%), difference interval 29.9–45.4 percentage points.
Final disagreements 125/219 (57.1%) versus 76/281 (27.0%), ratio 2.11,
difference interval 21.3–37.8 points. Core flags on all slices are 1,242/3,000.
Margin .05–.20 adds no flags at .60 on this sample; keep zero.
The strongest exploratory split is .80/0 (final 49.5% versus 10.2%), but adopting
the best-looking split from this same transfer sample is unnecessary post-hoc
retuning. No target flag rate governed the recommendation.

At .60/0, final core-flagged versus core-unflagged field disagreement counts:
topic 48/219 versus 29/281; intent 39/219 versus 12/281; severity exact
39/219 versus 18/281; severity beyond ±1 4/219 versus 0/281; sentiment sign
25/219 versus 26/281; sentiment >.25 45/219 versus 35/281. The signal is
especially strong for categorical fields; sentiment sign alone separates weakly.

## Auxiliary-only reasons

Auxiliary-only means initial Jev needs_review true without a core .60/0 trigger.
All-slice counts total 772; the verified sample has 129. Reasons overlap. Reference
unflagged group is 152 verified rows with **48/152 (31.6%)** composite disagreement
for both Jev and final labels. Auxiliary-only groups below have identical Jev/final
disagreements because none received classification fallback.

- Non-English/ununderstood broad language bucket: 124/3,000 auxiliary-only rows;
  sample 19, disagreements **8/19 (42.1%)** versus 31.6%. Small sample; difference
  interval −13.5 to +34.8 points does not establish material separation.
- Understandable non-English subset: 59 rows; sample 11, **7/11 (63.6%)**.
  Wide interval includes zero and the group is below the 25-item criterion.
- Not-understood subset: 65 rows; sample 8, **1/8 (12.5%)**. Keep the declared
  unsupported-language rule; low categorical disagreement partly reflects both
  models using conservative other/unclear/1. Sentiment sign differs on 7/8.
- Missing context >=.5: 753 auxiliary-only rows; sample 124,
  **24/124 (19.4%)**, lower than unflagged 31.6%; difference interval
  −22.4 to −2.1 points. Only **42/124 (33.9%)** receive an independent verifier
  missing-context judgment. This suggests the current detector is broad, but is
  not human adjudication and does not authorize dropping the required reason.
- Additional opaque Luna-only final flag without a Jev trigger: **0** population
  and sample rows. No independent optional judgment reason was observed.

Exclusive buckets avoid double counting: language only 19 population / 5 sample
(4/5 disagree); context only 648 / 110 (20/110 disagree); both 105 / 14
(4/14 disagree). Thus 19+648+105=772 population and 5+110+14=129 sample.
Full per-field reason comparisons and pointwise intervals are in report.json.

## Independent language check

Of the 46 sampled Jev language-flagged rows (including not-understood), the verifier
calls **21 non-English-understood, 5 English, and 20 not-understood**. The broad
non-English-or-not-understood bucket agrees on 41/46 (89.1%), but that is not
41 confirmed non-English texts: 20 remain unidentified.

For the 30 Jev-understood-non-English rows, the verifier agrees on 21/30 (70%),
calls 4 English and cannot understand 5. For 16 Jev-not-understood rows, it calls
15 not-understood and 1 English. Of the 454 Jev-English rows, it calls 447 English,
3 non-English-understood and 4 not-understood. These are detection disagreements,
not a human language benchmark. Keep non-English flags as declared.

## Proposed final flag rule — not applied

Subsequent audit: `checkpoint-500-v3-ab-proposal.md` quotes contract line 49.
The contract's missing-context sentence does not require preserving every first-model
context flag after independent fallback. The sticky behavior below is an optional
policy proposal, not an explicit contract mandate. Current frozen behavior remains.

For every final record, use the stored original Jev judgments:
**language != english OR missing_context >=.5 OR core confidence <.60**.
Margin remains zero. Non-English/unsupported language stays flagged; missing context
stays flagged because GRADING_CONTRACT.md says "Missing context should trigger
`needs_review`; do not invent impact." No optional auxiliary reason currently
qualifies for retention: there is no separately observed optional reason to drop.
Do not introduce an unexplained Luna needs_review flag as a separate trigger.

This proposal also makes the required/context and supported core flags persist
after fallback. Current fallback may clear context/core flags; language already
persists. Resulting final flags would be **2,014/3,000 (67.13%)**, versus current
stored 1,823/3,000 (60.77%). In the verified sample: 348/500 (69.6%) would flag,
with final disagreement 153/348 (44.0%) versus 48/152 (31.6%). The combined rule
has weaker separation than the core rule because mandatory context flags dilute
it. Required and discretionary reasons should be displayed separately.

The proposal does not reduce the rate by discarding contract-required cases.
If the broad context detector is revised later, review its question/definition
against supported generic other/low-impact classifications, measure that revision,
and preserve genuine missing-context flags. That prompt revision is not approved
or implemented here.

## Hash and reprocessing cost

Keeping .60/0 alone does not change the existing hash. The proposed final policy
changes fallback flag handling, so explicitly version it in enrichment as
`needs_review_policy="required-context-core-v1"` to avoid silent semantic mixing.
Candidate hash (computed offline, not frozen):
`67cf1084c733c2ffbcff84a424b2b06f5e6a67c1695d777cf52300c63db6b31d`.
Current hash remains
`c79a70421de9caad53c9932393f0eb6420f6d80e249cb9097dd5af3eb9d8eba9`.

Recomputing proposed flags from saved Jev responses costs **$0 / zero calls**.
Publishing them under a new label_config cannot silently relabel old call evidence:
the contract/current strict cache policy requires matching succeeded enrichment
evidence. Under that policy, adoption requires separately approved fresh enrichment
of the 3,000 v3 texts in a new store/hash. Estimated cost at observed mix is
**$0.174502**; conservative envelope **$2.601909406**, maximum 7,132 calls,
same prompts, .60/0 routing, 10% fallback quota, output bounds and one repair.
No verifier rerun is inherently required just to diagnose stored flags; model
outputs on fresh enrichment may differ. Until migration, old slices do not provide
same-hash final cache reuse under the candidate hash. Old v2 pilot/checkpoint
remain historical and are not claimed as candidate-hash results.

Stopped at this gate. No policy change, reprocessing or remaining 10k calls.
Gate checks: 97 tests passed, ruff passed, dependency check passed; frozen
configuration hash independently checked unchanged.
