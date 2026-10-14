# Approved decisions and current phase boundary

Approved 2026-10-13: deliberate 100k partial run; no full-corpus target. Save the complete
nonempty-ID permutation before selecting its first N; union golden IDs. Preserve all
source IDs and direct exact-text cache provenance. Disclose partial scope in final
README, memo and run.json. Extra run.json keys are tolerated by the supplied checker.

Confirmed planning rates: Jev $0.042/M input, free output; Luna standard $0.10/M input,
$0.50/M output, $0.01/M cached input. Project-wide API cap $10. Paid provider preflight
and pilots require separate confirmation. No paid calls in Phase 1. Pin jev-1.13.0;
stop if unavailable. Use gpt-6-luna, log returned model string and flag changes.
TypeSafe console limits: 80 requests/s, 100,000 input tokens/s; recheck in Phase 4.
SDK retries must be coordinated with the shared ledger so no attempt escapes accounting.

Verifier: 500 random classified reviews excluding golden, batches of at most 50;
human disagreement review capped near 20. Each full run must have at least one succeeded
group-role call, even if existing group names are cached. Log enrich/verify/group/memo.

Deployment: reuse Vercel + Neon. Backend reads Postgres with a read-only role.
Recommendations are generated offline and stored. Disable Vercel Deployment Protection
and verify signed-out/incognito access before submission. No live dashboard model calls.

Class 7 date: unknown; treat the working 500-review checkpoint as urgent.
Deadline: October 20, 2026, 11:59 pm America/Los_Angeles.

Phases 1 and 2 approved; Phase 3 authorized and must stop at its gate. Jev request dispatch
is capped at 60/s for headroom below the console's 80/s limit. PDFs are ignored.
Phase 3 gate includes the interactive human labeler and declared harm/language rules.
Remaining phases after Phase 3 approval: provider preflight and measured calculator;
500/10k runs and evaluation; approved 100k run and recorded resume;
group/rank/claims/memo; deployment; final grading export and self-check.

Standing installation approval: pinned well-known PyPI/npm packages may be installed
in this project only. Global installs, other sources, URL install scripts and paid calls
still need approval. Preserve supplied files and existing ignore/example entries.
