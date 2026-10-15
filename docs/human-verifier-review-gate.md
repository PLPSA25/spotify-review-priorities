# Human verifier-disagreement review — complete

The owner adjudicated all 20 selected development cases, one target field per review, with four cases per field. Golden IDs and exact golden texts, and terminal records, were excluded. No model calls were made and no predictions/configuration were changed.

Overall verdicts: **Jev right 5; verifier right 12; both wrong 3; unclear 0**.

- Topic: Jev right 1; verifier right 3.
- Intent: Jev right 4.
- Severity exact: verifier right 2; both wrong 2.
- Sentiment sign: verifier right 3; both wrong 1.
- needs_review: verifier right 4.

These are judgments of a deterministic, stratified **disagreement-only sample**, not model accuracy on all reviews. A verdict applies only to its displayed target field, not every label on the row. Both-wrong verdicts do not provide replacement labels. The four needs_review cases had Jev=true and verifier=false; the owner's verdicts favor false in those four cases. This does not estimate a population flag error rate or authorize threshold/routing changes.

Source verdicts and displayed cases: `evals/verifier-human-review.json`. Machine-readable totals and field breakdown: `evals/verifier-human-review-summary.json`. All 20 verdicts were saved atomically from explicit owner answers. There are no unanswered cases.

Frozen hash remains `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`. The subsequently approved golden collection/evaluation is complete; see `docs/golden-final-evaluation-gate.md`. Its actual cost was $0.002603841, below the approved $0.076 cap. The 100k run remains draft-only; see `docs/100k-run-plan-draft.md`.
