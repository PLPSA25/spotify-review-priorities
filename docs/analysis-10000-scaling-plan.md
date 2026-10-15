# Analysis 10,000 scaling experiment — proposed, not authorized to execute

Updated proposal after full checkpoint verification:
checkpoint-500-recovery-gate.md proposes disjoint 1k slices at 1/2/8 workers followed
by a single analysis_10000 run, reducing repeated paid work. That proposal is awaiting
owner gate review; the matched full-file experiment below is an alternative, not a
scheduled or approved run.

The checkpoint gate must approve final thresholds and deterministic routing before
this experiment. No golden labels are used for selection or calibration. Provider
calls require a new reviewed proposal and explicit yes.

Run the identical supplied analysis_10000.csv (10,000 IDs, 8,448 distinct exact texts)
at 1, then 2, then 8 workers. Use three fresh result stores with empty result caches,
identical pinned label_config and identical saved Jev/fallback packing rules. No
cross-run saved-result reuse: otherwise the later workers would measure cache hits.
Keep provider limits, retry policy, token caps, fallbacks, text ordering, SQLite storage
and machine constant. Record provider prompt-cache usage per attempt because it cannot
be forcibly reset; compare billed/cache tokens and disclose cache differences rather
than describe all provider caching as cold. Record whether machine load changes.

Three full cold replicates require up to 25,344 initial Jev calls rather than 8,448.
Two additional cold repeats are deliberate measurement overhead and must be added to
the project budget. Produce exact source-length/token/reservation bounds and an
expected-cost forecast using checkpoint usage before approval. Do not run all three
merely because the expected budget fits: the full-project conservative reservation
plan and available $10 ledger headroom must be reviewed. If too expensive, propose
matched smaller independent development subsets or fewer replicates, with the
statistical limitations, and obtain approval before changing experiment scope.

Time ingest/setup, enrichment, verification and downstream roles separately with a
monotonic clock. Primary scaling endpoint: distinct completed texts per enrichment
second. Also report completed input rows/second, wall time, tail request latency,
provider rejection/retry rates, reservation pressure, fallback/extraction ID fractions,
and overhead. Summed overlapping request latencies are not wall time. Persist all
measurements even on failure. Run a no-dispatch warm replay per result store separately.

Blinded verification is measured separately; worker scaling measures enrichment, not
repeated verifier cost. Plan one declared 500-review verifier sample on the authoritative
chosen result store. Reuse those predictions only when the first labels/config/input
remain the same; do not call repeated experiments ground-truth replications. Choose an
authoritative experiment output before final aggregation and cache extension.

Project the saved 77,913-text 100k scope using the chosen measured distinct-text
throughput, subtracting only proven cache hits under the final frozen label_config.
Project verifier wall time using the measured 500-review pass, then add group/memo and
other fixed overhead once. Give a base estimate and a conservative slowdown scenario;
neither is a measured 100k runtime. Checkpoint extrapolation is provisional until this
matched-input scaling measurement exists. Stop at the analysis_10000 gate before the
100k run or recorded interruption/resume.

## Deterministic fallback allocation proposal

Current checkpoint behavior admits slots transactionally when workers encounter an
eligible text. Queue claims use ascending cache key; fallback admission itself has
no confidence ordering. Interleaving and completion timing can change which worker
consumes the remaining slots, so selections are not deterministic across worker
counts/run order. Persistent fallback_jobs protects admitted slots on resume, but
does not establish reproducible selection across independently fresh stores.

Proposed policy `lowest-confidence-v1`: complete and save Jev judgments for all distinct
texts in the fixed experiment scope before any fallback selection. Compute minimum
confidence and minimum top-two Choice margin from saved responses. Eligible texts
satisfy the frozen confidence/margin rule. Select at most floor(scope distinct texts
× fallback fraction) by ascending minimum confidence, then ascending minimum margin,
then sha256(exact UTF-8 text), then lexicographically smallest original review ID.
Persist the entire selected job list and its input/config digest atomically before
dispatch. Exact-text aliases consume no extra slot. Select/pack extraction and fallback
batches in deterministic saved order before workers claim batches; workers only change
dispatch concurrency. Language/other mandatory flags remain independent of selection.

Declare the selection policy/version in the enrichment section so label_config hashes
it. This deliberately produces a new config, because changing which reviews receive
fallback can change final labels. Do not relabel old checkpoint records or reinterpret
their provenance. A frozen new-scope extension policy must specify how already admitted
fallbacks consume quota; avoid global re-ranking that silently drops earlier decisions.
For extension, use explicit persisted new-work tranches, documented boundaries and a
fixed quota per tranche; reproducibility requires the same tranche boundaries. Model
reruns may themselves differ even if the allocation algorithm is deterministic.

This policy is proposed for review at the checkpoint gate, not applied retroactively.
