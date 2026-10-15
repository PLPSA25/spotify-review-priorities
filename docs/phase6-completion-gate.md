# Production enrichment completion gate — October 15, 2026

Offline verification/export only. No new provider calls, failure-window resets,
state recovery, paid continuation, backup access, video inspection or upload.
The frozen label_config remains
`21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`.

## Interruption evidence and clip 3

The original after checkpoint was **not rewritten**. Its actual contents differ
from the approximate count recalled from the recording:

- `artifacts/scope-100k/checkpoint_after.json`: **22,227** sorted, unique IDs;
  SHA-256 `026e0cbdd1b07802a1df2ce9879295e060ced6d5a0602c51b040a3c38e9d2f8b`.
- `checkpoint_before.reconstructed.json`: **19,719** sorted, unique IDs;
  SHA-256 `39252683567643d0c967477f874739aa0a65bb98a0faee47752f3435c140fef3`.
- Same frozen hash; before strictly contained in after, after contained in completed.
- `resume-audit.json`: **pass**, `resume_enrich_ids_in_before: []`,
  **2,508** newly completed direct records with real paid resume-call evidence.
- The full supplied submission checker also reports **zero resume flags**.

Clip 3 needs only this secret-free command, from `C:\dev\Spotify`:

```powershell
.venv/Scripts/python.exe -m pipeline scope-proof
```

It reruns the audit against existing immutable files. It must show `status: pass`,
`before_count: 19719`, `after_count: 22227`, both subset booleans true,
`resume_enrich_ids_in_before: []`, `new_direct_paid_resume_count: 2508`.
It writes only the audit report, never a checkpoint or any provider call.

Disclosure: clip 1's pasted `scope-evidence beforeSet-Location C:\dev\Spotify`
was rejected by argparse; no before file was saved during that recording.
The separate, explicitly reconstructed before file uses the retained pause receipt
and pinned pre-run completed-state intersection with selected IDs. Its provenance
is preserved in `docs/100k-reconstruction-provenance.json`. The grading copy uses
the required canonical filename plus a provenance sidecar; it is not represented
as a contemporaneous recording artifact. Clip 2 wrote the actual after file, then
its audit failed on a database lock. Clip 3 completes the audit without replacing it.

## Final scope, failures and integrity

- Selected scope: **100,041 IDs / 77,913 texts** (100k prefix union golden IDs).
- Selected completed: **100,001 IDs / 77,874 texts**.
- Selected terminal: **40 IDs / 39 texts**, all
  `invalid_model_output_after_retry`. Of the newly admitted 75,874 texts,
  **75,836 completed / 38 terminal**; the other terminal text was retained from development.
- Saved new Jev scores: **75,871**, exactly matching succeeded production Jev IDs.
- Internal state includes imported development rows: **108,506 completed / 45 quarantined**.
  This is not the selected-scope count. The original 28,224 versus 19,719 pause
  difference was 8,505 imported completed IDs outside selected scope.
- SQLite state and ledger integrity: **ok**. Raw JSONL and SQLite contain the same
  **85,941** unique call events, byte-independent canonical event hashes identical,
  zero duplicate request IDs, differing events or missing events. See
  `100k-final-integrity.json` for full diagnostic counts and terminal IDs.

Terminal reasons below count selected IDs; parenthesized values are distinct texts:

- Extraction quote not an exact nonempty source substring: **18 (18)**.
- Fallback quote not an exact nonempty source substring: **13 (13)**.
- Jev choice differs from highest-probability option: **4 (3)**.
- Extraction refused/truncated batch: **2 (2)**.
- Fallback refused/truncated batch: **2 (2)**.
- Extraction missing/duplicate returned ID: **1 (1)**.

No terminal record was revived. These are invalid outputs after permitted repair,
not successful classifications or connection failures. Connection failures were
accounted pessimistically and retried under the approved policy.

Final resume segment wall time: **2,384.959 seconds**. This excludes earlier
scoring, pauses and recovery, so is not a whole-run throughput measurement.

Measured ledger invocation: **$4.834135303 / $7.28**, unused allowance
**$2.445864697**. Project: **$5.604212288 / $10**, headroom **$4.395787712**.
Zero leases, zero reserved funds, no cap latch. These include pessimistic accounting
for unknown-charge failures; they are not provider-dashboard reconciliation.

## Offline full-row propagation and interim grading export

`python -m pipeline.scope_export` streamed the unchanged full input and verified
its manifest SHA-256 before and after. The cache contains only completed selected
texts and their direct real-call origins. Unrelated imported development texts
were not used to expand coverage. All label fields and final flag reasons propagate;
each original row keeps its own ID/hash and each alias references a direct original.

- **660,622** output IDs; **13** empty-text quarantines.
- **237,722 / 660,609 nonempty rows completed = 35.9853%**.
- **159,848** valid direct cache reuses; **77,874** direct completed originals.
- **422,845** `not_classified_partial_run` nonempty rows.
- **42** terminal-failure rows after exact-text propagation.
- **422,900** total quarantined; **100% accounted**, no pending/missing/duplicate IDs.

The local `grading/` export is interim: business CSVs contain headers only and
run.json explicitly marks group/rank/claims/memo pending. JSONL payloads are ignored
by Git. `100k-interim-export-manifest.json` records sizes/hashes.

All three real course commands ran, without `--gold` or reading human golden labels:

```powershell
.venv/Scripts/python.exe data/check_submission.py profile --full data/spotify_reviews_18months.csv --out grading/ingestion.json
.venv/Scripts/python.exe data/check_submission.py reference --full data/spotify_reviews_18months.csv --analysis data/spotify_reviews_18months.csv --out local-reference.json
.venv/Scripts/python.exe data/check_submission.py check --reference local-reference.json --submission grading --out self-check.json
```

Actual result copied to `100k-interim-self-check.json`: **review_required**.
Every flag is explained here:

- `unfinished_classification: 1`: **422,887** nonempty rows lack completed labels
  (422,845 declared out of scope + 42 terminal). Expected deliberate scope limitation.
- `ungrouped_complaints: 1`: **70,239** completed complaint/cancellation IDs await membership.
- `missing_claims: 1`: numerical claims stage has not run.
- `missing_model_roles: 1`: current production-only log lacks **verify, group, memo**.
  Prior blinded verification exists separately: the v3 transfer log has **11 succeeded
  verify calls covering 500 unique IDs**. Its auditable import is proposed at the
  next gate; it is not silently relabeled as new production execution.
- `invalid_usage: 20`: **10** failed TypeSafe connection calls each lack **two**
  token fields. Values stay `null`, not invented zeroes. Each is pessimistically
  charged at its reserved bound. The contract (line 90) explicitly allows clearly
  unavailable usage with README disclosure and says the checker reports it.

No other flags. Quality is `not_supplied` because no human benchmark was passed
to this offline audit; prior golden accuracy reports remain separate. The checker
coverage-point candidate **0.6159** is not an assigned grade.

## Live-read repair

Status, snapshot and proof reads now use read-only connections with a 5,000 ms busy
timeout and at most four attempts for SQLITE_BUSY/SQLITE_LOCKED, backoffs
0.25/0.5/1 seconds (roughly 21.75 seconds maximum per contended execute).
Other errors are not retried. Writes/checkpoints and model calls are never replayed.
Permanent locks still surface for diagnosis rather than spinning forever.
Tests cover real lock release, exhausted contention, unrelated errors, read-only
enforcement and snapshot publication after contention, alongside existing resume tests.

## Submission size proposal — not applied

Complete inventory: `submission-large-files.json` lists every working file above
**50,000,000 bytes**, its size and tracked status. **None is tracked**.
Current grading files exceeding this threshold are calls **488,704,196 bytes** and
records **196,196,656 bytes**. The original runtime call log is **487,875,908 bytes**.
Other large files are ignored SQLite stores/recovery snapshot, local reference,
raw source, runtime enriched JSONL and the two ignored recordings.

Contract line 53 permits `.jsonl.gz` and a downloadable ZIP/release asset.
Checker lines 153–173 read gzip when the plain counterpart is absent; both present
produce `ambiguous_file`. Call requirements at contract lines 84–90/checker
lines 332–368: unique nonempty request_id, valid role/model/outcome, original unique
review_ids (enrich 1–50), matching enrichment hash, initial/resume phase and integer
nonnegative input/output usage. Required unknown usage stays unavailable/disclosed.
Request/response payloads are not required by the grading adapter, but remain in
the full raw audit log. We propose **no field removal at all**:

1. Gzip the complete current grading calls and records, retain every JSON key/value.
2. Keep raw originals unchanged locally outside the distributed grading directory;
   publish only the gzip counterparts, never both forms under grading.
3. Ship the complete grading folder as a downloadable release/ZIP asset with hashes;
   commit only small code/docs/manifests/links. No files over 50 MB in Git.
4. Rerun the supplied checker on the distributed folder and compare coverage,
   call/token totals and flags with the uncompressed result. Byte decompression
   hashes must match. Compression must not conceal unavailable usage or scope limits.

Measured by compressing to a discarded stream (no .gz files created), gzip level 6
would produce **27,368,226 bytes** for grading calls and **53,350,340 bytes** for
records. Thus even compressed records should be an external asset under the owner's
50 MB repository limit. The full log need not be stripped to fit GitHub's 100 MB limit.
Compression is checker-supported, but cannot make the deliberate scope/unknown-usage
flags disappear; claiming a completely flag-free checker result would be false.

## Next gate

See `phase7-proposal.md`. Stop here; no group/memo calls or business aggregates ran.

Validation at this gate: **173 pytest tests passed**; `ruff check pipeline tests`
passed. All tests forbid network connections. Local commit excludes recordings,
secrets, raw CSV, PDFs, backups and every file above 50,000,000 bytes.
