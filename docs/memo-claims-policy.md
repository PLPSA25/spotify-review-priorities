# Revised memo: claims and checker policy

[GRADING_CONTRACT.md](../data/GRADING_CONTRACT.md), line 62, requires
`claims.csv` “for each material issue-level number in the memo.” Line 100 adds:
“Supported automated metrics are `complaint_count`, `severity_sum`,
`mean_severity`, `priority_score`; explain other quantities separately.” It
also explicitly permits a secondary business ranking and requires human review
of the prose and numerical evidence.

[check_submission.py](../data/check_submission.py), lines 300–311, reads
`claims.csv` and compares each value to the recomputed **baseline** issue row.
It flags unsupported metrics, unknown issues and mismatches. It does not read
the memo or verify that prose citations are complete. Therefore a clean claim
check is mechanical consistency, not certification of the memo's reasoning.

The selected approach retains the requested secondary comparison in the memo:

- [claims.csv](phase7/claims.csv) has only allowed baseline metrics, with compact
  B references for the memo's baseline counts, severity sums and means.
- [secondary-claims.csv](phase7/secondary-claims.csv) separately labels random-prefix
  counts/sums, ranks, the controls-to-ads ratio and coverage/unspecified percentages.
  Its S references are explicitly secondary analyses, not baseline claims; this
  file is not passed to the supplied baseline checker as `claims.csv`.
- [extended-claims.csv](phase7/extended-claims.csv) preserves the full earlier
  evidence table. The six-decimal mean-severity claims support the rounded means
  in the memo; the ratio and percentages are calculated from saved values.

An alternative is to move all secondary numerical analysis to the README and
leave only qualitative comparisons in the memo. Putting secondary numbers in
the main baseline claims file, even using an allowed metric name, would be
incorrect: their values differ from the baseline and the checker would flag them.
The selected approach follows the contract's permission to explain other
quantities separately; those supplementary figures remain subject to human review.

The owner-directed rewrite is offline editorial work on the saved memo-role
output, not another model execution. The original response and call log are
preserved. The selected quote was verified as an exact substring of its original
review. The propagation example was checked against actual memberships and the
seeded prefix. No classifier, grouping rule, human golden label or frozen hash
was changed. The final owner-approved revision compares observed additional
baseline rows directly, supported by S11/S12 subtraction claims. The uniform
random prefix is the sampling frame; its observed classified ranking excludes
terminal failures. The additional-row comparison is not a measurement of the
issue mix of unclassified texts. “Additional” corrects the proposed “duplicated”:
two additional ad texts are absent from the prefix. Approval is recorded in
[memo-owner-approval.json](phase7/memo-owner-approval.json).

The checker is run against `artifacts/phase7/grading-check`, containing unchanged
production records, all saved production/Phase 7 calls, current memberships and
rankings, and the revised baseline claims. Committed grading gzip files remain
untouched pending the single final submission export.

## Measured revision check

The supplied checker completed with **zero claim-related flags** against that
working submission. Remaining flags: `invalid_usage: 20` (historical unknown
token usage) and `unfinished_classification: 1` (declared partial scope).
See [the actual checker output](phase7/memo-revision-self-check.json) and
[compact result](phase7/memo-revision-result.json). The local
[memo citation audit](phase7/memo-claim-audit.json) reports no unresolved B/S
references and an exact-substring quote check. These separate audits do not
claim that the supplied checker reads prose or validates secondary analyses.
No API calls were made for this revision. Targeted regression tests: 9 passed;
Ruff checks passed.

After the final owner-approved edits, the supplied checker was rerun against
the same working submission: again **zero claim-related flags**, with the same
two historical/declared flag types. See
[owner-approved checker result](phase7/memo-approved-result.json) and
[full audit](phase7/memo-approved-self-check.json). No grading gzip was rewritten.
