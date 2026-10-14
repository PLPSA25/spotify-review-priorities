# Phase 2 gate — actual results

Completed October 13, 2026 (America/Los_Angeles). No model calls or API spend.

Before Phase 2, deleted only the explicitly requested ignored failed-ingestion file
artifacts/ingestion/tmpjlgwb0lz.sqlite3.tmp and artifacts/test-temp* directories, after
verifying their resolved paths were inside this workspace. The published state.sqlite3
remains intact. Tests now use a per-test TemporaryDirectory under artifacts/ and clean
up automatically even when a test fails. No test-temp directories remain.

Set Jev dispatch headroom to 60 requests/s in config.toml. Added *.pdf to .gitignore;
the course PDF remains local and is ignored, with no PDF tracked. All prior ignore
entries and the blank .env.example remain unchanged.

Phase 2 deliverables:

- docs/labels.md: all eight topic definitions, intent precedence, severity definitions,
  non-golden worked examples, sentiment/entities/quote/needs_review conventions, and
  safe UTF-8 CSV hand-labeling instructions.
- evals/golden_50_human.csv: byte-identical blank copy of the supplied golden template;
  all seven human-label fields blank for all 50 records. No answers were prefilled.
- pipeline/labels.py and CLI commands golden-template / validate-golden: offline checks
  for exactly the original 50 IDs, duplicates/missing IDs, preserved original fields,
  exact labels, finite sentiment, integer severity, entity arrays, true/false spelling
  and nonempty exact-substring evidence. Template creation refuses overwrite.
- evals/golden_validation.json: actual current report. Status is
  needs_human_labels_or_correction; 50 blank records, 0 valid records. Exit 1 is expected
  until the owner supplies all labels. This is not label evaluation or an accuracy score.
- config.toml: predeclared sentiment tolerance 0.25, with MAE also planned for evaluation.

Final checks:

```text
pytest: 18 passed in 0.29s
ruff: All checks passed!
pip check: No broken requirements found.
All five source CSV checksums still match manifest.json.
Golden working copy matches source bytes and all label cells remain blank.
git check-ignore .env and course PDF: both ignored.
git ls-files -- .env '.env.*' '*.pdf': only .env.example.
No test-temp directories or requested failed-ingestion temporary file remain.
```

The tests use synthetic review fixtures, not predicted labels for the golden set.
They cover valid and invalid labels, source alteration, accent/multiline quote matching,
NaN/out-of-range sentiment, duplicate/missing IDs, malformed CSV, blank-copy fidelity,
overwrite refusal and the existing ingestion protections. Network connections are
blocked for all tests.

Issues corrected during this phase: ruff found an import ordering error, fixed before
the final run. A no-overwrite hard-link publication attempt was blocked on Windows;
template publication now uses Windows atomic rename (which refuses an existing target)
and a POSIX hard link on other platforms. The final Windows tests passed.

Gate: inspect the label definitions, examples and blank human-label copy, then approve
Phase 3. Human labeling remains owner work and should precede final evaluation. Class 7
date is still unresolved: the supplied answer repeats the literal placeholder [DATE].
The checkpoint_500 run must be ready before the actual Class 7 date, once supplied.
