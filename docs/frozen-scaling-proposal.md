# Frozen-config scaling spend proposal — awaiting yes

Frozen label_config:
`c79a70421de9caad53c9932393f0eb6420f6d80e249cb9097dd5af3eb9d8eba9`.
Source, slice hashes, exact controls/rates and nanodollar envelopes are in
../artifacts/scaling-proposal/plan.json. No scaling API calls have been made.

Three disjoint slices of analysis_10000.csv, each 1,000 original rows and 1,000 distinct
texts, run at 1, 2 and 8 workers. Seeded exact-text ordering; representative original
IDs/source fields preserved. Exclude prior checkpoint text families and golden IDs.
Fresh empty result cache for each slice; shared rate/spend ledger. Provider prompt
cache cannot be reset. Inputs differ, so report lengths/language/routing and treat
this as a practical capacity comparison, not isolated causal worker speedup.

Each slice makes 1,000 initial Jev calls (six questions per call). Fallback quota at
most 100 distinct texts, selected deterministically only after all Jev scores persist.
Long extraction texts: 84/95/87. Initial Luna enrich call bounds use singleton worst
case 184/195/187 IDs, with batching up to 20 normally reducing calls. At most one
invalid-output repair per item, one transient attempt; terminal failures continue
subject to >5% rolling failure stop. No verifier/group/memo calls.

Paid per-slice invocation caps proposed:

- 1 worker: $0.858769558; up to 2,368 calls including repairs.
- 2 workers: $0.879541298; up to 2,390 calls including repairs.
- 8 workers: $0.863598550; up to 2,374 calls including repairs.

Total worst-case rate-based envelope **$2.601909406**, maximum **7,132 calls** including
all repairs. This replaces the earlier $2.474397406 envelope: restored explicit
language/context questions add $0.127512 to the conservative Jev reservation total.
Envelope uses singleton requests, raw UTF-8 byte input +2,048 protocol overhead
+1,024 repair bytes, worst largest permitted Luna singleton costs, maximum 200
output tokens per review, Jev $0.042/M input, Luna max(input/write) $0.125/M input
and $0.50/M output. No prompt-cache discount. Enforce per-call and per-stage envelopes
before dispatch, and retain unknown-charge reservations. Exceeding an envelope stops
admission; it does not silently increase the approved cap or call count.

The runner checks frozen identity, source hashes, rates/controls and fresh outputs
before dispatch. Operational max_workers/runtime invocation caps and one-attempt policy
do not change the label hash. Default $0.50 invocation cap is overridden only by the
three reviewed caps above after explicit yes. Project cap remains $10.
Current project spend $0.065419278; if the entire envelope were spent, accounted total
would be $2.667328684. Provider receipts remain unreconciled.

Estimated spend $0.175925699 base / $0.263888549 conservative mix, not measured under
the frozen prompt: historical per-text costs plus an explicit assumption of four bytes
per added token for the 506-byte prompt addition. Expected routing/token usage must
be refreshed from actual scaling results. Modeled enrichment time 7.10/3.55/0.89
minutes at 1/2/8 workers assumes linear scaling from the old two-worker checkpoint;
new auxiliary judgments, limits and contention can invalidate it. Report actual wall
time, throughput, routing, cache categories, failures and cost at the gate.

## Development-to-100k overlap

Saved 100k prefix plus forced golden IDs contains 100,041 IDs. Of analysis_10000:
1,490 original IDs are inside it, 8,510 outside. Another 2,046 outside IDs have exact
text appearing in scope, so 3,536 development rows / 1,995 distinct development texts
potentially contribute same-text reuse; 6,453 development texts have no scope match.
Counts/source are in development-scope-overlap.json. These are potential cache savings,
not completed/reused classifications. Require frozen hash and direct original succeeded
enrich evidence; do not reuse old checkpoint/pilot hashes.

The three prepared slices are source rows from analysis_10000 and therefore count
toward its later run. After successful saved results, analysis still has 7,000 original
IDs / 5,448 new distinct texts before any further exact-text aliases are accounted for.
Do not run those now. Paid command after yes: python -m pipeline.scaling --confirm-spend.
It executes only these three slices and their zero-call warm checks, then stops at the
scaling gate. The rest of analysis_10000, verification, grouping/memo and 100k require
their later gates and separate spend approvals.
