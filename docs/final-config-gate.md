# Final reason/config gate — October 14, 2026

User approved this final behavior change before the checkpoint A/B. Jev-v3 and
confidence .60 / margin 0 stay unchanged. No paid execution occurred at this gate.

New frozen label_config:
`21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`.
The preceding snapshot is preserved at frozen-label-config-before-reasons.json;
the exact current description and prompt/schema identities are in
frozen-label-config.json. Old paid calls/records keep their historical hashes.

## Implemented semantics

Every completed record, including direct exact-text cache aliases, carries
needs_review_reasons. Allowed reasons, in canonical order, are
language_non_english, language_not_understood, missing_context, low_confidence.
The list is unique; needs_review equals whether the list is nonempty. Unflagged
records have an explicit empty list. Quarantined records retain their failure
reason/status rather than being represented as successfully classified reviews.

Jev derives language reasons from its Choice, context from Noul >=.5, and
low_confidence from the minimum four core confidences <.60. Margin is zero and
therefore contributes no additional flags. Local completion preserves these
reasons. Extraction-only Luna returns explicit independently identified reasons;
code unions all of them with all initial reasons. Extraction cannot clear initial
classifier uncertainty. Independent fallback returns its own reason list; code
unions it with the original language/context reasons, dropping only the original
low_confidence reason. Luna may independently report low_confidence for unresolved
classification uncertainty; this is self-reported, not a numeric Jev score.
Missing-context raised by either model and original language flags persist.

Luna-v2 prompt and strict output schema request reasons on both extraction and
classification responses. For classification, a boolean/reason mismatch, unknown
reason or duplicate reason is invalid output and receives the permitted repair.
For extraction, the final boolean is computed after the reason union. Quote remains
an exact substring, limited in the new Luna prompt to 80 characters. The output
budget remains 200 tokens per review; this new prompt has not been live-measured.

New records use record-v2. Cache aliases copy the reason list. New live enrichment
stores persist an explicit reason requirement and reject completed records lacking
it; reopening does not weaken that requirement. Legacy history remains readable
without inventing old reasons, and State/config guards prevent mixing hashes.
Calls log the Luna-v2 prompt and record-v2 schema identity. Golden human records,
templates and validator were not modified or read for this change.

## Offline 3,000-row projection, not new-hash results

Saved Jev responses plus historical final booleans yield a carry-forward proxy:
1,896/3,000 (63.2%) flagged, versus historical 1,823 (60.77%); 73 Jev
missing-context signals previously cleared by fallback are restored. Original
low-confidence flags can still clear, so this is not the earlier 67.13% sticky-core
proposal. Known retained reason counts/rates overlap:

- language_non_english: 155/3,000 (5.17%).
- language_not_understood: 110/3,000 (3.67%).
- missing_context from saved Jev: 1,369/3,000 (45.63%).
- low_confidence retained outside classification fallback: 942/3,000 (31.4%).

109 historically flagged fallback records lack the new Luna reason schema. Most
also have a known retained language/context reason; four projected flags have no
such known reason. Their old final booleans are retained only in this *projection*,
not fabricated as new-hash classified records. New Luna context/confidence reasons
on fallback and extraction calls are unknown, and its changed prompt can change
predictions. Therefore 63.2% is an offline proxy, not a guaranteed fresh-run flag
rate or a complete final reason forecast. Machine-readable summary and per-ID proxy
are docs/final-flag-offline-projection.json and
artifacts/scaling/final-flag-offline-proxy.json. No old label/call is rehashed.

## Revised same-row checkpoint A/B proposal — waiting for yes

The proposal JSON is docs/checkpoint-500-v3-ab-proposal.json. Re-enrich the same
500 checkpoint rows / 479 distinct texts under the final hash, two workers,
fresh result store. Propagate 21 aliases; allocate at most 47 fallback texts.
38 long texts +47 possible fallback texts yield at most 85 Luna enrichment IDs.
At most one repair per item and one transient attempt:

- Jev: 479 initial +479 possible repair requests; bound $0.249835488.
- Luna: up to 85 singleton-equivalent initial +85 repairs; bound $0.180374750.
- Total **1,128 calls maximum, $0.430210238 worst case**; proposed invocation
  cap **$0.431**. No verifier, group, memo or golden calls.

The upper bound uses actual new canonical payload UTF-8 bytes +2,048 overhead
+1,024 repair allowance, two attempts per permitted item, Jev $0.042/M input,
Luna conservative $0.125/M input/cache-write and $0.50/M output, 200 output
tokens per review. Luna's larger prompt/schema increases the old proposal by
$0.024968750; call count is unchanged. Project spend remains $0.266722386 with
zero reservations; full worst case would produce $0.696932624 total.
Per-call/stage/project guards, source/reference/config/rate checks and terminal
failure policy remain in force. The explicit runner is
python -m pipeline.checkpoint_ab --confirm-spend, and is not run at this gate.

Reuse the fixed 500 blinded checkpoint verifier predictions. Audited historical
verifier inputs contain only original IDs/text plus rubric, not first predictions.
Primary historical matched-text comparison uses only four Jev core answers with
identical decoding in v2/v3. Shared core rules/questions are unchanged; added
auxiliary questions are the prompt difference. Operational final enrichment is
reported separately: thresholds/allocation and now Luna-v2 reason schema/context
persistence differ, so it is not a pure Jev-prompt comparison. Show topic, intent,
severity exact/±1 and sentiment sign, plus .25 tolerance, and disclose valid
denominators, failures and paired changes. Verifier comparisons are not human truth.

After the A/B, complete analysis_10000 under this final hash. Historical 3,000 slice
records cannot be silently reused as final-hash evidence; their texts must be
processed under the new hash as part of completing that development dataset.
The A/B supplies reusable final-hash checkpoint text evidence where exact-text
overlap exists. Before analysis dispatch, calculate/show its separate envelope
and obtain the required paid yes; stop at the analysis gate before 100k.

Regression coverage checks persistent context from either model, both language
categories, clearing only initial low confidence at fallback, extraction unions,
empty lists, rejected boolean/reason mismatches/duplicates/unknown enums, copied
cache reasons, durable store validation and no dispatch without approval.
Gate checks: 112 tests passed, ruff passed and dependency check passed. The
runtime config, final snapshot and A/B proposal were checked to have the same hash.
