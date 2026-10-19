# Spotify review priorities

A pipeline that turns Spotify Google Play reviews into a product-priority recommendation.
It preserves original IDs, saved model evidence, deterministic rankings and an owner-approved memo.
The dashboard serves saved aggregate results; it does not classify reviews on demand.

**Recommendation:** test restoring back, seek and repeat controls for free users, measuring complaints alongside Premium conversion. Controls rank second with 4,444 complaints/cancellations and 13,877 severity points; Other--unspecified ranks first but supplies no specific fix target ([grading/ranking.csv](grading/ranking.csv)). Controls also rank second in the seeded random-prefix view, with 4,440 rows and 13,865 points ([docs/phase7/sample_ranking.csv](docs/phase7/sample_ranking.csv)). This supports an experiment, not a causal or revenue claim. See the [owner-approved memo](docs/phase7-memo-draft.md).

> **Start here:** [Decision memo](docs/phase7-memo-draft.md) and [live dashboard](https://spotify-review-priorities.vercel.app).
> - [Ten-point rubric-to-evidence map](#rubric-to-evidence-map).
> - Zero-API profile: `python -B data/check_submission.py profile --full data/spotify_reviews_18months.csv --out <outside-repo>/ingestion.json`.
> - Zero-API reference: `python -B data/check_submission.py reference --full data/spotify_reviews_18months.csv --analysis data/spotify_reviews_18months.csv --out <outside-repo>/local-reference.json`.
> - Zero-API check: `python -B data/check_submission.py check --reference <outside-repo>/local-reference.json --submission grading --out <outside-repo>/self-check.json`.
> - [Ranking replay](scripts/replay_baseline_ranking.py): `python -B scripts/replay_baseline_ranking.py --out artifacts/ranking-replay` (output not in the repository).

## Live dashboard

**https://spotify-review-priorities.vercel.app** -- open signed out; no login should be required. Signed-out alias UI: **owner-verified 2026-10-19 (incognito)**; phone: **owner-verified 2026-10-19**; Protection: **Standard Protection; access confirmed signed out; owner screenshots 2026-10-19**; build log: **[NOT YET]**. These UI/access checks are owner-verified, not machine-verified.

The app reads a saved aggregate snapshot from Neon through `dashboard_reader`, a read-only role, and makes no model calls on page load ([web/lib/data.ts](web/lib/data.ts), [web/app/Dashboard.tsx](web/app/Dashboard.tsx)). Its footer identifies the data source and snapshot ID:

`2d29566238c93179d4518f4eb08cc5c0e45e0f125fe1a9d103a0ce0ff6b0282e`

Source: [docs/phase8-snapshot-manifest.json](docs/phase8-snapshot-manifest.json). Saved HTTP evidence reports Neon; the saved HTTP evidence is complemented by the owner verification above. The human-evaluation summary is bundled in [web/lib/human-check.json](web/lib/human-check.json), not read from the database. [Deployment evidence and remaining checks](docs/phase8-deployment-evidence.md).

## Rubric-to-evidence map

**Deliverable quality (4): points 1-4; Testing & evaluation (3): points 5-7; Working result (3): points 8-10.** One row per point in the assignment's Grading Rubric (10 points). Status is our evidence assessment, not an awarded score.

| Point / criterion | Self-assessed evidence status (not a grade) | Evidence and actual outcome |
|---|---|---|
| 1. Accessible code/setup and artifacts | Partial | [Setup](#setup-and-offline-commands), [grading](grading/), [contract](data/GRADING_CONTRACT.md). Code and final submission artifacts are available locally; source CSV and private store are not bundled; recordings are included under evidence/recordings/. |
| 2. Clear architecture, shared schema and provenance | Complete | [Schema](pipeline/schema.py), [configuration](config.toml), [manifest](data/manifest.json), [checkpoint provenance](grading/checkpoint_before.provenance.json), [snapshot exporter](pipeline/dashboard_snapshot.py). IDs, source hashes and label configuration connect stages. |
| 3. Memo numbers linked to correct calculations and source evidence | Complete | [Memo](docs/phase7-memo-draft.md), [claims](docs/phase7/claims.csv), [secondary claims](docs/phase7/secondary-claims.csv), [arithmetic](pipeline/rank.py), [final comparison](docs/phase8-deployment-evidence.md). All 35 baseline issues and 140 baseline claims match saved deployed evidence; UI links currently download CSVs rather than explaining claims inline. |
| 4. Coherent recommendation, alternatives and limitations | Complete | [Approved memo](docs/phase7-memo-draft.md), [original model memo](docs/phase7/memo-draft.json), disclosures below. Controls experiment weighed against ad-cap alternative; no causal revenue inference; owner edits preserved separately. |
| 5. 50 human labels, per-field comparisons and error analysis | Complete | [Golden report](evals/golden-final-evaluation/report.html), [error analysis](docs/golden-error-analysis.md), [label revisions](docs/golden-human-accuracy-gate.md). Topic 37/50; intent 42/50; exact severity 36/50; severity within one 48/50; sentiment sign 41/50; needs_review 23/50; severity MAE 0.34; sentiment MAE 0.1857 (report.json). Errors remain; entities were not human-labeled. |
| 6. Independent verification plus planted-error and injection tests | Partial | [Verifier agreement](docs/phase7/verifier-agreement.json), [planted error](tests/test_human_review.py), [injection boundary](tests/test_enrichment.py). Of 500 blinded verifier rows, 462 had Jev labels checked by Luna (different model); 38 had Luna fallback labels checked by Luna (same model). Different-model verification is meaningful, but neither subset is human accuracy and duplicate texts induce dependence. Planted-error test detects wrong/missing predictions; injection test uses MockTransport and checks untrusted-input separation, not live adversarial robustness. |
| 7. A real 100-review cold/warm pilot, correct offline cost/runtime calculator, and demonstrated retry, spending and recovery controls (T3) | Partial | [Measurements](cost/measurements.json), [replay](cost/replay.json), [calculator tests](tests/test_calculator.py), [retry tests](tests/test_enrichment.py), [spend controls](tests/test_controls.py), [recovery](docs/100k-halt-recovery-gate.md). Cold run classified 100 but memo failed after 58.6224091s; memo-only continuation succeeded in 5.265659s. Warm run 0.0212832s, zero new calls/spend. Pilot API $0.007171879; local compute cost unknown. Real stop/resume, halt and lock failures are disclosed, not hidden as a clean first attempt. |
| 8. Full ingestion, record coverage and successful classification | Partial | [Profile](grading/ingestion.json), [records](grading/records.jsonl.gz), [completion gate](docs/phase6-completion-gate.md). All 660,622 IDs accounted for; only 237,722 of 660,609 nonempty rows classified. 422,845 out-of-scope, 42 terminal and 13 empty quarantines. 237,722 valid classification records, of which 77,874 are direct model classifications (62,542 Jev + 15,332 Luna fallback) and 159,848 are exact-text reuse of a saved result; whether reuse counts toward the 100,000 minimum in the Definition of Done is the instructor's decision. |
| 9. A runnable staged program with bounded calls, saved handoffs and demonstrated resume | Partial | [CLI](pipeline/__main__.py), [operator guide](docs/100k-production-commands.md), [recovery guide](docs/100k-recovery-operator-guide.md), [proof](grading/checkpoint_before.provenance.json). Bounded stages and persisted resume exist; one generic arbitrary-CSV command covering enrichment through memo is missing. Recorded proof grows 19,719 to 22,227 completed with 2,508 new paid records and no before-ID relabels. |
| 10. Reproducible baseline ranking and a usable deployed dashboard, connected through a backend to the processed data in a database, with grounded AI-generated recommendations | Partial | [Ranking](grading/ranking.csv), [API](web/app/api/dashboard/route.ts), [data layer](web/lib/data.ts), [deployment evidence](docs/phase8-deployment-evidence.md), [memo](docs/phase7-memo-draft.md). Saved HTTP evidence proves Neon snapshot reads; reader passed 7/7 denial probes. Database holds processed aggregates, not the full row store. Owner verified signed-out/phone access and Protection; build-log inspection remains open; AI memo is owner-edited. |

## Setup and offline commands

Source: [Kaggle dataset, version 2](https://www.kaggle.com/datasets/bwandowando/3-4-million-spotify-google-store-reviews). The assignment CSV is a transformed date-window subset, not the downloaded archive. Its SHA-256 is `1fc85de68a304dd8978b537cfa58793d5f41cbaf417fa32cb53899f83a2fcef6`; archive SHA-256 is `7b351f41fef9de9d8cba07ac40a300d20fd605ff0298a1885df0dbf0d66b3cbc` ([data/manifest.json](data/manifest.json)). Grader supplies the subset at the path above; the source identity is recorded in the manifest. The local copy matched the expected SHA-256.

Python 3.11+ ([pyproject.toml](pyproject.toml)); verified interpreter Python 3.12.10. The minimum is justified by standard-library tomllib and datetime.UTC imports, not an execution test on 3.11; pipeline/checker use the standard library. [requirements-dev.txt](requirements-dev.txt) pins pytest/ruff and their supporting packages; there is no requirements.txt. The checker imports only argparse, csv, hashlib, gzip, json, math, sys, collections, decimal and pathlib: **no third-party packages required**. Web requires Node 24.x and the committed package-lock.json ([web/package.json](web/package.json)). Dependency installation requires internet access; the verification and replay commands are offline. Role prompts: [Jev v3](prompts/jev-v3.json), [Luna enrichment v2](prompts/luna-enrich-v2.txt), [verifier/group/memo instructions](pipeline/pilot_stages.py), [production role instructions](pipeline/phase7.py). Label definitions: [docs/labels.md](docs/labels.md), [schema](pipeline/schema.py), [contract](data/GRADING_CONTRACT.md). Ignore policy: [.gitignore](.gitignore). `.env.example` passed a content-safe structural check: 3 lines, each a comment or an uppercase variable name followed by `=` with no value. No line content was printed. Database setup: [web/README.md](web/README.md), read alongside the corrected [reader SQL](web/db/01-reader-role.sql) and [verification evidence](docs/phase8-reader-verification.txt); the web README documents the deployed snapshot, restricted LOGIN role and verification procedure.

PowerShell (repository root):
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Push-Location web
npm.cmd ci
Pop-Location
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider -q
Push-Location web
npm.cmd test
npm.cmd run typecheck
Pop-Location
```
POSIX shell (repository root):
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
(cd web && npm ci)
.venv/bin/python -B -m pytest -p no:cacheprovider -q
(cd web && npm test && npm run typecheck)
```
Offline validation (2026-10-19): **226 Python tests passed**; **9 web contract tests passed**, typecheck passed. Web results are from the preceding unchanged-app check. Production build/browser verification is recorded separately in [deployment evidence](docs/phase8-deployment-evidence.md); build-log inspection remains open. Commands/tests: [tests/](tests/), [web/package.json](web/package.json).

CSV-path staged entry point, no manual pasting (offline mock, enrichment only; [CLI](pipeline/__main__.py)):
```powershell
.\.venv\Scripts\python.exe -B -m pipeline enrich --input data/cost_100.csv --output artifacts/verify/mock-enrich --mock  # output not in the repository
```
```sh
.venv/bin/python -B -m pipeline enrich --input data/cost_100.csv --output artifacts/verify/mock-enrich --mock  # output not in the repository
```
Verified result: `SIMULATED enrichment states: {'completed': 100}`, exit 0; data/cost_100.csv is tracked. This does not demonstrate paid-model quality.

**Missing:** one generic CSV-path command running all stages through verified grouping/ranking/memo. Paid mode is deliberately gated; do not infer authorization from these examples.

Offline baseline regeneration from tracked saved membership and enriched records ([replay script](scripts/replay_baseline_ranking.py), [aggregation](pipeline/rank.py)). The output directory must not exist; output is local and not in the repository.
```powershell
.\.venv\Scripts\python.exe -B scripts/replay_baseline_ranking.py --out artifacts/ranking-replay  # output not in the repository
```
```sh
.venv/bin/python -B scripts/replay_baseline_ranking.py --out artifacts/ranking-replay  # output not in the repository
```
The replay checks all six fields and issue order against grading/ranking.csv. It requires no raw CSV, sampling permutation, private database or model call. The random-prefix secondary view separately requires the private sampling permutation (not in the repository).

Offline calculator replay in a fresh copy of cost/ ([calculator](pipeline/calculator.py)). These output directories are not in the repository; neither command changes the saved cost reports:
```powershell
New-Item -ItemType Directory -Path artifacts/cost-replay -ErrorAction Stop | Out-Null  # output not in the repository
Copy-Item -LiteralPath cost -Destination artifacts/cost-replay/cost -Recurse  # output not in the repository
.\.venv\Scripts\python.exe -B -m pipeline cost --directory artifacts/cost-replay/cost  # output not in the repository
```
```sh
mkdir -p artifacts
mkdir artifacts/cost-replay  # output not in the repository
cp -R cost artifacts/cost-replay/cost  # output not in the repository
.venv/bin/python -B -m pipeline cost --directory artifacts/cost-replay/cost  # output not in the repository
```
Copy the supplied cost folder without adding credential files to it. Replay dispatches no models. [Saved replay](cost/replay.json), [rate-sensitivity tests](tests/test_calculator.py). Unknown local compute cost stays unknown; projected runtime is not measured full-run runtime.

## Grader quick start

Supply the unchanged `data/spotify_reviews_18months.csv`; it is intentionally excluded from Git. Its expected identity is in [data/manifest.json](data/manifest.json). Create the project venv using the setup section above before running these zero-API checks.

From the repository root in PowerShell, send generated reports outside the repo. The saved reference is 164,162,495 bytes, approximately 164 MB (measured file: `artifacts/final-checks/local-reference.json (not in the repository)`, local-only).

```powershell
$checks = Join-Path $env:TEMP 'spotify-grading-checks'
if (-not (Test-Path -LiteralPath $checks)) { New-Item -ItemType Directory -Path $checks | Out-Null }
.\.venv\Scripts\python.exe -B data\check_submission.py profile --full data\spotify_reviews_18months.csv --out "$checks\ingestion.json"
.\.venv\Scripts\python.exe -B data\check_submission.py reference --full data\spotify_reviews_18months.csv --analysis data\spotify_reviews_18months.csv --out "$checks\local-reference.json"
.\.venv\Scripts\python.exe -B data\check_submission.py check --reference "$checks\local-reference.json" --submission grading --out "$checks\self-check.json"
```

POSIX shell equivalent (repository root):
```sh
checks="$(mktemp -d /tmp/spotify-grading-checks.XXXXXX)"
.venv/bin/python -B data/check_submission.py profile --full data/spotify_reviews_18months.csv --out "$checks/ingestion.json"
.venv/bin/python -B data/check_submission.py reference --full data/spotify_reviews_18months.csv --analysis data/spotify_reviews_18months.csv --out "$checks/local-reference.json"
.venv/bin/python -B data/check_submission.py check --reference "$checks/local-reference.json" --submission grading --out "$checks/self-check.json"
```

The profile command does not overwrite submitted evidence. Compare its parsed JSON with `grading/ingestion.json`; the check command checks the submitted profile against the reference. The checker reads the two gzip JSONLs directly: do not extract plain counterparts into `grading/` ([data/GRADING_CONTRACT.md](data/GRADING_CONTRACT.md), [data/check_submission.py](data/check_submission.py)).

Expected result: **`review_required`**, with exactly `invalid_usage: 20` and `unfinished_classification: 1`; the unavailable fields are `input_tokens: 10` and `output_tokens: 10`. Source: `artifacts/final-checks/self-check.json (not in the repository)` and [docs/phase8-deployment-evidence.md](docs/phase8-deployment-evidence.md). These are disclosed below, not a clean pass or an assigned grade. Any additional flag needs investigation.

## Final production/export and coverage

Final production invocation: `7180188e-0938-4d2f-8e2b-6bf412cf77ca` ([docs/100k-final-status.json](docs/100k-final-status.json)). This ingests the full corpus but classifies a budgeted partial scope. Final [grading/records.jsonl.gz](grading/records.jsonl.gz) contains 237,722 completed; 422,845 out-of-scope quarantined; 42 terminal-failure quarantined; 13 empty quarantined ([completion gate](docs/phase6-completion-gate.md)). 237,722 valid classification records, of which 77,874 are direct model classifications (62,542 Jev + 15,332 Luna fallback) and 159,848 are exact-text reuse of a saved result; whether reuse counts toward the 100,000 minimum in the Definition of Done is the instructor's decision. The 100,001 figure is completed rows within the selected 100,041-ID production scope (100,000 seeded prefix plus forced golden IDs, with overlap); 40 selected rows were terminal. The 237,722 total also includes prior/imported work and exact-text propagation beyond that scope.  Quarantined rows are in the same archive, not discarded. Total quarantined 422,900; total rows 660,622; nonempty denominator 660,609 ([profile](grading/ingestion.json), local `artifacts/final-checks/self-check.json (not in the repository)`).

Coverage-point arithmetic: **0.2 x 1 + 0.2 x (237,722 + 422,900) / 660,622 + 0.6 x 237,722 / 660,609 = approximately 0.615912**. This assumes profile match and accepts the checker's valid completed/quarantined rows; **our arithmetic; the instructor decides** ([contract/checker](data/check_submission.py), saved self-check). It does not award the full rubric score.

Final export instructions and private-input requirements: [pipeline/final_export.py](pipeline/final_export.py). Fresh output only; no promotion is implied:
```powershell
New-Item -ItemType Directory -Path artifacts/final-export-new  # output not in the repository
.\.venv\Scripts\python.exe -B -m pipeline.final_export --out artifacts/final-export-new  # output not in the repository
```
```sh
mkdir artifacts/final-export-new  # output not in the repository
.venv/bin/python -B -m pipeline.final_export --out artifacts/final-export-new  # output not in the repository
```
Ten final submission files matched grading/ in the independent saved replay; four raw pre-overlay intermediates differed as expected ([export evidence](docs/phase8-deployment-evidence.md)). Profile is generated separately by the grader command above. No re-import was needed: snapshot ID stayed unchanged.

## Cost summary

Model API spend: **$5.629964013** = `ledger.spent_nanodollars: 5629964013` in [final Phase 7 receipt](docs/phase7/receipt.json); confirmed against read-only SUM(spent) in private artifacts/spend.sqlite3 (not in the repository), reservations table. Not a provider invoice.
Production invocation: **$4.834135303 / $7.28 cap** = `invocation_committed_usd` / `shared_cap_usd` in [final production status](docs/100k-final-status.json); spent amount also confirmed against the invocation's 4,834,135,303 ledger nanodollars.
Project: **$5.629964013 / $10 cap**; same final receipt ledger total and `controls.project_api_cap_usd` in [config.toml](config.toml). Earlier production status predates Phase 7: $5.604212288 + final receipt `invocation_spent_usd` $0.025751725 = $5.629964013. Local compute and hosting billing are separate/unreconciled.

## Glossary

- **Jev:** configured `jev-1.13.0`, fixed label judgments ([config.toml](config.toml), [pipeline](pipeline/)).
- **Luna:** configured `gpt-6-luna`, bounded extraction/fallback, blinded verification, grouping and memo ([config.toml](config.toml), [pipeline](pipeline/)).
- **Scope:** seeded partial production selection, distinct from full-corpus ingestion ([config.toml](config.toml), [scope plan](docs/100k-production-plan.json)).
- **Checkpoint:** saved completed-ID/evidence boundary used to prove resume without paid relabeling ([provenance](grading/checkpoint_before.provenance.json)).
- **Cohort/issue:** deterministic grouping of complaint/cancellation records; cross-topic rules can differ from primary topic ([frozen rules](docs/frozen-grouping-v3.json)).
- **severity_sum:** sum of severities for an issue's complaint/cancellation rows; the baseline priority score ([pipeline/rank.py](pipeline/rank.py)).
- **Cache alias:** another original ID reusing an exact-text saved result under unchanged label_config; not provider prompt caching ([completion gate](docs/phase6-completion-gate.md)).
- **Terminal failure:** bounded attempts exhausted or unrecoverable validation failure, retained as a quarantined row rather than silently retried forever ([halt gate](docs/100k-halt-recovery-gate.md)).

## One review, end to end

Review ID: `7e271329-4c82-403b-a59a-7fd8b6c40405`.

| Step | Actual saved evidence | Source |
|---|---|---|
| Original text | "New update is worst we can't skip song from a particular timing to a particular instant and also i am not able to play songs in order it is in shuffle mode and to play in order buy premium this is the worst update ever." | `data/spotify_reviews_18months.csv`; public bounded copy in the dashboard snapshot, selected by `pipeline/dashboard_snapshot.py` |
| Labels | Completed; topic `usability`; intent `complaint`; severity 3; sentiment -0.99; entities `["premium"]`; `needs_review: true`, reason `low_confidence`. Evidence quote is the original text. | [grading/records.jsonl.gz](grading/records.jsonl.gz), original ID above |
| Group | `cross-topic--free-tier-premium-controls`: Free-tier playback controls locked behind Premium. The cross-topic grouping does not rewrite the primary label. | [grading/membership.csv](grading/membership.csv), [names](docs/phase7/group-names.json), [frozen rules](docs/frozen-grouping-v3.json) |
| Baseline rank | Rank 2; count 4,444; severity_sum/priority 13,877; mean 3.122637. | [grading/ranking.csv](grading/ranking.csv), matching issue ID |
| Claims | B2 = count 4,444; B3 = severity_sum 13,877; B6 = mean 3.122637; `cross-topic--free-tier-premium-controls:priority_score` = 13,877. | [grading/claims.csv](grading/claims.csv) |
| Recommendation | The memo quotes "to play in order buy premium" and proposes a controlled test restoring back, seek and repeat, considering Premium conversion alongside complaints. | [Owner-approved memo](docs/phase7-memo-draft.md); original model output [memo-draft.json](docs/phase7/memo-draft.json) is preserved separately |

## Recordings and timestamp index

The three recordings are included under evidence/recordings/. Timing facts are verified by frame review; times approximate, about 10 seconds. Clip 1 is the owner's chosen **unedited, compressed, silent, 7:12 recording**. The PC taskbar clock on 10/14/2026 and on-screen counters are the real-time reference.

| Clip | Approximate time | Frame-reviewed event |
|---|---|---|
| [Clip 1: run, stop, resume](evidence/recordings/clip1-run-stop-resume_2026-10-14.mp4) | 0:00 | 7:53 PM; blank terminal and Codex window with operator instructions. |
| Same | ~0:12 | Multi-line paste warning. |
| Same | ~0:18 | git rev-parse 8d2592a; scope-status prepared: completed 19,719, pending 80,321, quarantined 1, saved_new_jev_scores 0, cap $7.28. |
| Same | ~0:24 | scope-authorize --acknowledge-spend: "authorized offline; zero calls"; scope-run --confirm-spend starts. |
| Same | ~0:30 | Right terminal scope-status --watch: running, invocation 7180188e-0938-4d2f-8e2b-6bf412cf77ca, saved_new_jev_scores 19. |
| Same | 0:36-5:06 | 7:53-7:59 PM; saved scores about 109 to 4,764; project_spent_usd about 0.775 to 1.003; cap_latched false. |
| Same | ~5:06 | Monitor output ends at 4,764; elapsed_segment_seconds 303.3. |
| Same | ~5:54-6:00 | 7:59 PM; New-Item artifacts/scope-100k/stop.request (not in the repository); last write 7:59 PM. |
| Same | ~6:00 | 8:01 PM; scope-run stopped_user, drained True, wall_seconds 349.4; scope-status stopped_user, saved_new_jev_scores 5,570, safe_to_resume true. |
| Same | ~6:06-6:48 | scope-evidence before typed, not run. |
| Same | ~6:54 | 8:02 PM; paste error "invalid choice: 'beforeSet-Location'", no before file saved; scope-run --resume typed; monitor phase resume/running, scores 6,570. |
| Same | 7:06-7:12 | Resume continues, scores 6,653 then 6,738; clip ends mid-run. |
| [Clip 2: SystemicFailure and recovery](evidence/recordings/clip2-systemicfailure-recovery_2026-10-14.mp4), duration 2:40 | 0:00 | History shows SystemicFailure; recovery_ready with 19,876 scoped completed. |
| Same | ~0:32 | scope-continue --recovery; completed rises from 20,813 to 20,856. |
| Same | ~1:04 | AI-chat window visible; completed passes 21,000; owner reviewed the clip; no sensitive content reported. |
| Same | ~1:36 | scope-evidence after typed; completed 21,375. |
| Same | ~2:08-2:30 | Two database-is-locked failures, then Immutable checkpoint already exists. |
| [Clip 3: scope proof](evidence/recordings/clip3-scope-proof_2026-10-15.mp4), duration 0:48 | ~0:10-end | scope-proof pass: before 19,719; after 22,227; no before IDs in resume calls; 2,508 new paid records. |

There is an **unrecorded gap between Clips 1 and 2**; these are not a continuous recording. Saved receipts and recovery evidence document that gap but cannot prove what was on screen. Sources for timestamps: the supplied verified frame-review index; file sizes and hashes are recorded in the submission inventory.

The scope-run stop receipt's `counts` covers the whole imported reviews table; scope-status `scope_counts` covers only the production_scope join. Thus 28,224 completed / 80,321 pending / 6 quarantined in the former and 19,719 completed / 1 quarantined in the latter have different denominators, not contradictory progress. Sources: [run_segment](pipeline/graceful.py), [State.counts](pipeline/state.py), [production.status](pipeline/production.py).

## Disclosures and limitations

- **Partial scope:** 237,722 / 660,609 nonempty reviews completed, **35.99% rounded**; every original ID remains accounted for. Quarantined benchmark omissions count as incorrect. Exact-text propagation weights repeated text; compare both ranking scopes. Sources: [deployment evidence](docs/phase8-deployment-evidence.md), [secondary claims](docs/phase7/secondary-claims.csv).
- **Reconstructed before-checkpoint:** a pasted scope-evidence command was rejected; no before file was saved in Clip 1. The before set was reconstructed afterward with provenance, not presented as contemporaneous video evidence. Sources: [checkpoint provenance](grading/checkpoint_before.provenance.json), [recovery guide](docs/100k-recovery-operator-guide.md).
- **SystemicFailure halt:** the mixed-stage monitor double-attributed Jev terminal failures to finalization, producing a false finalization failure signal. At that diagnostic gate there were 78 failed Jev attempts: 75 invalid-output attempts and 3 HTTP 499 responses, not 78 terminal reviews. An additional persistence defect left 133 valid outputs saved but unfinalized; they were recovered offline without new calls. Fixes separated stage monitoring, persisted valid siblings before propagating a halt, and handled floating-point ties; the historical gate reports 162 passing regression tests. Approved continuation retained the same invocation, total cap, history and terminal quarantines. Sources: [halt diagnosis](docs/100k-halt-recovery-gate.md), [applied recovery](docs/100k-offline-recovery-result.json), [continuation guide](docs/100k-recovery-operator-guide.md). Historical counts are not final corpus accuracy.
- **Unrecorded gap:** there is a gap between Clips 1 and 2. Clip 1 is unedited; the taskbar clock and counters are the real-time reference. The timing index was verified by frame review.
- **Locked DB:** the recorded after-checkpoint/audit attempts hit SQLite locks. Read-only status/proof access now has a 5,000 ms busy timeout and at most four attempts with bounded backoff; writes and model calls are not replayed. Source: [phase6-completion-gate.md, Live-read repair](docs/phase6-completion-gate.md).
- **Unavailable tokens:** ten historical failed calls have unknown input/output usage: 20 fields remain null, split 10 input_tokens and 10 output_tokens. Costs were pessimistically accounted; no fabricated zeros or dashboard reconciliation. Sources: [deployment evidence](docs/phase8-deployment-evidence.md), [historical usage disclosure](docs/phase6-completion-gate.md).
- **V1 to V3 grouping:** recall fixes came from development spot-checks, not golden labels. V3 was frozen; no ranking-driven reopening. Lexical cohorts can still miss or misassign cases. Source: [phase7-gate.md](docs/phase7-gate.md), [frozen rules](docs/frozen-grouping-v3.json).
- **Golden-label revisions:** four labels were revised after an AI-assisted contract-rule check; final decisions were the owner's. Golden labels were excluded from prompts/routing/calibration; entities were not hand-labeled and were excluded from evaluation. Source: [golden-human-accuracy-gate.md](docs/golden-human-accuracy-gate.md).
- **Owner-edited memo:** the original model draft and owner-approved edits are separate artifacts; editorial work was not logged as a new model call. Sources: [approval](docs/phase7/memo-owner-approval.json), [original output](docs/phase7/memo-draft.json), [approved memo](docs/phase7-memo-draft.md).
- **Verifier self-agreement:** of the 500 blinded verifier rows, **462 were Jev-labeled and checked by Luna** (different model), and **38 were Luna fallback-labeled and checked by Luna** (same model). These are row counts, not distinct-text counts; duplicate texts induce dependence. Verification supplies a second model on 462 rows, while the 38-row subset partly reflects self-agreement; neither is human accuracy. Source: [verifier-agreement.json](docs/phase7/verifier-agreement.json).
- **Verifier bug 25001:** sending informational queries and transaction probes together prevented the transaction-mode change. Splitting into separate query parts fixed the observed run; reader verification passed all denial probes. Source: [deployment evidence](docs/phase8-deployment-evidence.md), [reader transcript](docs/phase8-reader-verification.txt).
- **Reader-password incident:** the owner reports a read-only password was exposed in a chat screenshot and rotated before production use. No values are reproduced; rotation was not independently inspected. Source: [deployment evidence](docs/phase8-deployment-evidence.md).
- **Bundled human evaluation:** the app imports a saved aggregate summary; it is not fetched from Neon. Sources: [web/lib/human-check.json](web/lib/human-check.json), [web/app/Dashboard.tsx](web/app/Dashboard.tsx).
- **Documented failed case:** review `014df5d4-c2dc-4e7c-9a18-d874bd80fef5` hit a machine-precision argmax rejection; the validator was repaired for future acceptance, but this frozen run retained the terminal outcome. Semantic rule errors also remain documented. Sources: [halt diagnosis](docs/100k-halt-recovery-gate.md), [golden error analysis](docs/golden-error-analysis.md), [counted limitations](docs/confirmed-rule-limitations.json).
- **AI assistance (owner-confirmed):** code was written with ChatGPT Codex and reviewed with Claude under owner direction, with all spend and decisions owner-approved. Source: owner-confirmed disclosure.
- **Deployment checks:** signed-out alias UI owner-verified 2026-10-19 (incognito); phone owner-verified 2026-10-19; Protection: Standard Protection, access confirmed signed out, owner screenshots 2026-10-19. Build log [NOT YET]; billing consoles remain unverified. These are owner checks, not machine verification. Source: [deployment evidence](docs/phase8-deployment-evidence.md).

## Repository layout

| Path | Purpose |
|---|---|
| `pipeline/` | Ingestion, classification, recovery, grouping and export code; `final_export.py` documents the saved-evidence adapter. |
| `grading/` | Submitted gzip records/calls, profile, membership, ranking, baseline claims and checkpoint evidence. |
| `cost/` | Saved pilot, editable rates, calculator/replay evidence; [instructions](cost/README.md). |
| `data/` | Course contract/checker/manifests; graders supply the ignored original CSV. |
| `evals/` | Golden evaluation and human-review evidence. |
| `web/` | Dashboard source, server-only read model and bundled aggregate evaluation. |
| `tests/` | Offline Python tests; app contract/browser tests are under `web/tests/`. |
| `docs/` | Evidence and indexed historical records; see [STATUS](docs/STATUS.md). |
| `artifacts/` | Local runtime/private state and temporary checks; not a public reproduction dependency bundle. |

## Reproducibility limits

The submitted `grading/` can be checked using the supplied source CSV and course checker without model calls. Full regeneration needs the private local production SQLite store, checkpoints and saved Phase 7 call/membership artifacts; they are not all included in Git. **The Neon database contains only the aggregate/sample dashboard snapshot, not that production store.** [pipeline/final_export.py](pipeline/final_export.py) documents its exact inputs, offline command, optional output directory and overwrite refusal.

Identical gzip packaging was independently verified for the final submission outputs, with fixed gzip metadata. An arbitrary new model run is not promised to reproduce labels, latency or costs. A changed snapshot payload requires offline validation and the [re-import rule](docs/phase8-deployment-evidence.md); unchanged payloads must retain the published snapshot ID.

## Documentation status

[docs/STATUS.md](docs/STATUS.md) distinguishes current evidence from historical/superseded records and identifies frozen sources. [docs/build-log.md](docs/build-log.md) preserves the historical development log; use this README for current instructions.

