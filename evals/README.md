# Golden-set workflow

golden_50_human.csv is an exact blank working copy, not model predictions. Complete it
yourself following ../docs/labels.md; preserve all source fields and edit only the seven
human label columns. The supplied ../data/golden_50_to_label.csv remains unchanged.

Run `python -m pipeline validate-golden` from the project root. Until you fill the
labels, exit 1 is expected and golden_validation.json reports the missing work.
After edits, rerun the validator to replace the report atomically. Reports identify
record IDs and field errors; no labels are suggested. These files are local/offline
evaluation artifacts and are never provider inputs or dashboard data.

For a guided offline workflow run `python -m pipeline label-golden`. It saves after each
complete review and resumes past valid human labels. q/Ctrl+C/EOF stops safely. Numbered
menus never display model predictions; custom evidence quotes are checked immediately.
