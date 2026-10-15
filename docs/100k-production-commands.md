# Prepared 100k run — PowerShell operator guide

Prepared offline, no model calls. **Do not execute paid commands until the owner says yes to the $7.28 shared invocation cap.** The 20% fallback fraction and frozen prompt are approved; the invocation itself awaits approval. Do not rerun preparation or edit the execution plan after authorization. The source/store is already prepared locally.

## Required evidence, exact wording

`data/GRADING_CONTRACT.md:16`:
> Demonstrate interruption after saved progress, then resume with additional completed records and no new enrichment calls for already completed IDs under the same configuration.

`data/GRADING_CONTRACT.md:17`:
> Supply a short recording and the two checkpoint snapshots. The instructor may ask for a small fresh-input demonstration after submission.

The contract explicitly requests a **short recording plus both snapshots**, not snapshots alone. It does not specify format or duration or use the word “video”; a short screen recording is the appropriate evidence of the CLI demonstration. `CHATGPT_PROMPT.md:97` additionally requires a “recorded interruption and resume.” Contract lines 64–65 require `checkpoint_before.json` and `checkpoint_after.json`; project prompt lines 61–64 specify strict subset growth, exclusion of before IDs from resume enrich calls, and actual new paid resume work. No video artifact exists yet.

## Final offline preflight

- Frozen hash: `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`, unchanged after applying fallback 0.20.
- Scope: 100,041 IDs (fixed 100k permutation prefix plus forced golden IDs); 77,913 distinct texts = 2,038 reusable completed + one retained terminal + 75,874 new.
- Selected IDs already completed by exact-text cache: **19,719**. Pending: **80,321**. One retained terminal ID. Internal imported development rows outside scope remain provenance only.
- Eight workers, frozen routing tranche and 15,174 maximum fallback text slots (limited by eligibility); select confidence → margin → exact-text hash before dispatch. The quota never resets on resume.
- Base remaining estimate **$4.852176 / 1.89 hours**, not a measured completion guarantee. TypeSafe ~$3.705730, Luna ~$1.146446. No prompt-cache savings assumed.
- Proposed shared invocation cap **$7.28**, rounded up from 1.5× base. One ledger run ID across start/resume, not two caps. Project $0.770076985 spent, $0 reserved; maximum after this invocation **$8.050076985 / $10**, leaving $1.949923015 for separately approved later work.
- Owner-reported TypeSafe **$10.41**; OpenAI prepaid **$9.82**, October spend $0.18 against $20 org limit. OpenAI effective ceiling is prepaid credit, before delayed usage. **Owner rechecks both balances and concurrent/unposted usage immediately before authorizing.** No dashboards were accessed or old unknown outcomes reconciled.
- Production state SQLite integrity `ok`; no leases; no paid production calls. Original CSV SHA verified against the course manifest. Exact-source selected CSV and initial prepared state have pinned SHA-256 in `docs/100k-production-plan.json`. At least 10 GiB free required; free disk is about 282 GiB, rechecked by authorization and start. Keys remain local and are never displayed.
- All code/docs/evidence must be committed locally before authorization; authorization refuses dirty or changed code/plan. No push. Raw full CSV, production selected CSV, SQLite, credentials, PDFs and backups are excluded. The authorization receipt is local/ignored.

## 1. Start — Terminal A, only after yes and live balance recheck

Set location. Show the commit and offline prepared counters while recording; do not display `.env`, billing pages, raw logs or provider payloads.

```powershell
Set-Location C:\dev\Spotify
git rev-parse --short HEAD
.venv/Scripts/python.exe -m pipeline scope-status
.venv/Scripts/python.exe -m pipeline scope-authorize --plan docs/100k-production-plan.json --acknowledge-spend
.venv/Scripts/python.exe -m pipeline scope-run --plan docs/100k-production-plan.json --confirm-spend
```

`scope-authorize` is offline: it pins this plan and local commit and records your explicit acknowledgment after the balance recheck. The final line is the **first paid command**. It uses eight workers without relying on the default max_workers in config. Start and resume use the same approved $7.28 invocation, cap and fraction. Authorize once; do not mint another receipt to bypass a halt. The runner's final stdout is allow-listed counters; unexpected exception messages/payloads are not printed. If a guard refuses the command, stop and ask for diagnosis rather than editing its guard fields.

## 2. Monitor and interrupt at approximately five minutes — Terminal B

In another PowerShell terminal:

```powershell
Set-Location C:\dev\Spotify
.venv/Scripts/python.exe -m pipeline scope-status --watch
```

This read-only command prints every five seconds: invocation ID, phase, elapsed segment seconds, scoped counts, new distinct work, saved Jev scores, leases, project/invocation spend and remaining cap. It never shows text, payloads, keys or raw errors. Press **Ctrl+C in Terminal B only** to stop the monitor, not the runner in Terminal A.

When `elapsed_segment_seconds` is about **300**, with saved new Jev scores >0 and new work still pending, request the graceful interruption in Terminal B:

```powershell
New-Item -ItemType File -Path artifacts/scope-100k/stop.request -ErrorAction Stop
```

Do not use Ctrl+C in Terminal A, Task Manager or terminate its shell. The watcher stops new claims, lets admitted requests and permitted repairs finish, and saves validated work. Wait for Terminal A to return with `status: stopped_user`, `drained: True`, zero leases and zero reservations. Then check:

```powershell
.venv/Scripts/python.exe -m pipeline scope-status
```

Require `safe_to_resume: true`, `cap_latched: false`, zero `leases` and `reserved_usd`. The request is acknowledged only after the durable drained receipt; do not delete stop or ledger files manually.

**At five minutes the run is expected to be in the Jev-scoring pass.** Progress is saved scores, not yet new final labels. This is legitimate saved progress and prevents re-paying those scores on resume. The before snapshot will likely contain the 19,719 reusable completed IDs. Do not pretend final-label progress occurred before it did. If no new score has been saved by five minutes, investigate instead of fabricating progress. The run scores the entire new tranche before routing Luna; final completed-row growth after resume may take roughly an hour or more. The 1.89-hour total projection is uncertain and excludes time spent manually paused.

## 3. Show the immutable before checkpoint — Terminal B, after drained exit

```powershell
.venv/Scripts/python.exe -m pipeline scope-evidence before
```

Shows path, completed-ID count, SHA-256 and no private review text. The saved file is `artifacts/scope-100k/checkpoint_before.json`. It contains selected-scope IDs only, not unrelated imported development IDs. It refuses overwrite. Show the filename/count/hash on the recording.

## 4. Resume — Terminal A

```powershell
.venv/Scripts/python.exe -m pipeline scope-run --plan docs/100k-production-plan.json --confirm-spend --resume
```

No new authorization or budget. Same invocation ID, hash, original routing selection/fraction, retry logs and failure windows. Saved Jev scores and completed/cache records are reused. Resume processes pending stages only. In Terminal B restart the monitor:

```powershell
.venv/Scripts/python.exe -m pipeline scope-status --watch
```

For a **short recording**, pause capture or visibly skip the long scoring wait; disclose the time gap. Record actual start/stop/saved progress, actual resume and the later checkpoint proof. Do not claim a continuous five-minute full run or edit logs/timing. The pipeline continues while the monitor runs.

## 5. Show after and prove resume — Terminal B

Once `scope_counts.completed` exceeds the before count by at least about **200**, stop only the monitor with Ctrl+C and run:

```powershell
.venv/Scripts/python.exe -m pipeline scope-evidence after
```

This writes immutable `checkpoint_after.json`, validates it against the current state and real calls, and writes `resume-audit.json`. Require:

- `status: pass`;
- `before_count < after_count`;
- `before_strict_subset_after: true` and `after_subset_completed: true`;
- `resume_enrich_ids_in_before: []`;
- `new_direct_paid_resume_count > 0` (completed direct originals with succeeded, nonsimulated, paid resume calls).

If it says **not ready**, no snapshot was written: wait for new finalized labels and real paid resume evidence, then try again. A failed proof after writing is an integrity gate: preserve everything and stop for diagnosis, never overwrite the snapshots. The after snapshot may be saved while work continues; completed sets grow monotonically. After should not be confused with every eventual completion.

Leave the run going. After Terminal A exits at completion, rerun the proof against the same immutable snapshots and the full call history:

```powershell
.venv/Scripts/python.exe -m pipeline scope-status
.venv/Scripts/python.exe -m pipeline scope-proof
```

The proof is `checkpoint_before ⊂ checkpoint_after ⊆ completed`, zero resume-phase before IDs, plus new direct paid resume work. Checkpoint JSONs, SHA-256s, `resume-audit.json`, segment receipts, SQLite, raw calls and the short recording are retained locally. Do not expose full raw calls on video. Historical imported development call phases are not this production invocation; the final grading adapter must retain source phase and map imported phases relative to this recorded run as documented in the run plan.

## 6. If the runner halts

Run only the offline status command:

```powershell
.venv/Scripts/python.exe -m pipeline scope-status
```

- **Voluntary pause:** resume only after `stopped_user`, drained/zero reservations and leases, `safe_to_resume: true`, and the before checkpoint is saved.
- **Invocation or project cap:** `cap_latched: true` or `stopped_cap`. **Stop and report the status, remaining cap and counts.** Do not raise the cap, authorize again, change run ID, delete the ledger/stop latch or resume. New approval is required even if later settlement frees headroom.
- **Terminal-failure or connection threshold:** separate >5% in a rolling 100, minimum 20 observations, stops admission. Unknown charges are pessimistically accounted with bounded retries. **Stop and report.** No reset of windows or automatic resume; diagnosis and a new recovery decision are required.
- **Integrity/auth/model error, outstanding lease/reservation or failed proof:** preserve files; stop and ask for recovery. A killed process is not a clean user interruption. Never print `.env` or raw exception/payload logs on camera.

Do not run additional verifier/group/memo calls. At completion stop at the enrichment gate; cache propagation and out-of-scope `not_classified_partial_run` export are offline next steps under the documented scope policy, with no new model calls.
