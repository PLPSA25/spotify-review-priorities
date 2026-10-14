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
