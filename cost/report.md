# Measured 100-review cost/runtime report

Source: saved pilot calls, usage, measurements and dated editable rates. Provider receipts are not reconciled.

Status: ready
Pilot API spend: $0.007171879
Measured cold/warm wall seconds: {'cold': 58.622409100004006, 'memo_continuation': 5.265658999996958, 'warm': 0.021283199996105395}
Local compute cost: None (unknown is not zero).

Attempts, failures, retries, fallbacks, models and tiers: {'total_attempts': 109, 'succeeded': 107, 'failed': 2, 'fallback_attempts': 1, 'retry_attempts': 1, 'actual_models': ['gpt-6-luna', 'jev-1.13.0'], 'actual_tiers': ['default', 'standard']}
Cold exact-text cache hits: 0; warm completed-result reuse: 100
Provider preflight spend (separate): $0.000184380; accounted project subtotal: $0.007398385

Measured Jev mean billed input tokens per call: 1018.87
Measured Jev billed input tokens per distinct text, including attempts: 1018.87
Projected Jev cost for saved 100k scope: $3.33409516902
Trimmed Jev prompt proposal required above $4: False

Per 1,000 input rows: $0.071718790
Per completed record: $0.00007171879
Measured input throughput: 1.7058323179692245 rows/s

Every Jev call's measured input token count is in jev_usage.jsonl. Charged categories map to request IDs in usage.csv.
Doubling API rates doubles replayed API spend; measured time/local compute remain unchanged.

## Scope and projections

These are estimates, not full-run measurements. Fixed grouping/memo overhead is counted once.
- 100k sample with exact reuse / base: $4.02463773002; estimated model-stage seconds None; exceeds $10: False.
- 100k sample with exact reuse / conservative: $6.036411520030; estimated model-stage seconds None; exceeds $10: False.
- 100k sample without exact reuse / base: $5.16067907114; estimated model-stage seconds None; exceeds $10: False.
- 100k sample without exact reuse / conservative: $7.740473531710; estimated model-stage seconds None; exceeds $10: False.
- full corpus with exact reuse / base: $24.88266068306; estimated model-stage seconds None; exceeds $10: True.
- full corpus with exact reuse / conservative: $37.323445949590; estimated model-stage seconds None; exceeds $10: True.
- full corpus without exact reuse / base: $33.93998232986; estimated model-stage seconds None; exceeds $10: True.
- full corpus without exact reuse / conservative: $50.909428419790; estimated model-stage seconds None; exceeds $10: True.

Full-corpus scenarios are comparison only. Approved target remains the saved 100k prefix plus forced golden IDs.
Projection sensitivity: conservative variable work is 50% higher; it is not an extra measured experiment.
No unmeasured prompt-cache discount, concurrency speedup or Batch/Flex discount is assumed.
Missing usage request IDs: []

Inspect measurements.json for statuses, unique texts, workers, batches and stage timing; verifier.json for blinded disagreements; business.json and claims.csv for grounded memo evidence.

## 2026-10-14 analysis connection recovery (offline)

Seven unknown TypeSafe connection outcomes were pessimistically accounted at full reserved cost, $0.001561182; this is not measured provider usage. Original analysis invocation known usage $0.003852030 plus these accounted charges totals $0.005413212, leaving exactly $1.494586788 of its $1.50 approval. Project ledger: $0.299776650 accounted/spent, $0 reserved, $10 cap. No provider dashboard or paid request was used for settlement. Prior pilot projections above remain historical. Current receipt: `artifacts/analysis-10000-final/connection-recovery-report.json`; resume proposal and policy: `docs/analysis-connection-recovery-gate.md`. Resume requires a new yes.

## Subsequent approved eight-worker resume — gate reached

Final-hash analysis_10000 is resolved: 9,994 completed, six terminal failures (five new invalid-output failures after repair), zero pending/leased work. Resume reported usage cost $0.467696494, no new pessimistic charges, zero recorded connection failures. Both analysis attempts including the original seven pessimistic charges total $0.473109706; original $1.50 approval has $1.026890294 unused. Project accounted spend $0.767473144 / $10, reserved $0. The unused invocation amount is not approval to start another phase.

Timing: 8,558 new completed rows / 842.634709 active seconds across both resume segments = 10.156240 rows/s. Final optimized segment 569.920479s / 15.016130 rows/s has saved-score reuse and is not a cold throughput figure. Maintenance removed a duplicate full-log scan without repeating any completed Jev stage. Production projection normalizes actual scored texts separately from finishing work.

Remaining 100k enrichment estimate: 75,918 texts, 1.784380 hours, $4.507158 base / $6.760737 with 50% cost allowance. Project total including current spend: $5.274631 base / $7.528210 with allowance. One terminal text already in scope is retained separately; projections exclude future verifier/group/memo/deployment and its retry. These are mix-dependent estimates, not a paid envelope. Current full evidence: `docs/analysis-10000-resume-gate.md` and `artifacts/analysis-10000-final/resume-gate-report.json`. Stopped at gate; no 100k or downstream calls dispatched.

## Golden collection and fallback-options gate — October 14, 2026

Approved golden cap $0.076; enforced reviewed envelope $0.075555748. All50 predictions complete (six reused IDs,44 new distinct texts):46 requests /9.382519s /$0.002603841 reported usage, comprising Jev $0.002137716 and Luna $0.000466125. Zero failed calls/new terminal records. Project accounted spend now **$0.770076985 / $10**, reserved $0. By provider: TypeSafe $0.585554760; OpenAI $0.184522225. These are project ledger totals, not current provider/org balances.

Post-golden 100k scope:2,038 reusable completed texts, one retained terminal text,75,874 pending texts. Development-only modeled options:10% fallback $4.504546 /1.783346h /$6.80 proposed cap;20% $4.852176 /1.891450h /$7.28;30% $5.192665 /1.998126h /$7.79. Recommended20% was frozen before golden evaluation and is **not applied**. It adds about $0.35 /6.5min vs10%; it is not a measured human-accuracy gain. Hash remains unchanged at all three operational caps.

At the full proposed $7.28 production cap, project total would be $8.050076985, leaving $1.949923015 for later separately approved work. TypeSafe balance is user-reported $10.41; predicted production Jev≈$3.71 (conservative≈$5.56). OpenAI org limit is$20, actual remaining org headroom unverified: project OpenAI spend alone cannot establish it. Expected production Luna at20%≈$1.15 /$1.72 with1.5× allowance. Recheck actual balances/limits and disk before any run.

Evidence: `docs/golden-final-evaluation-gate.md`, `docs/fallback-options-development.json`, `docs/100k-run-proposal-draft.json`, and the actual golden `calls.jsonl`/measurements. Entity accuracy is excluded by design. No100k, extra verifier, group or memo call was made; stop at gate.


### Offline pre-production clarification

Caching means the pipeline's exact-text **result cache** under an unchanged label_config, not provider prompt caching. OpenAI reports 0% prompt-cache hits; no prompt-cache savings are claimed or implemented. Saved Jev stages are reused on resume.

Fallback and verifier both use Luna: blinded verification hides Jev output but remains correlated with fallback. Verifier-agreement gains partly reflect self-agreement; the 20 owner verdicts are independent human evidence, not a random accuracy estimate. The owner approved a 20% fallback cap for 100k pending the prompt decision; the offline recommendation keeps the frozen prompt. Current config remains 10% until an approved production setup. No paid start is authorized.

Updated user-reported preflight: OpenAI October spend $0.18 / $20 org limit; prepaid balance $9.82 is the real ceiling before unposted charges. TypeSafe $10.41. Recheck remaining credits/limits before dispatch. See docs/offline-preproduction-gate.md and docs/100k-run-plan-draft.md.
