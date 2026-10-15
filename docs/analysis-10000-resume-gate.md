# Final-hash analysis resume gate

Status: completed_with_terminal_failures. Eight workers, final hash `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`. No further paid work dispatched.

Measured 8558 new completed rows over 842.635s of active execution: **10.156 rows/s** including the initial maintenance segment. Final segment alone: 569.920s / 15.016 rows/s, with saved Jev scores (warm start). Final counts: {'completed': 9994, 'quarantined': 6}. New terminal rows: 5. Pending leases: 0. SQLite integrity: ok.

Connection failures by phase: {'connect': 0, 'send': 0, 'post_send': 0}; retries (including previous-attempt recovery): 54; retry breakdown: {'previous_attempt_connection_recovery': 7, 'new_connection_retry': 0, 'output_repair': 47, 'http_or_other_retry': 0}; total new calls: 8011. Successful reused connections: 7987. Per-worker HTTPS keep-alive, explicit connect/TLS timeout 15s and read/write timeout 60s; failed connections close before the next audited retry. Send failures remain charge-uncertain; no hidden resends.

Resume reported usage cost: $0.467696494; pessimistic new charges: $0.000000000. Resume accounted cost: $0.467696494, below the approved $1.494586788 remaining cap. Both analysis attempts including original seven pessimistic charges: $0.473109706. Project accounted spend: $0.767473144 / $10. Historical seven charges are estimated at reservation cost, not measured provider usage.

100k scope: 100041 IDs / 77913 texts; completed reuse 1994 texts, terminal 1, remaining 75918. Measured resume finalization throughput: 13.983 distinct texts/s. Estimated remaining 100k enrichment: 1.7843803661135247 hours; $4.507158 base, $6.760737 with 50% allowance. Project total including current spend: $5.274631 base / $7.528210 with allowance.

Final-hash eight-worker keep-alive timing. A maintenance pause removed a redundant audit-log scan; its first timing segment is archived. Primary combined rows/s includes both active segments (excludes maintenance downtime). Projection uses optimized-segment Jev seconds divided by texts actually scored in that segment, plus finishing seconds divided by the original pending tranche. This corrects for all saved Jev scores and avoids treating warm scores as free production throughput. Assumes production mix transfers; excludes exports and future downstream stages. Both analysis attempts, including all repairs and seven pessimistic charges, divided by 7969 new distinct texts. Assumes review lengths, routing and observed billing/cache mix transfer; 50% allowance is an estimate, not a paid envelope. No verifier, golden evaluation, grouping/memo, deployment or retry of terminal scope items included.

This is a measured development gate and an estimated production projection, not approval to start 100k. Stop here.
