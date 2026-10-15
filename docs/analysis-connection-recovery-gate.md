# Analysis connection recovery gate — 2026-10-14

No provider dashboard was consulted and no API call was made for this recovery.

All seven failures were TypeSafe Jev requests to `https://api.typesafe.ai/v1/systemone`.
The exact retained application exception was `ProviderError: Timeout/connection outcome unknown; reconcile before retry`.
The transport caught either `TimeoutError` or `urllib.error.URLError`, then discarded the underlying exception and message (`from None`). Consequently those exact underlying types/messages cannot be reconstructed. No HTTP status, response or usage was received.

Per-call timestamps were not logged. The measurement file was written at 2026-10-14 22:58:16.669065 UTC after a measured 26.122006-second run (approximate start 22:57:50.547059 UTC). Failed dispatches were adjacent calls 77–83, each lasting 21.594–21.625 seconds: consistent with an early-run connection burst, not failures distributed over a long run. Exact per-call start/end times are unavailable. Subsequent calls now store UTC timestamps and redacted transport exception diagnostics.

The eight workers share an HTTPTransport wrapper, but it holds only keys and timeout. The installed Python urllib implementation creates a fresh HTTPConnection and forces `Connection: close` for every request. There is no persistent connection pool and no configured pool size; up to eight independent connections can be in flight. Likely cause is transient network/connection establishment or upstream reachability failure; similar 21.6-second durations suggest a transport connection timeout. Eight-worker connection churn may amplify it, but concurrency and the exact root cause are unproven. Recommend two workers for the reviewed resume.

## Offline settlement

All seven reservations were settled at full reserved worst case, total $0.001561182. Their failed events now contain reason `connection error, charge unknown, accounted as charged`, preserving the previous error and leaving usage null. These are pessimistic accounted charges, not measured provider billing. Settlement is idempotent; seven held jobs were released and no leases remain. Completed records and 79 valid newly saved Jev stages were preserved.

Known invocation usage $0.003852030 plus pessimistic settlement $0.001561182 = $0.005413212 accounted. Project ledger now $0.299776650 spent/accounted, $0 reserved, against $10. Original $1.50 invocation approval leaves exactly **$1.494586788**.

## Policy and proposed resume

Unknown-charge outcomes (including transport connection failures) are pessimistically settled before retry, on both Jev and Luna paths. Up to three uncertain attempts per item/stage, exponential backoff 1s, 2s plus up to 0.5s jitter (30s ceiling); at most four total attempts per item/stage including the single permitted invalid-output repair. Previously accounted failures count toward attempt limits. Exhausted items are terminally failed and excluded from calibration; unrelated items continue. Existing terminal item failure monitoring remains.

A separate shared call-health window stops new admissions only when unknown-charge failures exceed 5% of the last 100 completed call outcomes, minimum 20 observations. The interrupted attempt had 7/86 (8.14%); it remains stopped. The proposed user-approved resume explicitly resets this operational circuit breaker for a new invocation, retaining the full old audit trail. No automatic restart occurs. In-flight requests are settled and persisted when a stop occurs.

Proposed scope: remaining analysis_10000 enrichment only, two workers, unchanged final label_config `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`. Reuse 1,436 completed rows and 79 saved new Jev stages; retry seven released jobs. Up to 7,890 remaining distinct Jev inputs; at most 1,545 Luna review IDs (fallback quota remains 796 from the original tranche, plus long-text extraction). Conservative call ceiling with retries/repair is 37,733 future calls, versus the original full-run ceiling 19,028. The larger retry allowance does not authorize more spend: **the hard future cap is $1.494586788**, including every pessimistic charge and outstanding reservation. Actual call count will be lower or admission will stop at the cap. A cap stop remains atomic, latched and resumable under the same hash, with no automatic resume. No verifier, golden evaluation, 100k or downstream work is included. Wait for explicit yes.

Machine-readable receipts and proposal: `artifacts/analysis-10000-final/connection-recovery-report.json`, `docs/analysis-10000-resume-proposal.json`. Previous stopped measurements remain historical snapshots; this receipt supersedes their unsettled-reservation status.

## Subsequent user approval: eight-worker keep-alive resume

The user superseded the proposed two workers with eight, explicitly reset the health window, and authorized execution conditional on tests passing. The remaining cap stays $1.494586788. A contained standard-library transport change now keeps one HTTPS connection per worker/provider, fully consumes response bodies, reconnects only through the auditable retry path, and closes failed or server-closed connections. Explicit TCP/TLS connect timeout: 15 seconds; read/write timeout: 60 seconds. Diagnostics distinguish `connect`, `send` (request may be partially sent), and `post_send`, plus whether the request completed sending and whether the connection was reused. API keys are redacted; response bodies/authorization headers are never added to diagnostics. Final label hash unchanged. Transport, worker-isolation, retry, budget and regression checks passed (130 tests; lint passed) before dispatch. `pipeline.analysis_resume` enforces the exact remaining cap and refuses any automatic second resume.

### Auditing-overhead maintenance correction

The resume wrapper initially added `Calls.max_calls`, duplicating the atomic BoundedTransport ceiling with an expensive full audit-log scan before every request. Admissions were manually paused after 1,653 calls / 272.714231 active seconds / $0.080329200 reported usage. All in-flight calls drained; zero connection failures, outstanding reservations, held leases or new terminal rows remained. The manual stop marker omitted the ledger's expected `cause` field, producing `KeyError: 'cause'`; the exact measurement is preserved in `resume-maintenance-segment.json`. This was a maintenance stop, not a budget-cap or provider stop.

The duplicate scan was removed. The existing BoundedTransport call ceiling and Ledger monetary admission guard remain. Tests and lint passed again. Continuation uses the **same invocation ID and $1.494586788 total cap**, deducts prior attempts from its remaining call ceiling, preserves the existing call-health window and all saved results, and only removes the explicitly identified manual maintenance latch. The old failed connection attempt's seven charges remain in their separate historical invocation. No cap stop was reset and no completed stage was repeated. The final report includes both active timing segments; production timing is normalized by actual scored texts to correct for saved scores.
