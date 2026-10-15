# Scaling gate — October 14, 2026

All three approved disjoint 1,000-row slices from analysis_10000 completed under
frozen label_config `c79a70421de9caad53c9932393f0eb6420f6d80e249cb9097dd5af3eb9d8eba9`.
The runner stopped before remaining analysis_10000. No transfer verifier or golden
agreement evaluation was dispatched. Machine-readable evidence is
`artifacts/scaling/gate-report.json`, per-slice measurements, calls and state files.
Reproduce the descriptive report offline with `python -m pipeline.scaling_report`.

## Measured scaling

- 1 worker: 1,000 completed, 303.410 seconds, 3.296 rows/s, $0.057228236.
- 2 workers: 1,000 completed, 155.997 seconds, 6.410 rows/s, $0.058728234.
- 8 workers: 1,000 completed, 82.747 seconds, 12.085 rows/s, $0.058545713.

Total scaling cost was $0.174502183 against approved combined caps $2.601909406.
Project ledger spend is $0.239921461 against $10, with zero reserved charges.
There were 3,041 attempts across all stages, five failed Jev validation attempts
(Choice differed from the highest-probability option), all successfully repaired;
zero terminal failures. Each slice allocated 100 fallback IDs. Extraction-only IDs
were 74 / 87 / 78. Warm replays issued zero calls and took 0.0011 / 0.0023 / 0.0017 s.

Each slice began with a fresh saved-result cache and unique texts disjoint from
the other slices and checkpoint. Provider prompt caching was uncontrolled; billed
usage remains in the logs. Input populations differ, so observed 1.95x / 3.67x
speedups over one worker do not isolate a causal worker effect. Extrapolating the
8-worker throughput to 77,913 scope texts suggests about 1.79 hours for enrichment
without reuse; this excludes verification, grouping, memo and operational delays.

## Jev-v3 versus Jev-v2

V2 is checkpoint_500: 500 rows, 479 distinct texts. V3 is the 3,000 scaling rows,
all distinct texts. Mean reported input tokens per Jev call increased from
1,018.54 to 1,157.05. V3 has 3,005 Jev attempts including repairs; billed input
per successful distinct text including attempts is 1,158.97.

Recomputed initial triage at confidence 0.60 / margin 0 flags 181/500 (36.2%)
for v2 and 2,014/3,000 (67.13%) for v3, a 30.93 percentage-point increase.
V2 lacked language/context answers, so its rate is confidence-only and its
non-English count is unavailable. Its historical final flags used old thresholds.
For v3, core low confidence flags 1,242/3,000 (41.4%); 772/3,000 (25.73%)
are flagged only by auxiliary judgments. Missing context >=0.5 flags 1,369,
overlapping other reasons. Model-identified non-English flags total 265 (8.83%),
including 110 not understood; all 265 remain flagged after fallback.
Final v3 stored flags after fallback are 1,823/3,000 (60.77%). These are distinct
from the initial triage rates; fallback may resolve confidence/context concerns.

Core confidence is the minimum across topic, intent, severity and sentiment;
language confidence does not feed that minimum. Distinct-text distributions:

- V2: mean .6651; p10 .408; p25 .52; median .67; p75 .85; p90 .94; range 0–.99.
- V3: mean .6387; p10 .39; p25 .50; median .64; p75 .79; p90 .92; range 0–1.

Histogram counts for [0,.2), [.2,.4), [.4,.6), [.6,.8), [.8,1] are
5/37/137/156/144 for v2 and 33/287/922/1038/720 for v3. Per-field distributions
are in the gate JSON. Differences combine prompt and population changes and
cannot establish a prompt-only effect. Language counts are model judgments.

Calibration should be rechecked on v3 before the remaining analysis_10000 rows:
the large auxiliary-only cohort was absent from the v2 calibration evidence.
Retain the frozen values pending verifier evidence; flag-rate drift alone is not
a reason to tune toward a target rate. These comparisons are not human accuracy.

## Updated cost projection

Measured v3 enrichment averages $0.0000581673943 per distinct text, including
observed repairs, fallback and extraction. For 77,913 distinct texts in the
100k scope, Jev alone projects $3.792566 versus v2's $3.333004; complete
enrichment projects $4.531996 base / $6.797994 with a 50% variable allowance.
683 completed slice texts can be reused in scope after validated same-hash
provenance import, reducing incremental scope enrichment to $4.492268.

The full analysis_10000 has 1,490 IDs inside the 100k scope and 8,510 outside.
Exact-text overlap also allows reuse for additional outside IDs; all 10k work
under the frozen hash would supply 1,995 distinct scope texts. The project
forecast is $5.071544 base / $7.486683 with 50% future-variable allowance:
current spend plus remaining 5,448 development texts and 75,918 scope texts,
three future 500-row verifier passes at historical measured cost including
failures, and two grouping/memo sets at successful pilot overhead.
These forecasts are estimates, not worst-case guarantees or paid authorizations.

## Proposed v3 calibration transfer verifier — not run

`artifacts/scaling/verifier-transfer-sample.csv` contains 500 completed slice
rows selected by seeded SHA256 order (`spotify-v3-transfer-500-v1` plus ID),
excluding golden IDs. Worker-slice composition is 162 / 176 / 162.
Only original texts and the rubric enter the blinded Luna verifier; no first
labels or golden answers. Proposal evidence is
`artifacts/scaling/verifier-transfer-proposal.json`.

Ten initial batches of 50 plus at most one singleton repair per invalid item
produce at most 510 calls. Transient attempts are limited to one. Initial
batch limits are 24,000 input / 10,000 output tokens; singleton repair limits
are 10,000 input / 200 output tokens. Offline byte-plus-overhead preflight passed
for all selected batches and singleton repair envelopes. Conservative rates
are $0.125/M input (including the cache-write bound) and $0.50/M output:
10 × $0.008 + 500 × $0.00135 = **$0.755 worst case**.

After permitted repair, terminal failures are logged and excluded from
calibration; continue unless terminal failures exceed 5% of a rolling 100-item
window after at least 20 finalized items. Spend/auth/unknown-charge integrity
stops remain in force. Compare the same 35 confidence/margin pairs and field
breakdowns, including low-confidence, non-English, missing-context and
auxiliary-only cohorts. Frozen 0.60/0 is the primary transfer check. A new
explicit paid approval is required; stop at its report gate before remaining
analysis_10000 work.
