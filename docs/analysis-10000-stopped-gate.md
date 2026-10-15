# Analysis_10000 stopped-run gate — October 14, 2026

The user approved **$1.50**, replacing the earlier proposed $7.442 invocation cap.
The full theoretical call/token envelope remains $7.441328042; it is not permission
to spend that amount. Models, prompts, .60/0 thresholds and final label_config remain
`21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`.

## Cap safety verified before starting

Calls reserve spent + outstanding reservations + next request cost atomically.
The first monetary rejection is committed as a durable per-invocation admission
stop before the exception propagates. All later reservations for that invocation
are rejected even if earlier in-flight calls settle and free headroom. Already
dispatched calls drain; unstarted claims release. Completed records and their
aliases commit in one SQLite transaction. Valid intermediate Jev responses remain
saved on pending work, not half-written completed records.

Regression tests demonstrate eight-worker monetary interruption, zero dangling
leases in that cap-stop case, same-hash reopening without re-calling successful
Jev IDs, and a cap stop between a partial Luna batch and the invalid item's repair.
Valid siblings persist and a reviewed new invocation resumes only the missing item
with the same saved selection. The wrapper refuses automatic recovery/resume.
These operational safety changes do not affect the label hash.

## Actual stop: provider outcomes unknown, not a cap hit

The invocation stopped after **26.122006 seconds**, before Luna enrichment.
Seven TypeSafe requests ended with "Timeout/connection outcome unknown; reconcile
before retry" after about 21.6 seconds each. No provider responses or usage were
available for these requests; the root connection cause and whether inference was
billed are not established. The integrity guard stopped admissions immediately.
No retry, lease release for those unknown jobs, or paid resume occurred.

- 86 new requests: **79 succeeded Jev results saved**, seven outcomes unknown.
- **Known new cost $0.003852030**; **$0.001561182** retained in reservations for
  unknown charges. This is not a claim that those calls cost zero or were unbilled.
- Project known spend **$0.298215468**, plus reservations **$0.001561182**;
  committed total **$0.299776650 / $10**.
- The $1.50 invocation cap was **not hit**. Known spent + reserved for this
  invocation is $0.005413212.
- Rows: **1,436 completed** (all final-hash reuse), **8,563 pending**, **one
  retained terminal quote failure** from the A/B. New terminal failures: **zero**;
  the seven unknown calls are held pending, not falsely classified as terminal.
- Seven unknown work leases remain intentionally held to prevent silent duplicate
  calls. SQLite integrity check passed; no half-written completed records.

At eight workers the interrupted run saved **3.024 valid distinct-text Jev results/s**.
It produced **zero newly finalized rows**, so new completed-row throughput was
0 rows/s over this attempt. This is not an end-to-end capacity measurement: the
deterministic workflow waits for all Jev outcomes before fallback selection and
final completion. Counting 1,436 imported/computed cache records as new throughput
would be misleading.

Measurement/source files: artifacts/analysis-10000-final/measurements.json,
calls.jsonl, state.sqlite3 and stopped-gate-report.json. The latter lists the seven
local request IDs/review IDs without key material. Reproduce the offline report
with python -m pipeline.analysis_stopped_report.

## Provisional 100k enrichment projection

The saved scope remains 100,041 original IDs / 77,913 distinct texts. There are
**143 completed same-hash scope texts** available, leaving **77,770** new scope
texts at this stopped gate; the retained terminal A/B text is outside this scope.
The 79 partial Jev results are saved but not counted as completed cache records.

Cost estimate uses measured Jev input spend from the 79 valid new calls and the
Luna cost/routing mix from the last complete final-hash A/B (including charged
failures). Estimated scope enrichment: **$4.510468 without development reuse**;
**$4.502190 incremental** with currently completed scope cache, or **$6.753284**
with a 50% allowance. This is a hybrid provisional estimate, not a full analysis
measurement or worst-case paid envelope. It excludes finishing analysis_10000,
unresolved bills, future verification and group/memo work. Input/routing/cache mix
may differ, and completing analysis would change the reusable scope count.

There is no refreshed full final-hash eight-worker timing measurement. The older
complete eight-worker slice measured 12.085 distinct texts/s under the same Jev-v3
but older Luna-v1/policy hash. Applying that rate to 77,770 texts gives **1.788 hours**,
excluding verification/group/memo and operational interruptions. This remains a
prior-run scenario, not a validated current-hash or current-connectivity forecast.

## Resume gate

Stop here. Reconcile the seven unknown provider outcomes/charges before releasing
their held work or retrying. Successful Jev responses, final cache records, original
sources and call provenance are preserved under the same hash. Any recovery must
be explicitly reviewed and approved; it must account for existing known spend and
retained reservations within the approved budget. No automatic resume, new verifier,
golden evaluation, 100k, group or memo call is authorized or dispatched here.
Gate verification: 120 tests passed, ruff and dependency checks passed. Runtime
configuration still matches the final frozen hash; the paid process exited.
