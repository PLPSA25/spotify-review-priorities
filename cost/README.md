# Offline cost replay and explicit paid pilot

Default: `python -m pipeline cost`. No API key or network is needed. It recomputes saved
usage using editable dated rates.csv and writes usage.csv, replay.json, jev_usage.jsonl
and report.md. Until a real pilot exists, it reports awaiting_real_cold_warm_pilot and
unknown measured values; there are no fabricated pilot outputs.

Plan: `python -m pipeline cost --plan-pilot`. This is offline. Review pilot_plan.json,
the exact calls and worst-case cost; execution requires an explicit yes for that step.

After approval only:

```powershell
python -m pipeline cost --execute-pilot --confirm-spend --approved-plan cost/pilot_plan.json
```

Cold mode uses the unchanged cost_100.csv, an empty result store and one worker. It
includes Jev, Luna extraction/fallback packed up to 20 (configurable, max 50), a blinded
10-review pilot verifier, group naming, deterministic ranking/claims and grounded memo.
Only missing/invalid enrichment IDs get individual repairs; valid siblings are saved.
The pilot stops on transient errors rather than spending on automatic transient retries;
one invalid-output repair remains available. Every attempt is logged and charged/reserved.
The approved maximum call count and project/invocation budget stop additional admission.

Warm mode reuses completed enrichment and saved downstream artifacts; a transport guard
forbids all new model calls. It measures incremental wall time and reports zero calls only
if that actually occurred. If warm reuse fails, it stops and reports the failure.

Artifacts: pilot_records.jsonl, pilot_calls.jsonl, measurements.json, usage.csv, rates.csv,
report.md/replay.json, verifier.json, business.json, membership.csv, ranking.csv, claims.csv.
Each original pilot ID has a final status; unfinished work is disclosed. Cache provenance
is direct. The shared project ledger also includes separately reported provider preflight.

Formula: billable units × rate in actual tier, summed by mutually exclusive input,
cached-input, cache-write and output categories. Jev output is free; reasoning already
in output is not added again. Local-compute costs remain unknown until measured.
Rates are USD per million tokens, dated 2026-10-13, with official source links. Cache-write
pricing uses the documented $0.125/M assumption; actual receipt reconciliation is pending.

Test: doubling API rates with fixed usage doubles API spend and leaves measured time
and local costs unchanged. Projected volumes do not change the recorded 100-review run.
Base/conservative scenarios show approved 100k scope alongside full-corpus comparisons,
with fixed naming/memo overhead once and a declared 500-review final verifier sample.
Conservative scenarios increase variable work 50%; throughput extrapolation is estimated,
not a measured worker-count speedup. Full-corpus scenarios are not the project target.

The report includes every Jev call's billed input tokens and the saved-sample 100k cost.
If that Jev projection exceeds $4, propose jev-v2 with deduplicated rules before the
500-review run. Keep v1 evidence, evaluate/approve any additional paid experiment separately,
and freeze the final label_config before checkpoint_500. Never mix old/new result caches.

The separately approved v2 measurement used 1,003 input tokens, missing the <=1,000 target
by three. The pilot remains pending. Run `python -m pipeline.budget_projection` offline
to refresh `project_budget.json`: it includes the pilot, checkpoint_500, analysis_10000,
the selected scope, verification, four group/memo runs, retry allowances and actual spend.
It estimates $6.88 base and $10.35 conservative; the latter exceeds the cap. Only the
synthetic billing is measured; review-length conversion and Luna envelopes are assumptions.
The $10 ledger is a spending stop, not a promise that every retry scenario completes.

Latest status (2026-10-14): pilot recovered successfully through a separately approved memo-only continuation. Original cold failure and two failed memo calls remain logged. Warm replay completed with zero model calls. Pilot cost $0.007171879; project ledger spend $0.007398385, reservations zero. Observed-pilot-mix full-project estimates are $4.41 base/$6.60 conservative; older planning sensitivity estimates remain available. Phase 4 gate is pending; no checkpoint_500 calls are authorized.
