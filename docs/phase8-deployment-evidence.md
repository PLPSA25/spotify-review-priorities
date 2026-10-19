# Phase 8 deployment evidence

Evidence reviewed offline on 2026-10-19. Live URL: https://spotify-review-priorities.vercel.app.
Pier reports the site is live. This report validates Pier's saved HTTP responses;
no network request, Vercel command, credential-file read or commit was performed.
Saved responses establish the captured result, not continuous availability.

## Snapshot identity and database source

- Snapshot ID: `2d29566238c93179d4518f4eb08cc5c0e45e0f125fe1a9d103a0ce0ff6b0282e`.
- `meta.source`: `neon`.
- `meta.snapshot_id`: exact match to the top-level snapshot ID.
- Import time (UTC): `2026-10-19T12:00:03.412Z`.
- Database size: **8,257,536 bytes**, reported by Pier from the import measurement;
  not independently remeasured during this offline review.
- Runtime variable: **`DATABASE_URL_READONLY`**, **Production**, **Sensitive**.
  This records the requested/owner-reported setting; the console was not inspected.

Node executed the existing `checkedSnapshot()` and `canonical()` functions from
`web/lib/integrity.ts` on `artifacts/phase8/dashboard.json` and
`web/.local/dashboard.json`. Both validate. The canonical payload SHA-256 equals
`2d29566238c93179d4518f4eb08cc5c0e45e0f125fe1a9d103a0ce0ff6b0282e`, which equals both snapshot IDs. The canonical payloads are exactly equal;
response-level source metadata is outside the hashed payload.

The payload contains 660,622 original rows: 237,722 completed (77,874 direct
originals plus 159,848 cache reuses), 422,845 out-of-scope rows, 42 terminal rows
and 13 empty rows. There are 660,609 nonempty rows and 185,396 needs-review rows.
These counts exactly match the local validated snapshot.

Both rankings contain 35 issues. Baseline membership totals 70,239 complaints/
cancellations and severity_sum 154,528; random-prefix membership totals 43,042
and severity_sum 109,940. These are different scopes, not competing totals for
the same population. All means agree with severity_sum/count, rounded half-up
to six decimal places.

Human-evaluation figures in the UI are a bundled saved summary from
`web/lib/human-check.json`, not a runtime database read. The captured report
snapshot and claims are the database-backed data verified here.

## Saved HTTP headers

| Saved endpoint response | HTTP status | X-Dashboard-Data-Source | X-Dashboard-Snapshot-Id |
|---|---|---|---|
| Dashboard JSON | 200 | neon | Exact match |
| Baseline claims CSV | 200 | neon | Exact match |
| Secondary claims CSV | 200 | neon | Exact match |

Inputs: `artifacts/phase8/dashboard.headers.txt`,
`artifacts/phase8/claims-baseline.headers.txt`, and
`artifacts/phase8/claims-secondary.headers.txt`. All three snapshot headers
exactly equal the ID above. The dashboard JSON meta agrees with its headers.

## Claims and grading-export comparison

- Saved baseline claims CSV: **140/140 parsed rows exactly match** the dashboard's
  baseline claims, the local snapshot, and `docs/phase7/claims.csv`.
- Saved secondary claims CSV: **12/12 parsed rows exactly match** the dashboard's
  secondary claims, the local snapshot, and `docs/phase7/secondary-claims.csv`.
- Baseline ranking: **35/35 rows exactly match** `docs/phase7/ranking.csv` for rank,
  issue ID, complaint_count, severity_sum, mean_severity and priority_score.
- Secondary ranking: **35/35 rows exactly match** `docs/phase7/sample_ranking.csv`
  for those same fields.
- `grading/ranking.csv` and `grading/claims.csv` are currently **header-only**:
  zero ranking rows and zero claims rows. Consequently every published baseline
  issue/claim is missing there; there are no existing numeric grading rows to
  call equal or numerically different. Secondary ranking/claims are separate
  analysis and must not be compared as if they were the baseline.
- `grading/run.json` still declares business stages pending. The final export
  must replace this interim state and include Phase 7 evidence.

### Per-issue comparison

Each numeric cell is **complaint_count / severity_sum / mean_severity**.
"Exact" compares live versus local validated snapshot and the corresponding
Phase 7 ranking. "Missing" means no baseline issue row exists in the current
`grading/ranking.csv`; the current `grading/claims.csv` also has no issue claims.
The table follows baseline order; secondary rank order was checked separately.

| Issue | Live baseline: count / sum / mean | Live random prefix: count / sum / mean | Local/Phase 7 comparison | Current grading baseline |
|---|---|---|---|---|
| `other--unspecified` | 36225 / 58636 / 1.618661 | 12002 / 20564 / 1.713381 | Exact, both scopes | Missing |
| `cross-topic--free-tier-premium-controls` | 4444 / 13877 / 3.122637 | 4440 / 13865 / 3.122748 | Exact, both scopes | Missing |
| `usability--ad-interruptions` | 6037 / 12965 / 2.147590 | 4088 / 9071 / 2.218933 | Exact, both scopes | Missing |
| `usability--unspecified` | 4228 / 10500 / 2.483444 | 3784 / 9609 / 2.539376 | Exact, both scopes | Missing |
| `billing--premium-upgrade-mentions` | 3152 / 8784 / 2.786802 | 3123 / 8705 / 2.787384 | Exact, both scopes | Missing |
| `playback--unspecified` | 2727 / 8688 / 3.185919 | 2558 / 8189 / 3.201329 | Exact, both scopes | Missing |
| `playback--stops-skips-wont-play` | 1674 / 5590 / 3.339307 | 1651 / 5513 / 3.339188 | Exact, both scopes | Missing |
| `usability--queue-playlist-controls` | 1582 / 4705 / 2.974083 | 1582 / 4705 / 2.974083 | Exact, both scopes | Missing |
| `access--login-credentials` | 1136 / 4466 / 3.931338 | 1021 / 4008 / 3.925563 | Exact, both scopes | Missing |
| `catalog--unspecified` | 1126 / 3115 / 2.766430 | 1118 / 3093 / 2.766547 | Exact, both scopes | Missing |
| `billing--unspecified` | 1044 / 2536 / 2.429119 | 1018 / 2501 / 2.456778 | Exact, both scopes | Missing |
| `playback--buffering-connectivity` | 664 / 2173 / 3.272590 | 656 / 2151 / 3.278963 | Exact, both scopes | Missing |
| `playback--crashes-freezes` | 596 / 2132 / 3.577181 | 566 / 2013 / 3.556537 | Exact, both scopes | Missing |
| `billing--price-paywalls` | 836 / 2120 / 2.535885 | 764 / 1985 / 2.598168 | Exact, both scopes | Missing |
| `downloads--download-failure` | 627 / 2059 / 3.283892 | 608 / 1985 / 3.264803 | Exact, both scopes | Missing |
| `catalog--lyrics` | 663 / 1905 / 2.873303 | 646 / 1855 / 2.871517 | Exact, both scopes | Missing |
| `usability--interface-navigation` | 721 / 1814 / 2.515950 | 708 / 1788 / 2.525424 | Exact, both scopes | Missing |
| `access--unspecified` | 417 / 1616 / 3.875300 | 406 / 1572 / 3.871921 | Exact, both scopes | Missing |
| `usability--shuffle-controls` | 386 / 1017 / 2.634715 | 386 / 1017 / 2.634715 | Exact, both scopes | Missing |
| `catalog--search-results` | 304 / 934 / 3.072368 | 304 / 934 / 3.072368 | Exact, both scopes | Missing |
| `billing--subscription-cancellation` | 288 / 827 / 2.871528 | 288 / 827 / 2.871528 | Exact, both scopes | Missing |
| `downloads--offline-access` | 182 / 584 / 3.208791 | 180 / 578 / 3.211111 | Exact, both scopes | Missing |
| `playback--audio-quality-volume` | 207 / 575 / 2.777778 | 205 / 571 / 2.785366 | Exact, both scopes | Missing |
| `billing--charges-refunds` | 177 / 560 / 3.163842 | 177 / 560 / 3.163842 | Exact, both scopes | Missing |
| `catalog--availability-selection` | 191 / 553 / 2.895288 | 191 / 553 / 2.895288 | Exact, both scopes | Missing |
| `catalog--discovery-recommendations` | 193 / 489 / 2.533679 | 193 / 489 / 2.533679 | Exact, both scopes | Missing |
| `downloads--unspecified` | 104 / 349 / 3.355769 | 104 / 349 / 3.355769 | Exact, both scopes | Missing |
| `playback--background-resources` | 109 / 330 / 3.027523 | 109 / 330 / 3.027523 | Exact, both scopes | Missing |
| `support--unspecified` | 75 / 153 / 2.040000 | 43 / 89 / 2.069767 | Exact, both scopes | Missing |
| `access--account-security` | 31 / 149 / 4.806452 | 30 / 144 / 4.800000 | Exact, both scopes | Missing |
| `access--signup-registration` | 36 / 136 / 3.777778 | 36 / 136 / 3.777778 | Exact, both scopes | Missing |
| `downloads--missing-downloads` | 25 / 97 / 3.880000 | 25 / 97 / 3.880000 | Exact, both scopes | Missing |
| `support--resolution-quality` | 18 / 49 / 2.722222 | 18 / 49 / 2.722222 | Exact, both scopes | Missing |
| `support--contact-response` | 11 / 34 / 3.090909 | 11 / 34 / 3.090909 | Exact, both scopes | Missing |
| `access--account-restrictions` | 3 / 11 / 3.666667 | 3 / 11 / 3.666667 | Exact, both scopes | Missing |

### What can change at final export

`grading/` will be re-exported once at final submission. Its empty ranking and
claims files should become populated with the approved baseline; missing group,
verify and memo call evidence, call/token totals and related file hashes will
change when Phase 7 calls are included. Secondary claims remain explicitly
separate from baseline claims.

A refresh alone should not change frozen classification counts, either ranking's
issue counts/severity sums/means, or the approved claims shown above. Any such
numeric change requires reconciliation against the frozen sources and approval;
it must not be silently described as an export-only change. A changed payload
would require a new snapshot ID/import and renewed deployed verification.

## Re-import rule

After final grading re-export, regenerate the snapshot offline and validate it.
The payload contains hashes of `grading/records.jsonl.gz` and
`grading/ingestion.json`, plus record-derived summaries/classifier ID and
ingestion-derived review dates. Changed archive bytes alone can therefore change
the regenerated snapshot ID even when displayed figures stay identical. Grading
call counts, token totals, cost, and the grading run/manifest are not inputs.

If anything inside the regenerated payload changes, rerun offline validation
(`checkedSnapshot` and `npm.cmd run import:snapshot` without confirmation), then
re-import from `web/` using the owner's private credential file and
`npm.cmd run import:snapshot -- --confirm-import`. Run `npm.cmd run verify:reader`,
re-save the live dashboard/claims responses and headers, and update this document
with the new identity/import time and comparisons. Pier performs the connected
steps separately; this rule does not authorize network access in an offline task.
Otherwise the live snapshot ID must still equal the repo's regenerated snapshot
ID. From the repository root, compare a freshly saved live response offline:

```powershell
node -e "const fs = require('node:fs'); const read = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '')); const live = read('artifacts/phase8/dashboard.json').snapshot_id; const repo = read('web/.local/dashboard.json').snapshot_id; if (live !== repo) throw Error('Snapshot IDs differ'); console.log('MATCH', repo);"
```

## Reader verification and resolved failures

Saved transcript: [phase8-reader-verification.txt](phase8-reader-verification.txt).
It records a reader-authenticated connection, successful SELECT of the matching
snapshot and UTC import time, and **7/7 expected privilege denials**: INSERT,
UPDATE, DELETE, CREATE TABLE in dashboard, CREATE TABLE in public, CREATE SCHEMA,
and CREATE TEMP TABLE. Dangerous role flags are false, LOGIN is true, INHERIT is
false, direct membership count is zero, the membership list is empty, and
neon_superuser membership is false. Defaults are read-only on and timeout 5s.
The probes deliberately turn off the transaction's read-only default so their
42501 denials test grants. Grants are the boundary; defaults are secondary.

An early verifier run failed with **25001**. The former script submitted
informational statements and probe transaction in one simple-query message.
The inferred cause was a prior query snapshot preventing the read-only setting
change. The fix splits the SQL at `-- ===== TRANSACTION PROBES =====` into two
separate query calls. Part 2 starts with BEGIN and the transaction setting before
its queries. Marker validation, sanitized output and the 7/7 requirement remain.
Connection closure in finally aborts a transaction if the probe part fails.

The reader-role SQL previously failed with **42501** when restating restricted
role attributes with ALTER ROLE as neondb_owner. The specific privilege cause
was inferred, not established by that code alone. The fix retains safe CREATE
ROLE attributes and replaces the second attribute-changing ALTER ROLE with a
fail-closed pg_roles check. It removes the broad sweep of unrelated/Neon-managed
schemas and retains effective-privilege checks before COMMIT. Current files:
`web/db/01-reader-role.sql`, `web/db/02-verify-reader.sql`, and
`web/scripts/verify-reader.mjs`. Fix commit: `46413a9`.

## Credential incident and production configuration

Pier reports that a read-only role password was exposed in a chat screenshot
and **rotated before being used in production**. No password, old/new credential,
connection string or screenshot is reproduced here. Rotation and console
configuration were not independently inspected in this offline review.
Only `DATABASE_URL_READONLY` is intended for the application runtime, with
Production scope and Sensitive classification. Owner/import credentials must
remain outside deployed runtime settings. Saved report reads make no model calls.

## Not yet verified

- Vercel build log and the exact deployment's build/source configuration.
- Full UI behavior in a signed-out/incognito browser.
- UI behavior on an actual phone.
- Deployment Protection setting in the console (required OFF for submission).
- Vercel and Neon billing consoles, free-plan status and current usage.
- Runtime environment-variable settings and absence of injected owner credentials
  by direct console inspection; only the variable name/scope policy is recorded.

The saved HTTP 200 responses do not independently prove those console settings,
signed-out UI accessibility, mobile behavior or billing status. The final
files-and-Git-history secrets scan, README completion, final grading refresh and
owner-reviewed videos remain final-submission work. Earlier step-1 build/browser
results are historical and were not rerun for this evidence review.
