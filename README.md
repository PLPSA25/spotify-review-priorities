# Spotify Insight Pipeline

Phases 1–3 are complete. Phase 4 provider preflight and the recovered cold/warm
100-review pilot are complete; see docs/phase4-status.md and cost/report.md.
Python 3.11+; developed on Windows with Python 3.12.

## Approved scope

Ingest all 660,622 source rows. Later classify the first 100,000 nonempty IDs of a saved,
seeded permutation, union the golden 50, and propagate validated labels by exact text.
Keep every original ID. Export all other nonempty rows as quarantined with
`not_classified_partial_run`; empty texts use `empty_review_text`.

This deliberately conflicts with the course contract's full-classification requirement.
The owner approved this partial scope. The final checker will report
`unfinished_classification`; benchmark omissions count as incorrect. Coverage credit is
reduced. The preliminary 36% completion / 0.62 coverage-point estimate is not measured.
Actual sampling and propagation counts will be reported in a later phase, along with a
random-sample-only ranking to expose repeated-text selection bias.

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
