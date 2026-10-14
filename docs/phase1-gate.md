# Phase 1 gate — actual results

Completed on October 13, 2026 (America/Los_Angeles). No model calls or API spend.

The eleven supplied course files were moved to data/ without byte changes. All five
CSV SHA-256 values matched manifest.json after the move and again after ingestion.
The PDF remained in root. Existing .env.example and ignore entries were preserved.
Git was initialized; files are staged for review, with no commit or push performed.
Git attributes disable text conversion for all supplied course files.

Full ingestion results in artifacts/ingestion/:

- Source rows: 660,622; no duplicate review IDs.
- Empty review texts: 13, quarantined as empty_review_text.
- Missing app versions: 159,701.
- Distinct nonempty exact texts: 484,189.
- Internal pending rows: 660,609. Classification has not started.
- SQLite integrity_check: ok; stored row count 660,622.
- Exact profile is ingestion.json; extended report is ingestion_report.json.
- data_manifest.json records source identity, supplied manifest/checker hashes and provenance.

Actual validation:

```text
pytest: 3 passed in 0.10s
ruff: All checks passed!
pip check: No broken requirements found.
git check-ignore .env: .env
git ls-files -- .env '.env.*': .env.example
git ls-files -- data/spotify_reviews_18months.csv: no output
CSV checksums: True
```

Tests cover exact multiline/Unicode source preservation and row hashes, empty-text
accounting, checksum refusal and refusal to overwrite an existing state store. Network
connection functions are blocked automatically in tests.

Failures encountered and corrected: sandbox temporary-file access blocked pip bootstrap;
approved escalation completed it. Sandbox DNS blocked PyPI access; approved escalation
installed project-local pinned tools. The first ingestion/test implementation used a
SQLite transaction context without closing the connection, causing Windows rename
failure. Explicit closing fixed it; tests and full ingestion then succeeded. The first
failed full ingestion left an ignored temporary database for debugging; it is not the
published state store and is not staged. Scratch ingestion uses an in-memory journal and
is disposable on interruption; future enrichment recovery is Phase 3 work.

Approval required before Phase 2. Class 7 date remains unresolved because the answer
contained the placeholder [DATE]. Sampling, model verification, enrichment, cache
propagation, grading export, memo and deployment remain later-phase work.
