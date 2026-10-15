# Offline recovery complete — owner starts the paid continuation

Owner approved the offline recovery and will run the continuation personally. No
paid calls were made by this recovery. The original ledger invocation and $7.28
total cap are unchanged; **$3.575524047 remains**. Never start a new invocation to
obtain a new allowance. Frozen hash and 20% routing selection are unchanged.

## What was applied offline

- SQLite and ledger backups plus byte-preserved original receipts are in
  `artifacts/scope-100k/recovery/`. The original failed `stop-receipt.json` and
  original segment receipts remain unchanged. The failed invocation is additionally
  archived in a separate SQLite artifact.
- Approved stage-history repartition: original mixed 3/27 finalization history
  preserved. Its three duplicate-attribution Jev failures stay in classification
  history/call logs; classification and connection windows are unchanged. The
  finishing window began with its 24 true successful finalizations; replay added
  133 successes, leaving last 100 finishing outcomes successful. No real failure
  was erased or retry allowance reset. No cap latch existed or was cleared.
- **133 stored valid outputs** were finalized with their existing succeeded paid
  call provenance. Raw `calls.jsonl` bytes, call count, reservation rows and charges
  did not change. Exports now reflect the recovered labels. All 75,871 Jev scores
  remain stored. All three terminal texts (four IDs) remain terminal.
- Current scoped counts: **19,876 completed / 80,160 pending / 5 quarantined**.
  New distinct work: **157 completed / 75,714 pending / 3 quarantined**. Internal
  completed count 28,381 includes 8,505 imported completed IDs outside scope.
- Status is honestly **recovery_ready**, not a fabricated stopped_user state.
  The ordinary resume path remains blocked for this status. A sealed recovery
  authorization binds the owner-run entry point to the local commit, recovered
  state SHA, original invocation ID, rates/controls and unchanged ledger.

## Reconstructed before evidence

The owner's clip-1 account: a paste produced
`scope-evidence beforeSet-Location C:\dev\Spotify`; argparse rejected it, so no
before file was created. The clip shows a drained initial voluntary pause, 19,719
scoped completed IDs, 5,570 saved new Jev scores, safe_to_resume true and invocation
`7180188e-0938-4d2f-8e2b-6bf412cf77ca`. The saved initial segment receipt corroborates
the pause state. The assistant has not inspected the recording.

The separately named **`artifacts/scope-100k/checkpoint_before.reconstructed.json`**
was created after the halt by intersecting pinned selected IDs with completed exact
texts in the unchanged pre-run base, using the original pause receipt to establish
that no new final completions existed then. Count **19,719**. SHA-256:

`39252683567643d0c967477f874739aa0a65bb98a0faee47752f3435c140fef3`

The separate `.reconstructed.provenance.json` records creation time, paste error,
method and base/selection/pause hashes; a copy is in
`docs/100k-reconstruction-provenance.json`. **Do not describe this as saved during
the recording or rename it to imply that.** README includes the disclosure.

An after-recovery snapshot was saved separately as
`checkpoint_after.offline-recovery.json`. It contains **19,876** selected IDs.
The local audit passes **before ⊂ after ⊆ completed**, zero before IDs touched by
production resume calls, and **157 new direct paid resume originals**. The recovery
made no calls; their payment/provenance comes from the already completed eight
extraction calls in the failed resume segment.

The actual resume section of `data/check_submission.py:314–370` was executed offline
with these snapshots and the declared grading call view: imported history mapped
to initial with original phase/run identity retained, incompatible historical
enrichment hashes omitted from the grading view only. Raw history is unchanged.
Result: **resume rules pass; zero resume flags**. Ten unknown-charge calls have
twenty unavailable token-usage fields flagged separately. This is not a full
submission audit or certification that the reconstructed file existed on video.
Reports are in `artifacts/scope-100k/recovery/`.

## Terminal A — owner starts continuation

Recheck provider funds if needed. Do not run the original start command or mint
another original authorization. From PowerShell:

```powershell
Set-Location C:\dev\Spotify
.venv/Scripts/python.exe -m pipeline scope-continue --recovery artifacts/scope-100k/recovery/continuation.json --confirm-spend
```

This is the paid command. It uses eight workers, the same invocation ID and total
$7.28 ledger cap, preserving the already-spent $3.704475953. Additional spend cannot
be admitted above the remaining $3.575524047. Expected finishing spend is about
$1.165205, not a completion guarantee. It skips saved Jev scores, recovered outputs,
completed/cache IDs and terminal items. Three quote-invalid extraction items get
only their already-permitted repair. No new fallback selection is drawn.

The receipt is single-use against this recovered state fingerprint. A cap, monitor,
connection/auth/integrity failure or another voluntary pause requires a reviewed
next step; do not reauthorize, clear latches/windows, change run ID or manually
change status. An exception prints only its type, never raw provider payloads.

## Terminal B — monitor and save after evidence

```powershell
Set-Location C:\dev\Spotify
.venv/Scripts/python.exe -m pipeline scope-status --watch
```

This is read-only and displays safe counters, phase, invocation, leases and budget.
Before starting it shows `recovery_ready` and `safe_to_continue_recovery: true`;
ordinary `safe_to_resume` is false by design. Once running, phase is resume. Press
Ctrl+C **only in Terminal B** to stop the monitor, never in the paid Terminal A.

After additional continuation progress (for example, scoped completed at least
**20,076**, 200 beyond the recovered baseline), stop the monitor and run:

```powershell
.venv/Scripts/python.exe -m pipeline scope-evidence after
```

It automatically verifies and uses the separately reconstructed before file.
It creates immutable `checkpoint_after.json`, not the earlier separate
offline-recovery snapshot. It must show:

- before_count **19,719** and after_count greater than 19,719;
- proof status **pass**;
- before_strict_subset_after and after_subset_completed **true**;
- resume_enrich_ids_in_before **[]**;
- new_direct_paid_resume_count **greater than zero**.

The reconstructed provenance is not rewritten. Do not rerun `scope-evidence before`
or overwrite either snapshot. If after already exists, use the repeatable proof
command instead. At final completion, rerun the proof against full call history:

```powershell
.venv/Scripts/python.exe -m pipeline scope-proof
```

If halted, run only `scope-status`, preserve artifacts and report status/counts/cap.
No automatic recovery or additional paid stage is authorized. Do not display .env,
raw calls or provider payloads on video. The local MP4 remains ignored and uncommitted.
