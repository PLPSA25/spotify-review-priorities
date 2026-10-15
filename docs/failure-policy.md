# Terminal item failures and systemic admission stop

Malformed outputs receive the existing one permitted repair. If invalid afterward,
the failed call stays in the audit log. Enrichment quarantines the distinct-text job
and its aliases with reason; verification saves terminally_failed and excludes it
from calibration. Processing continues. Valid siblings in batches remain saved.

At each finalized distinct enrichment job / verifier review ID, record success or
terminal failure once. Stop when terminal failures exceed 5% of the last 100 finalized
items, after at least 20 observations; exactly 5% continues. No automatic extra paid
retry follows a terminal failure or systemic stop. The three controls are editable in
config.toml; they are outside label_config and do not change valid labels.

Recovery reuses persisted valid and terminal verifier outcomes and seeds its monitor
with prior valid records. The generic enrichment monitor starts fresh per invocation;
it does not reconstruct historical chronological windows on resume. That limitation
must be addressed before a large unattended resume if cross-invocation systemic
failure persistence is required. Existing saved terminal jobs never get silently
retried. Spend caps, unknown-charge reconciliation, auth/model/config/integrity errors
remain mandatory independent stops. Final artifact 'complete' means every requested
verifier item finalized; 'all_valid' distinguishes zero terminal failures.
