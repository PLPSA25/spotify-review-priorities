# Spotify Insight Pipeline

Phases 1–6 are complete through the approved partial production enrichment and
offline propagation gate. Group/rank/claims/memo await approval. Current measured
results: [Phase 6 gate](docs/phase6-completion-gate.md). Earlier dated gate notes
below preserve history and are superseded by that completion report.
Python 3.11+; developed on Windows with Python 3.12.

## Approved scope

Ingest all 660,622 source rows. Classify the first 100,000 nonempty IDs of a saved,
seeded permutation, union the golden 50, and propagate validated labels by exact text.
Keep every original ID. Export all other nonempty rows as quarantined with
`not_classified_partial_run`; empty texts use `empty_review_text`.

This deliberately conflicts with the course contract's full-classification requirement.
The owner approved this partial scope. The final checker will report
`unfinished_classification`; benchmark omissions count as incorrect. Coverage credit is
reduced. Actual offline propagation completed **237,722 / 660,609 nonempty rows
(35.9853%)**, with 159,848 valid direct cache reuses. The checker coverage-point
candidate is **0.6159**, not an assigned grade. A random-sample-only secondary ranking
will accompany the baseline to expose repeated-text selection bias.

## Windows setup and offline run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pipeline prepare --input data/spotify_reviews_18months.csv
python -m pytest
python -m ruff check pipeline tests
```

Activation is optional: use `.\.venv\Scripts\python.exe` directly if PowerShell policy
blocks activation. No credentials are needed for preparation or tests. Paid commands
are not implemented in Phase 1. Never paste credentials into chat. Maintain `.env`
yourself; only blank `.env.example` belongs in Git.

Outputs in `artifacts/ingestion/`: `data_manifest.json`, `ingestion_report.json`, exact
course-helper `ingestion.json`, and local `state.sqlite3`. The database retains original
field strings, helper row hashes, pending/quarantined statuses, attempts and reasons.
Preparation validates course checksums before ingestion and confirms them afterwards.
The command builds a fresh ingestion store; it is not the eventual enrichment/resume
command. Do not run preparation over a future active enrichment store.

## Source and preserved course files

The eleven course files are unchanged in `data/`; the assignment PDF remains in root.
See `data/README.md`, `data/GRADING_CONTRACT.md`, `data/COST_CALCULATOR.md` and
`data/manifest.json`. Do not edit or regenerate supplied CSVs.

Source: [BwandoWando Spotify reviews, version 2](https://www.kaggle.com/datasets/bwandowando/3-4-million-spotify-google-store-reviews).
Full CSV SHA-256: `1fc85de68a304dd8978b537cfa58793d5f41cbaf417fa32cb53899f83a2fcef6`.
The raw CSV and local database are excluded from Git.

## Next phases and gates

Prepare → Classify → Verify → Group → Rank → Recommend. Python controls accounting,
validation, caching, SQLite work state, budgets and deterministic arithmetic. Jev makes
fixed label judgments; Luna performs bounded extraction/fallback, blinded verification,
group naming and grounded writing. No business findings exist yet.

See `docs/approved-plan.md` and `config.toml` for accepted controls and unresolved items.
Phase 4 begins only after Phase 3 approval. The final README will add actual evaluation,
cost and resume evidence, rubric links, a traced review, memo and live dashboard URL.

## Golden labels (final human evaluation set)

Four golden labels were revised after an AI-assisted check against the contract rules; final labels are my decisions.

The owner completed and froze all 50 human labels. Offline validation on October 14,
2026 passed 50/50 records. Do not edit the original CSVs or use Excel. Validate offline:

```powershell
python -m pipeline validate-golden
```

The report identifies IDs and field errors, without proposing answers. A successful
schema check does not establish semantic accuracy. Golden answers are evaluation-only
and never model inputs. `golden-template` can create a new copy at an explicitly chosen
output path and refuses to overwrite existing human work.

Entities were not hand-labeled: empty arrays are intentional and entities must be
excluded from golden evaluation. Golden labels are never threshold/routing calibration
data. Final-hash golden evaluation is complete; see `docs/golden-final-evaluation-gate.md`.

The final-hash human-accuracy gate completed all 50 predictions: six golden IDs
reused exact-text results and 44 new texts were classified. Actual cost $0.002603841.
See `evals/golden-final-evaluation/report.html` for overall/fallback splits and all
confusion tables, and `docs/golden-final-evaluation-gate.md` for measured evidence. Golden metrics
and confusion CSVs are produced only by the offline `evaluate-golden` command
after predictions are frozen; golden results never tune prompts, thresholds or routing.

Use `python -m pipeline review-disagreements` for the offline human adjudication
of up to 20 blinded-verifier disagreements. It shows one review and both labels,
accepts Jev right / verifier right / both wrong / unclear for the displayed field,
and saves atomically to `evals/verifier-human-review.json` with a summary sibling.
`q` stops safely; rerun to resume. Golden IDs/texts and terminal rows are excluded.
The 100k execution/recording plan is draft-only in `docs/100k-run-plan-draft.md`.

The owner completed all 20 development disagreement verdicts: Jev right 5,
verifier right 12, both wrong 3, unclear 0. The field breakdown and limitations
are in `docs/human-verifier-review-gate.md`. This selected disagreement sample
does not estimate corpus accuracy and did not change the frozen configuration.

Tests use per-test workspace temporary directories and remove them automatically,
including after failures. PDFs are ignored. Jev's configured request limit is 60/s;
the account's published 80/s limit is recorded separately in the approved plan.

## Enrichment and resume

See `docs/enrichment.md` for explicit mock/live commands, controls, cache provenance,
interruption/resume and charge reconciliation. Providers use standard-library HTTP
with no hidden retries. Provider preflight and the 100-review pilot are complete.
The Class 7 date is unknown. The two-worker enricher completed all 500 checkpoint
reviews; verifier recovery completed all 500 valid predictions. See
`docs/checkpoint-500-recovery-gate.md` for measured cost/time, terminal-failure policy,
full-field calibration and the smaller scaling proposal. The initial quota/failure
audit remains in `docs/checkpoint-500-gate.md`. Three approved disjoint 1,000-row
analysis_10000 slices have now completed; no golden agreement evaluation has run.

## Frozen calibration and next paid gate

Approved confidence 0.60, margin 0; explicit language/context judgments and deterministic
fallback allocation are frozen in `docs/frozen-label-config.json`. See
`docs/frozen-calibration.md` and its 35-pair/field CSVs for verifier comparisons (not
human accuracy), sentiment near-zero diagnostic and selection/resume tests. Old pilot
and checkpoint caches retain their historical hash and are not mixed into new outputs.
`docs/frozen-scaling-proposal.md` records the approved three-slice bounds.
`docs/scaling-gate.md` reports measured 1/2/8-worker results, v2/v3 flag drift and
updated costs. Stopped at the scaling gate before remaining 10k work. A proposed
500-row blinded v3 transfer verifier has now completed with 500 valid predictions.
See `docs/v3-verifier-gate.md` for auxiliary reasons, language confirmation, the
35-pair core grid and a proposed final flag rule. The proposal is not applied;
the frozen hash remains unchanged and remaining analysis_10000 is paused at the gate.
`docs/checkpoint-500-v3-ab-proposal.md` records the earlier contract/provisional
flags, proposes a same-row v2/v3 comparison and describes the offline flag-reason
export. Final fallback reasons include an unattributed category; initial signals
are not presented as known final causes. No A/B paid run has been approved yet.
The user subsequently approved explicit reasons and persistent missing-context
signals from either model. `docs/final-config-gate.md` and
`docs/frozen-label-config.json` are the current final policy/hash; historical
snapshots and paid outputs retain their old hashes. The revised A/B proposal is
$0.430210238 worst case was approved and the A/B has completed. V3 passed the
predeclared core topic/intent criterion on all 500 rows; final enrichment has
499 completed and one terminal quote failure. See `docs/checkpoint-v3-ab-gate.md`
for field comparisons and the proposed 8-worker analysis_10000 gate: $7.441328042
worst case was superseded by the user's $1.50 invocation approval. The analysis
attempt stopped on seven unknown-charge connection outcomes before that cap,
with 79 valid new Jev results saved and no new finalized records. See
`docs/analysis-10000-stopped-gate.md` for measured accounting, provisional 100k
estimates and the reconciliation gate. No automatic retry/resume occurred.

The subsequent user-approved eight-worker keep-alive resume has reached its gate:
9,994 analysis rows completed, six terminal failures total (five new), and no
pending work. See `docs/analysis-10000-resume-gate.md` for measured timing,
connect/send/post-send failure counts, retry breakdown, actual usage cost and the
estimated 100k time/cost. The label hash is unchanged. The seven original unknown
charges were pessimistically accounted without provider-dashboard reconciliation.
No golden evaluation, 100k run or downstream paid stage was dispatched.

The owner approved 20% fallback and accepted the frozen prompt; the cap is applied.
The offline recommendation is to retain the frozen prompt. At eight workers: estimated
$4.85 / 1.89h, with a $7.28 total invocation cap across interruption/resume. It was
frozen from development verifier data and human verdicts before golden evaluation.
It is now applied to controls at 20%, with the frozen prompt and hash unchanged. See
`docs/100k-run-plan-draft.md` and `docs/100k-run-proposal-draft.json`. No 100k run
or pre-run commit has occurred. OpenAI organization headroom still requires a live
preflight check; project spend alone is not an org balance.


### Offline pre-production clarification

#### Terminal near-tie validation failures in the 100k scoring pass

Three distinct exact texts remain terminal after two rejected Jev attempts each
(six failed attempts; four source IDs including one exact-text alias). All carry
`invalid_model_output_after_retry`; they are retained, excluded from calibration,
and not retried or reclassified during recovery:

- `3bbab369-2722-48ea-8ab2-0739a9b3d5f7`: topic choice billing 0.42 versus
  highest-probability usability 0.43, twice.
- `6ee89fe5-6900-43ce-9c54-43078ac506e1`: billing 0.46 versus usability
  0.47000000000000003, twice.
- `014df5d4-c2dc-4e7c-9a18-d874bd80fef5`: language choice nonenglish_understood
  0.45999999999999996 versus english 0.46, twice. This was a machine-precision
  false rejection; alias `ad5f72c8-46a5-4d6c-8dea-2469ee0b2ed0` shares the terminal
  result. The numerical validator is fixed for future work, but this frozen run's
  existing terminal status is deliberately retained. This is not a semantic label
  disagreement or a new golden error.

#### Clip-1 checkpoint disclosure

Clip-1 shows the interruption and resume, but the before-checkpoint command did
not succeed: a paste produced `scope-evidence beforeSet-Location C:\dev\Spotify`,
which argparse rejected. **No before checkpoint file was saved during that clip.**
The owner reports that the clip shows `stopped_user`, `drained: True`, scoped
completed 19,719, saved new Jev scores 5,570 and invocation `7180188e-…`; the saved
initial pause receipt corroborates the state. The video has not been independently
inspected by the assistant and remains local/ignored pending publication choice.

After the later halt, `checkpoint_before.reconstructed.json` was reconstructed
offline by intersecting the pinned selected IDs with completed exact texts in the
preserved pre-run base. It contains **19,719 IDs**, SHA-256
`39252683567643d0c967477f874739aa0a65bb98a0faee47752f3435c140fef3`.
The separate provenance note records the paste error, reconstruction timestamp,
base/selection/pause-receipt hashes and method. **This is post-hoc evidence, not a
claim that the file existed during the recording.**

The offline-recovery after snapshot is separately named
`checkpoint_after.offline-recovery.json`; it includes only validated existing paid
responses. `scope-evidence after` will create the later continuation snapshot and
automatically use the reconstructed before file. Resume audits check strict set
growth, inclusion in completed records, zero before IDs in production resume calls,
and new paid non-cache originals. The supplied checker's resume section is tested
using the declared grading view: historical imported calls retain source phase/run
identity and are mapped to initial relative to this recording; incompatible old
enrichment configurations remain raw provenance. Raw call logs are unchanged.
Passing those consistency rules does not attest when a file was created, certify
the recording, or constitute a full grading-submission pass.
The checker separately reports 20 unavailable token-usage fields on ten
pessimistically accounted calls. These are not resume-rule failures; no token usage
is fabricated and no provider reconciliation is performed.

#### Semantic rule-violation audit counts

The semantic audit counts confirmed pipeline rule violations separately from model
disagreement. These are reviewed subsets, **not corpus accuracy estimates**:

- **Golden, 50 records:** one clear severity violation: a pure feature request received
  severity 3 (`b58dd6f0`), whereas the contract specifies severity 1 (line 43).
  There are **zero confirmed topic/intent rule violations among the 21 field errors**
  (13 topic + 8 intent): **0/21 = 0% confirmed**, **20/21 = 95.2% interpretation/judgment
  disagreements**, and **1/21 = 4.8% conditional, translation-dependent intent violation**
  (`ac6cd66d`). Do not count that conditional case as confirmed, or silently combine
  it with judgment calls. Some interpretation disagreements favor the pipeline under
  the literal contract; disagreement with golden alone is not a pipeline violation.
- **Development, 975 unique verified texts screened:** manual review confirmed 13 core-Jev
  cases of generic criticism assigned severity 1 instead of 2 (contract lines 39/44).
  **12 remain violations in final records; fallback corrected one.** Human verdict 3
  independently confirms one of these cases; it is not an additional count.
- **Development Premium mention versus actual defect:** one independently human-confirmed
  topic violation (`a7b7539a`, review 6): billing rather than playback for music that would
  not play. The error remains in both core and final output (contract line 36).
  Zero confirmed golden cases of this same specific error; golden billing disagreements
  are interpretation disputes. No additional “confirmed” counts are inferred from the
  broad lexical screens for ads, catalog/lyrics, mixed issues or non-English text.

See [the full golden audit](docs/golden-error-analysis.md),
[counted limitations](docs/confirmed-rule-limitations.json), and
[development evidence](docs/development-pattern-evidence.json). Golden labels were not
revised, and these findings did not tune prompts, thresholds or routing. The owner
accepted the frozen prompt and hash. A hypothetical prompt improvement remains untested.

Caching means the pipeline's exact-text **result cache** under an unchanged label_config, not provider prompt caching. OpenAI reports 0% prompt-cache hits; no prompt-cache savings are claimed or implemented. Saved Jev stages are reused on resume.

Fallback and verifier both use Luna: blinded verification hides Jev output but remains correlated with fallback. Verifier-agreement gains partly reflect self-agreement; the 20 owner verdicts are independent human evidence, not a random accuracy estimate. The owner approved a 20% fallback cap for 100k pending the prompt decision; the offline recommendation keeps the frozen prompt. Current fallback control is 20%; the paid production invocation still awaits yes. No paid start is authorized.

Updated user-reported preflight: OpenAI October spend $0.18 / $20 org limit; prepaid balance $9.82 is the real ceiling before unposted charges. TypeSafe $10.41. Recheck remaining credits/limits before dispatch. See docs/offline-preproduction-gate.md and docs/100k-run-plan-draft.md.


Production setup is prepared offline. Use [the exact PowerShell operator guide](docs/100k-production-commands.md) and [the pinned plan](docs/100k-production-plan.json). The contract explicitly requires a short recording and both checkpoints (data/GRADING_CONTRACT.md:16–17). A graceful stop at about five minutes preserves Jev scores; final completed growth may occur much later after resume. Nothing paid starts before the owner approves the $7.28 shared invocation cap.


## Production completion, evidence and submission limitations

The selected scope ended at **100,001 completed / 40 terminal IDs** (100,041 total).
After exact-text propagation the full export accounts for every original ID:
237,722 completed, 422,845 nonempty rows quarantined as `not_classified_partial_run`,
42 terminal-failure rows, and 13 `empty_review_text` rows. Terminal selected IDs
break down as 31 invalid exact quotes, four refused/truncated batches, one
missing/duplicate returned ID, and four Jev near-tie probability/choice mismatches
(three distinct texts). Permitted repairs were exhausted; these remain failures.

Ten failed TypeSafe connection calls have **unavailable input and output token
usage** (null fields), producing 20 `invalid_usage` flags. They were pessimistically
charged at their reserved worst case; we did not invent zero usage or reconcile
provider dashboards. Contract line 90 explicitly permits disclosure of unavailable
usage and says the checker reports it. Project spend is **$5.604212288 / $10**;
production invocation spend **$4.834135303 / $7.28**, including pessimistic failures.

The full supplied checker ran and returns `review_required`. Besides unavailable
usage and partial scope, this interim export flags pending grouping for 70,239
complaint/cancellation IDs, missing claims, and missing verify/group/memo calls in
the current production export. Prior blinded verifier evidence remains separate. The owner requested a fresh
500-record production verifier proposal instead; no development verifier evidence
will be imported to satisfy the production role. Business CSVs currently contain
headers only and run.json declares them pending. This is not a final submission.
No duplicate, missing, invalid record, cache-origin or resume-proof errors were found.

**Recording disclosure:** clip 1's malformed pasted command did not save a before
checkpoint. `checkpoint_before.reconstructed.json` was reconstructed later from the
retained pause receipt and pinned base-state intersection (19,719 IDs); it is not a
file saved during the video. Its separately preserved provenance accompanies the
canonical grading copy. Clip 2 saved the immutable after checkpoint (22,227 IDs),
then hit a database lock during audit. Offline `scope-proof` now passes against
those unchanged snapshots: before strictly contained in after, after contained in
completed, no before IDs in resume enrichment calls, 2,508 new direct paid resume
records. A short clip 3 can rerun that proof. Recordings remain ignored/local;
no video is committed or uploaded.

See [full completion and checker explanations](docs/phase6-completion-gate.md),
[large-file inventory and unapplied gzip measurements](docs/submission-large-files.json),
and [the next paid gate proposal](docs/phase7-proposal.md). The two full grading JSONLs are now gzip level 9 and committed directly below
100 MB each; raw originals remain local and ignored. No release asset is needed.


## Current grading package and exact grader command

`grading/calls.jsonl.gz` (**26,686,127 bytes**) and `grading/records.jsonl.gz`
(**52,450,579 bytes**) are complete, maximum gzip level 9 exports, committed directly.
No JSON fields were removed. Decompressed SHA-256 values match the raw originals;
see [the gzip manifest](docs/submission-gzip-manifest.json). The explicit owner
instruction permits the records gzip above the earlier 50 MB commit limit.
Raw originals remain local/untracked under `artifacts/scope-100k/submission-raw/`.

The supplied `data/check_submission.py:152–158` reads these `.gz` files from
`grading/` **as-is**, with no manual extraction. Do not put a plain counterpart in
that folder: providing both causes `ambiguous_file`. From `C:\dev\Spotify`, with
the unchanged full course CSV available, create the local reference if necessary:

```powershell
.venv\Scripts\python.exe data\check_submission.py reference --full data\spotify_reviews_18months.csv --analysis data\spotify_reviews_18months.csv --out local-reference.json
```

Exact grader command:

```powershell
.venv\Scripts\python.exe data\check_submission.py check --reference local-reference.json --submission grading --out self-check.json
```

This check ran against the gzip files. All coverage, call/token totals and flags
match the earlier plain export; only the input-file hash inventory changes.
Current status remains `review_required` because Phase 7 is still pending, scope
is deliberately partial, and failed-call usage is genuinely unavailable. See
[the gzip check](docs/submission-gzip-self-check.json) and
[the equivalence proof](docs/submission-gzip-check-equivalence.json).

### Failed-call token usage disclosure

Ten TypeSafe connection attempts failed without a response containing usage.
Their `input_tokens` and `output_tokens` remain `null` (20 unavailable fields).
Every attempt is logged as failed and pessimistically charged at its reserved
worst case. These charges are **accounting bounds, not measured token usage**.
No zeroes or estimates have been substituted into token fields.

`data/GRADING_CONTRACT.md:90` says: “Usage/cost claims must be real or clearly
marked unavailable in the README; the checker reports missing usage rather than
inventing it.” The supplied checker at lines 345–347 requires nonnegative integer
usage on **every** event, with no exception for failed calls. Therefore these
20 `invalid_usage` flags are retained honestly. Compression does not clear them.
New production verification/group/memo calls will have their own actual usage or
similarly disclosed unknown values; historical failed-call evidence is not rewritten.

### Recording description draft — links/commit pending owner decision

The descriptions below follow the owner's account; the recordings have not been
opened or inspected. All three are ignored and uncommitted at this gate.

- **Clip 1:** `Recording 2026-10-14 200325.mp4` — **281,644,901 bytes**.
  Shows start, voluntary interruption/drain and resume. A pasted command became
  `scope-evidence beforeSet-Location C:\dev\Spotify` and argparse rejected it;
  no before checkpoint file was saved in this clip. The later, explicitly named
  `checkpoint_before.reconstructed.json` contains 19,719 IDs reconstructed from the
  retained pause receipt and pinned pre-run completed-state intersection with scope.
  It is **post-hoc evidence**, not a file written during the recording. Provenance
  accompanies the canonical grading copy. Proposed delivery: owner-supplied unlisted
  link (pending), referenced here after upload.
- **Clip 2:** `Recording 2026-10-14 225019.mp4` — **156,550,325 bytes**.
  Shows continuation and after-checkpoint attempts. A successful snapshot write
  preserved 22,227 after IDs, but audit encountered a live SQLite lock; a later
  attempt refused to overwrite the immutable checkpoint. Proposed delivery:
  owner-supplied unlisted link (pending), referenced here after upload.
- **Clip 3:** `Recording 2026-10-15 120822.mp4` — **7,246,223 bytes**.
  Shows `scope-proof` passing against unchanged checkpoints: reconstructed before
  19,719 strictly contained in after 22,227, after contained in completed, no before
  IDs in resume enrich calls, and 2,508 newly completed direct paid resume records.
  Proposed delivery: commit this small clip after explicit owner approval; then
  replace this draft delivery note with its repository link. An unlisted link is
  also acceptable if the owner prefers all three hosted together.

The first two files exceed GitHub's 100 MB limit. No uploads, video reads, video
commits or fabricated hosted links occurred. See [metadata inventory](docs/recording-inventory.md).

### Revised Phase 7 proposal (not approved)

Fresh blinded verification of 500 completed production IDs, ten batches of 50,
golden IDs excluded; do not substitute development verifier logs. The estimate is
Luna agreement with final records, not human accuracy, because fallback also uses
Luna. The frozen classifier and hash stay unchanged. The proposed finer taxonomy
has 34 topic/sub-issue cohorts; 46,907 of 70,239 eligible rows remain unspecified.
No production membership, rank, claim or memo has been applied.

[Full taxonomy/top-ten examples](docs/phase7-taxonomy-preview.md);
[verifier bounds](docs/phase7-production-verifier-proposal.json);
[combined gate](docs/phase7-proposal.md). Combined worst case **$1.5704785**,
proposed separate cap **$1.58**; no paid calls before new approval.
