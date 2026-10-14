# Spotify Insight Pipeline

Phase 3: offline labeler and mocked-tested enrichment infrastructure. No live model calls yet.
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

## Golden labels (human work pending)

Read `docs/labels.md`, then use `python -m pipeline label-golden` to fill the seven fields in
`evals/golden_50_human.csv` yourself. It is an exact blank copy of the supplied golden
file. Do not edit the original CSVs or use Excel. Validate offline:

```powershell
python -m pipeline validate-golden
```

Exit 1 and `needs_human_labels_or_correction` are expected until all 50 are labeled.
The report identifies IDs and field errors, without proposing answers. A successful
schema check does not establish semantic accuracy. Golden answers are evaluation-only
and never model inputs. `golden-template` can create a new copy at an explicitly chosen
output path and refuses to overwrite existing human work.

Tests use per-test workspace temporary directories and remove them automatically,
including after failures. PDFs are ignored. Jev's configured request limit is 60/s;
the account's published 80/s limit is recorded separately in the approved plan.

## Enrichment and resume

See `docs/enrichment.md` for explicit mock/live commands, controls, cache provenance,
interruption/resume and charge reconciliation. Providers use standard-library HTTP
with no hidden retries. Keys, model access and actual limits still require Phase 4's
separately approved tiny calls. The Class 7 date is unknown; prioritize the 500-review run.
No real cost, accuracy or completed 500-review result is claimed yet.
