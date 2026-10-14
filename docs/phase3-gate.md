# Phase 3 gate — actual results

Completed October 13, 2026 (America/Los_Angeles). No paid calls, live provider execution,
key verification, measured API cost or real completed 500-review run is claimed.
Class 7 date is unknown; the 500-review milestone is urgent after preflight/pilot gates.

## Requested additions

docs/labels.md and both versioned enrichment prompts contain the four declared rules:
unauthorized/after-cancellation charges billing/4 unless concrete stated financial loss
then 5; account takeover access/5; permanent library/playlist loss 5 versus temporary
missing items 3; understandable non-English labeled with review flag, otherwise
other/unclear/1 with review flag. The guide has synthetic examples. The financial rule's
potential difference from the shared contract's serious-harm threshold is disclosed.

`python -m pipeline label-golden` is an offline human-only interface: one original review
at a time, numbered topic/intent/severity menus, five sentiment anchors, comma-separated
entities, full-text default quote or an immediately validated exact substring, and y/n
review flag. Every complete review is saved atomically in exact UTF-8 CSV format.
q/Ctrl+C/EOF stops safely; restart skips already valid human work. Session locking avoids
two labelers overwriting each other. Neither model predictions nor keys are displayed.
The real golden working copy remains byte-identical to the blank source: 0/50 labeled.

## Phase 3 implementation

- pipeline/schema.py: strict record schema, row identity and exact quotes; cache key and
  composite label_config from pinned requested models/settings/prompts/schema/extraction.
- pipeline/state.py: transactional distinct-text jobs, every original ID retained,
  atomic leases, completed/quarantined status, attempts, saved stages and calls,
  direct cache_source_id with succeeded original enrichment evidence, and checkpoints.
- pipeline/classify.py: six Jev judgments in one state request (required Choices/Score,
  plus language and missing context); sentiment score / 2 - 1; conservative extraction;
  structured Luna extraction and quota-limited low-confidence fallback.
- pipeline/providers.py: explicit standard-library HTTP clients with no hidden retries,
  silent key presence checks, bounded timeout and sanitized error messages. Account
  availability and actual response shape remain unverified until Phase 4's approved calls.
- pipeline/calls.py and spend.py: shared transactional project/run reservations, rolling
  request/token limits, capped retries/backoff/jitter, durable per-attempt logs, returned
  model/tier checks, and worker stop admission. Missing usage remains unavailable.
- pipeline/recovery.py and reconcile.py: restore durable validated responses without
  redispatch; uncertain charges remain reserved and leased until explicit verified-cost
  reconciliation. No claim of absolute exactly-once billing after a lost provider reply.
- pipeline/enrich.py and CLI: explicit mock versus confirmed-spend execution, source
  checksum checks, reusable state, saved output/calls/counts and interruption controls.
  Full-source enrichment is guarded pending Phase 6's approved saved-permutation selector.

All calls share the ledger path in config; mock ledgers are separate. Defaults preserve
Jev 60/s, one worker, 10% fallback, $10 project cap and $0.50 invocation cap. The conservative
token envelope and potential cache-write reservation are assumptions to verify in the
pilot. Current cost settlement claims no prompt-cache savings; raw usage is retained for
the Phase 4 calculator to reconcile actual billing categories and tier.

Current Luna enrichment uses one review per call (within the required maximum 50), so
invalid output cannot lose another review's result. Larger packing is an optional pilot
optimization. No Batch/Flex calls occur. The shared dispatch path accepts the four checker
roles; verifier/group/memo stage implementations and real succeeded-role evidence remain
later-phase work.

## Actual verification

Saved command outputs: artifacts/phase3/checks.json.

```text
pytest: 61 passed in 3.18s
ruff: All checks passed!
pip check: No broken requirements found.
All five supplied CSV checksums still match manifest.json.
The actual golden copy is still byte-identical and all seven fields blank.
No test-temp directories remain.
.env, course PDF and raw corpus are ignored.
git ls-files for those patterns: only .env.example.
```

Tests exercise human save/resume/interrupt, quote validation, exact CSV/source preservation,
strict model output types/ranges/probabilities, malformed JSON/IDs/quotes, direct cache
provenance, concurrent claims, stale completion rejection, source/config mismatch,
spend admission before dispatch, shared rate limits, quota persistence across resume,
bounded retries/repair/quarantine, unknown timeout retention, response recovery,
explicit charge reconciliation, model-change stops and mocked HTTP boundaries.
Network connections are blocked automatically in all tests. Synthetic injection tests
check the input/instruction boundary only; actual semantic injection resistance remains
Phase 5's evaluation, not a claim supported by mocked labels.

Saved CLI smoke evidence: artifacts/phase3/mock-smoke/. It uses four synthetic records,
not course business data: one empty text, two identical texts and one different text.
The stop saved 1 completed / 2 pending / 1 quarantined. Resume produced 3 completed /
1 quarantined. Checkpoint_before is a strict subset of checkpoint_after; no resume call
included a previously completed ID. Two simulated calls total; a further warm rerun
added zero calls. Their usage/ledger costs are explicitly simulated, not measured bills.

Issues fixed during implementation: lint/import/type issues; strict malformed-response
handling; durable response recovery before settlement; retry/quota persistence;
indexed call provenance instead of scanning all calls; and preventing reports from
overwriting human labels or preserved course files. Final tests/lint pass after fixes.

## Gate and next step

Review the labeler, approved rules and docs/enrichment.md; approve Phase 4 separately.
That phase silently checks credentials, prepares tiny provider test-call projections
for separate spend confirmation, verifies Jev/version/access/limits, and builds/measures
the 100-review cold/warm calculator. Then prioritize the real checkpoint_500 run.
Golden hand-labeling is still owner work; use the interactive command while the pipeline
progresses. Sampling/propagation totals, final grading export, actual evals, group/rank/
claims/memo, deployed database/backend/dashboard and submission checks remain later gates.
