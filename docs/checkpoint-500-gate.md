# Checkpoint gate — held, October 14, 2026

Enrichment completed 500/500 original IDs: 479 distinct texts, 21 direct cache aliases,
zero quarantines. Frozen label_config is unchanged. Final needs_review: 264/500 (52.8%).
No golden agreement evaluation or analysis_10000 execution has occurred.

Two workers, cold result cache with no pilot reuse: enrichment 102.027312 seconds,
4.900649 input rows/s, 4.694821 distinct texts/s. The one-worker pilot's recorded
end-to-end attempt was 58.622409 seconds / 1.705832 rows/s; its enrichment-only timer
was not saved. Same result-cache conditions, different inputs/verification volumes;
this is not an isolated measured worker speedup. Provider prompt-cache state was not
controlled; raw billing categories are saved.

The invocation stopped after 612.058589 seconds, with 510.031277 seconds between
enrichment completion and verifier failure. This is a failed end-to-end attempt.
381 verifier predictions were saved during execution; offline recovery validated 18
more from archived individual output message blocks, for 399/500. Original call
failures were not rewritten. Recovery provenance is verifier_recovery.json; exact
IDs, schema/ranges and quotes were revalidated, and conflicting predictions rejected.

592 calls: 479 Jev, four fallback batches, 17 extraction batches, eight initial verifier
batches and 84 singleton repairs. Enrichment $0.025544543; verification $0.027977350;
total $0.053521893. Project ledger $0.060920278 / $10, reservations zero. Costs use
reported usage and dated rates; receipts remain unreconciled. Models stayed
jev-1.13.0/gpt-6-luna. Two multi-message responses failed concatenated JSON parsing;
two quote errors were repaired, but one later singleton repair still produced a
non-substring quote. It exhausted its original repair allowance, so no further paid
attempt has been made. Parser now accepts one unique structured message envelope and
rejects conflicting envelopes; exact-quote validation remains unchanged.

## Fallback quota bug, selection and deterministic proposal

305/479 distinct texts were fallback-eligible. Expected floor(479 × 10%) = 47 fallback
texts; actual 57 (11.90%). The old ledger
checked text keys globally, granting ten prior pilot allocations without consuming
checkpoint quota, in addition to 47 checkpoint allocations. Extraction-only: 31 texts;
total Luna-enriched texts 88, exceeding the proposed 85-ID bound. Dollar and call
envelopes held, but the ID/quota ceiling was violated. Historical results retain this
bug's effect; it is not an approved policy change.

Fixed future allocations to use composite (text key, scope) identity and transactional
scope counts. Legacy rows remain preserved. Regression tests verify scope isolation.
No paid relabeling followed the fix. Selection itself remains first admission: queue
claims use ascending cache key, but worker interleaving affects who consumes the slots.
Fresh runs are not deterministic across worker counts/run order; resume preserves
already admitted decisions.

Propose lowest-confidence-v1 before analysis_10000: save all Jev scores for a defined
scope, sort eligible distinct texts by minimum confidence, minimum Choice margin,
exact-text SHA-256, then canonical source ID; persist the top quota and deterministic
batch plan before dispatch. Declare policy/version in the enrichment hash and freeze
extension-tranche boundaries. Worker count then changes dispatch timing, not selection
for the same saved scores. Provider reruns themselves may differ. See
analysis-10000-scaling-plan.md; policy not applied retroactively.

## Development calibration (399 verified items; provisional)

All 35 candidate pairs, counts and rates: ../artifacts/checkpoint-500/calibration.csv.
Per-field counts, Jev/final comparisons and uncertainty: calibration.json. Endpoint:
any topic/intent/severity disagreement or sentiment difference >0.25; entities and
needs_review excluded. Non-English and missing-context remain mandatory flags.
Zero Jev non-English cases appeared in the 399 items, so effectiveness is unmeasured.

- (confidence .75, margin .15): 247/399 flagged (61.9%); final-label disagreement
  102/247 (41.3%) flagged versus 26/152 (17.1%) unflagged.
- (.60, 0): 140/399 flagged (35.1%); 70/140 (50.0%) versus 58/259 (22.4%).
- (.50, .10): 85/399 flagged (21.3%); 44/85 (51.8%) versus 84/314 (26.8%).
- (.80, 0): 276/399 flagged (69.2%); 111/276 (40.2%) versus 17/123 (13.8%).

No flag-rate target. Exploratory selection requires groups >=25, rate ratio >=1.5,
and exact-text-cluster bootstrap lower difference >5 percentage points against both
original Jev and final labels; maximize the smaller lower bound. Currently (.80, 0)
has final difference 26.4 points, pointwise 95% interval 17.5–35.1 points. Before the
last offline recovery (.60, 0) led, showing instability. Missing verifier records are
not random; intervals are not multiplicity adjusted; verifier is not human truth.
Therefore do not freeze new thresholds from this incomplete pass. Keep current hash
and records immutable until verification completes. Offline flag analysis costs $0.
New thresholds/selection change the hash; fresh checkpoint enrichment has the prior
$0.384882072 conservative bound under the corrected 10% quota and needs separate
approval. Saved independent verifier outputs can be re-compared offline under an
unchanged rubric, with provenance retained; no automatic paid re-verification.

## Projections and remaining verification

Measured two-worker enrichment extrapolates 77,913 distinct texts to 4.61 hours without
reuse, or 6.91 hours with 50% slowdown. Add unmeasured complete verification/fixed-stage
wall time; this is not a complete 100k runtime measurement. Current usage-based project
estimates $4.606 base/$6.878 conservative, or $5.507/$8.229 with two extra cold 10k
scaling repeats, extrapolate the buggy 11.9% fallback mix and incomplete verifier.
They are not worst-case guarantees; refresh routing/cache/recovery assumptions before
another large run. Matched 1→2→8-worker 10k experiments use fresh result stores and
25,344 Jev initial calls; new paid approval is required. Scaling plan is documented.

Concrete verifier-only recovery plan: checkpoint-verifier-recovery-proposal.json,
all 101 pending IDs. Reuse 399 valid predictions and all enrichment. Two unattempted
50-review batches plus one previously failed ID; up to one new repair per pending ID:
3 initial calls, up to 101 repairs, 104 maximum Luna calls. No transient retries.
Batch envelopes 24,000 input/10,000 output; singleton 10,000 input/200 output. For the
one failed quote, add explicit exact-substring/80-character guidance and disclose
blinded-quote-v2; other rubric/model settings unchanged. Revised payloads must be
validated before dispatch. Worst-case $0.153700000, proposed invocation cap $0.154,
project cap $10. No enrichment/group/memo calls or golden evaluation. New yes needed
because that ID exhausted the original repair allowance and this is a separate run.
After recovery, rerun development diagnostics offline and stop at the same gate.

Checks: 80 tests passed; project ruff passed; pip check passed; all five supplied CSV
checksums match. Failure evidence, usage and records are saved in artifacts/checkpoint-500.
