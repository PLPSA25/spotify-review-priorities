# Final-hash checkpoint v2/v3 A/B gate — October 14, 2026

**PASS** against the user's criterion recorded before paid v3 results:
topic and intent core-Jev disagreement must each be no more than 3 percentage
points worse than v2, on the same 500 original rows. V2 baseline counts 54/500
topic and 37/500 intent give inclusive limits 69/500 and 52/500. Criterion file:
docs/checkpoint-500-v3-ab-pass-criterion.json; a copy was saved in the paid output
before dispatch. Final hash remains
`21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`.

## Same-row core-Jev result

Both arms use four core answers with identical decoding, excluding language
overrides from this primary prompt comparison. All 500 original IDs / 479 exact
texts have valid Jev outputs, including the item whose later Luna quote failed.
Disagreements against the fixed existing blinded verifier:

- Topic: v2 54/500 (10.8%), v3 53/500 (10.6%); change −0.2 pp — passes.
- Intent: v2 37/500 (7.4%), v3 39/500 (7.8%); change +0.4 pp — passes.
- Severity exact: 64/500 (12.8%) → 68/500 (13.6%); +0.8 pp.
- Severity beyond ±1: 5/500 (1.0%) → 4/500 (0.8%). Within ±1 agreement
  is 99.0% → 99.2%.
- Sentiment sign: 40/500 (8.0%) → 42/500 (8.4%); +0.4 pp.
- Sentiment absolute difference >.25: 61/500 (12.2%) → 56/500 (11.2%).

Topic has four improved / three regressed rows; intent two improved / four
regressed. Descriptive exact-text-cluster bootstrap 95% change intervals are
−1.22 to +0.81 pp for topic and −0.41 to +1.44 pp for intent. The declared
pass criterion uses observed rates, not post-hoc interval requirements. Severity
exact has four regressions and no improvements; this is disclosed even though
severity was not a pass endpoint. All fields, paired changes and unique-text
summaries are in artifacts/checkpoint-500-v3-ab/paired-details.json. These are
verifier comparisons, not human accuracy or golden evaluation.

## Completed enrichment, failures and actual cost

499 completed / one quarantined after both allowed quote attempts failed exact
substring validation. Its Jev classification was valid; no additional recovery
or retry was dispatched. Partially valid batch siblings persisted; the singleton
repair failed. One failed whole request and one initially invalid item are logged.

Measured wall time 73.835711 seconds; 485 requests: 479 Jev and six Luna
(five initial enrichment batches plus one singleton repair). Total API cost
**$0.027641052**, against approved invocation cap $0.431:
Jev $0.023267202; fallback $0.002567000; extraction $0.001806850.
Project ledger spend **$0.294363438 / $10**, zero reserved.

The secondary final-enrichment comparison uses the same 499 successfully
completed rows in both arms. Counts v2 → v3: topic 54→55, intent 34→40,
severity exact 59→59, severity beyond ±1 4→1, sentiment sign 37→37,
sentiment >.25 54→54. This comparison also changes thresholds/allocation,
Luna reason prompt/schema and context persistence; it is not a Jev-prompt-only
effect. Final v3 flags 322/499 (64.53%); overlapping explicit reason counts:
language_non_english 18, language_not_understood 17, missing_context 244,
low_confidence 141. All completed records have valid reason lists.

The initial automated report incorrectly selected only completed final records
for the core comparison and declared it incomplete. That reporting error was
corrected offline using all 500 succeeded core predictions; the criterion and
labels/calls did not change. The initial report is retained as paired-report-initial.json,
with the corrected paired-report.json explicitly documenting the separation of
core and final denominators. Regression coverage now prevents this mistake.

## Analysis_10000 cost gate — proposal only

Use 8 workers and the final hash above. Input has 10,000 IDs / 8,448 distinct
texts. Read-only backup of the final-hash A/B state, then checksum-validated
analysis ingestion, retains original source hashes, successful call evidence,
direct cache origins, reasons and terminal failures. Imported calls are historical
provenance, not newly billed work.

- 499 original completed IDs are already present; exact-text propagation supplies
  937 additional aliases, so **1,436 rows / 478 distinct texts are reusable**.
- **One row/text remains terminally quarantined**, with no automatic retry.
- **8,563 rows / 7,969 distinct texts need new work**. This includes old-hash
  scaling texts; the historical 3,000 slice results cannot be silently reused.
- New tranche fallback quota is floor(7,969 × .10) = **796**. There are 749
  long new texts, giving at most **1,545 Luna enrichment IDs** before overlap.

New paid bounds: 7,969 initial Jev requests plus at most one repair each; up to
1,545 singleton-equivalent Luna initial requests plus one repair each. Actual
Luna batching uses the configured 20-item maximum and bounded payload packing.
Maximum **19,028 calls**, with one transient attempt and one output repair:

- Jev worst-case $4.160126292.
- Luna worst-case $3.281201750.
- Total **$7.441328042**; proposed invocation cap **$7.442**.

Rates and bounds are pinned: actual canonical UTF-8 payload bytes +2,048 overhead
+1,024 repair allowance; two permitted attempts, Jev $0.042/M input; Luna
max(input/cache-write) $0.125/M input and $0.50/M output, 200 output tokens/item.
Select the 1,545 largest possible Luna singleton envelopes; no cache discount.
The conservative envelope is not an expected bill. Observed A/B-mix extrapolation
is **$0.459857**, with different input lengths/routing as a limitation. Full envelope
spend would bring project total to **$7.735691480**. Ledger admission preserves
the $10 hard cap and unknown-charge reservations.

No verifier refresh, golden evaluation, grouping, memo or 100k calls are included.
If all new items complete, analysis accounts for 9,999 completed +one retained
terminal row; any new terminal failures are also retained and reduce completions.
Stop at the full analysis enrichment gate before further paid work.
The runnable command after a new yes is python -m pipeline.analysis_run --confirm-spend.
It pins source/base/config/rates and passing-report hashes, checks reuse counts,
preserves failed work, and enforces per-call/stage/invocation/project bounds.
Machine-readable proposal: docs/analysis-10000-final-proposal.json.
Gate checks: 117 tests passed; ruff and dependency checks passed. No analysis
dispatch occurred while preparing or testing this proposal.
