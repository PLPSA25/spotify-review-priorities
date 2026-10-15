# Frozen calibration and deterministic routing — October 14, 2026

Owner approved confidence 0.60, margin 0, non-English always flagged. Frozen live
label_config:
`c79a70421de9caad53c9932393f0eb6420f6d80e249cb9097dd5af3eb9d8eba9`.
Snapshot: frozen-label-config.json. Old checkpoint/pilot records remain immutable under
b0cc1ce0b0a518f391490a61ac00a1e0c0f8181f6feb3c143a1f2890ea7e8318; they are not cache
sources for this new hash. Worker count, rate/spend limits and fallback cap do not feed
the label hash. Model/settings, complete enrichment section, literal prompt contents,
schema/extractor versions and simulated flag do. The new selector/confidence-scope
versions and restored auxiliary prompt are included in identity.

## Calibration evidence

All 35 predeclared pairs are saved locally in calibration.csv; full per-field, flagged,
unflagged and overall comparisons for every pair in calibration_fields.csv. Those files
copy the measured checkpoint development diagnostic; source hash/provenance is recorded
in the frozen snapshot. Original detailed evidence remains in
../artifacts/checkpoint-500/calibration.json. These are comparisons with a blinded model
verifier, not human accuracy; golden labels never influenced calibration/design.

Chosen .60/0 flags 181/500 (36.2%) in the historical development evidence. Composite
disagreement (topic/intent/severity exact or sentiment difference >.25): final labels
97/181 (53.6%) flagged versus 64/319 (20.1%) unflagged; difference 33.5 percentage
points, exact-text-cluster bootstrap pointwise 95% interval 25.0–42.2 points. Original
Jev labels: 109/181 (60.2%) versus 64/319 (20.1%). Selection used no target flag rate:
among pairs with groups >=25, rate ratio >=1.5 and lower difference bound >5 points
against both original and final labels, maximize the smaller lower bound. Intervals
are exploratory and not multiplicity adjusted. This explains the owner-approved pair.

Final-label field disagreement: overall / candidate flagged / candidate unflagged:

- Topic: 54/500 (10.8%) / 39/181 (21.5%) / 15/319 (4.7%).
- Intent: 34/500 (6.8%) / 21/181 (11.6%) / 13/319 (4.1%).
- Severity exact: 60/500 (12.0%) / 43/181 (23.8%) / 17/319 (5.3%).
- Severity beyond ±1: 5/500 (1.0%) / 5/181 (2.8%) / 0/319 (0%).
- Sentiment sign: 37/500 (7.4%) / 14/181 (7.7%) / 23/319 (7.2%).
- Sentiment difference >.25: 54/500 (10.8%) / 20/181 (11.0%) / 34/319 (10.7%).

The rule distinguishes categorical/severity differences better than sentiment. Existing
final flags remain 264/500; the 181 candidate flags are offline triage, not rewritten
records or predicted counterfactual fallback results. New-policy live flag rates and
accuracy have not been measured.

## Language/context gap corrected before freezing

Historical trimmed jev-v2 asked four core questions only, so it could not reliably
enforce the language flag or missing-context flag from explicit judgments. Earlier
zero non-English diagnostic counts indicate missing auxiliary evidence, not proof all
reviews were English. Versioned jev-v3 preserves those four core questions/shared rules
and restores language Choice and missing_context Noul from the original v1 schema.
They remain in the same Jev request (six judgments, one call per distinct text).

V3 requires both auxiliary answers: missing ones invalidate output instead of silently
defaulting to English. Every nonenglish_understood or not_understood answer forces
needs_review, including after fallback; missing_context >=.5 also forces the flag.
Ununderstood language maps other/unclear/severity 1. Model language detection itself
has not been live-evaluated under v3. Confidence/ranking use only the four calibrated
classification fields (topic, intent, severity, sentiment); margins use the three
classification Choices. Auxiliary confidence does not change the calibration trigger.
Prompt v3 adds 506 serialized UTF-8 bytes per Jev request. New billed token usage and
quality are unmeasured; updated byte/token envelopes include the extra prompt.

## Deterministic selection and extension

`pipeline/deterministic.py` performs two phases. Save all valid Jev responses for the
fixed nonempty distinct-text tranche; terminal Jev failures are quarantined. Then rank
eligible texts by minimum classification confidence, minimum classification Choice
margin, exact UTF-8 text SHA-256, canonical original ID. Select at most
floor(tranche distinct texts × fallback fraction), persist the full ranked selection
and immutable batch plan in SQLite before any Luna dispatch. Ledger allocations use
both text key and tranche scope. Exact-text aliases consume no extra slot.

Source representatives for fresh jobs are canonical IDs, independent of CSV order.
Worker count changes dispatch concurrency, not selected texts/batches for identical
saved Jev results. Fresh provider responses may themselves differ. Tests compare 1/2/8
workers with reversed input, require all Jev scores and selection to exist before
Luna dispatch, exercise tie breaks and canonical aliases, verify warm no-dispatch and
interruption/resume without new Jev calls, and check cap changes cannot reselect a
pending tranche. Non-English remains flagged after fallback. Indexed Jev-stage claims
avoid rescanning all previously classified pending jobs.

Extension completes the active persisted tranche first; new pending texts create a
new immutable tranche with its own quota. Reproducibility requires the same tranche
boundaries; previously completed labels/calls/selections stay intact. Importing saved
results later must validate direct source/call provenance and this exact frozen hash.
At the scaling gate, keep three slice tranches fixed; the remaining analysis work is
a subsequent tranche rather than a silent global re-ranking. No old-hash relabeling or
new paid calls were performed during this freeze.

## Sentiment sign near zero (offline)

On the 500 valid checkpoint/verifier pairs, 37 sign disagreements. All 37 (100%) have
|sentiment| <.2 on at least one side: 33 neutral-versus-nonzero and four opposite
nonzero signs. 54/500 pairs have either value near zero; disagreement rate 37/54
(68.5%) there versus 0/446 away from zero. Thus observed sign disagreements are
concentrated near zero, not strong-polarity reversals. Exact zero defines neutral in
this diagnostic; sentiment mapping remains Jev score/2−1. Source counts and definition
are in sentiment-sign-diagnostic.json. This is a verifier diagnostic, not golden
evaluation or evidence that either model is human-correct.

Checks: 92 tests passed, project ruff and dependency check passed. Only mock/offline
execution in this continuation. Golden validator passed 50/50 without content being
inspected/displayed; requested revised-label disclosure and human CSV committed locally
as 1969b1b. Backup deleted after success and ignored; no push.
