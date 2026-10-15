# Golden evaluation and production decision gate — October 14, 2026

All 50 final-hash predictions are complete: six IDs reused completed exact-text results; 44 new distinct texts were classified. The approved cap was $0.076; the runner enforced the tighter reviewed $0.075555748 envelope. Measured: **46 requests, 9.382519 seconds, $0.002603841 reported usage** (Jev $0.002137716; Luna $0.000466125), zero failed calls, zero new terminal records. Project accounted spend **$0.770076985 / $10**, reserved $0. No 100k or downstream paid work was dispatched.

## Accuracy and actual fallback split

Against the owner's 50 final labels, all predictions remain in the denominators. In each line: overall; independent Luna fallback; no independent fallback.

- Topic: **37/50 (74%)**; 2/4 (50%); 35/46 (76.1%).
- Intent: **42/50 (84%)**; 2/4 (50%); 40/46 (87.0%).
- Severity exact: **36/50 (72%)**; 0/4 (0%); 36/46 (78.3%).
- Severity within ±1: **48/50 (96%)**; 2/4 (50%); 46/46 (100%).
- Sentiment sign: **41/50 (82%)**; 3/4 (75%); 38/46 (82.6%).
- needs_review: **23/50 (46%)**; 3/4 (75%); 20/46 (43.5%).

The fallback group is **n=4**, nonrandomly selected by confidence. These group percentages are descriptive, not a causal fallback comparison or an accuracy estimate for broader fallback routing. Cache aliases inherit the original work's classification route. Extraction-only Luna use is not classification fallback. No predictions are missing. Severity MAE is 0.34; sentiment MAE 0.1857; sentiment within 0.25 is 33/50 (66%). The needs_review confusion counts are TN 17 / FP 25 / FN 2 / TP 6. There was no predeclared golden pass threshold; do not call this an accuracy-gate pass.

**Entities are excluded:** they were not hand-labeled; empty arrays are intentional. Four golden labels were revised after an AI-assisted check against contract rules; final labels are the owner's decisions. Human labels were opened only by evaluation code after prediction collection. Golden results did not change prompts, thresholds, routing, models or the hash.

The saved report offers all six confusion tables for overall/fallback/no-fallback: `evals/golden-final-evaluation/report.html`. Matrices have **human rows / prediction columns**, including a missing column. Reproducible JSON: `report.json`; CSVs beside it and in `luna_fallback/` and `no_luna_fallback/`. Numeric rendering checks verified all 18 group/field views against source counts; desktop-browser visual preview was blocked by local socket access, so no screenshot-based layout check is claimed.

## Development-only fallback decision input

Recommendation was frozen in `docs/fallback-options-development.json` **before golden evaluation** (timestamp recorded in that file). It reads final-hash analysis predictions, independent development verifier labels and the owner's 20 judgments; no golden answers or evaluation results. Golden IDs and exact golden texts are excluded from development quality comparisons. Primary quality counts use unique texts; aliases are not counted as independent examples.

Among 3,422 eligible completed development texts, actual fallback outcomes exist for 840 (the selected low-confidence tail): **630/840 (75%) changed at least one core label**. Individual changes: topic 232/840; intent 233/840; severity exact 288/840; severity difference beyond 1 is 55/840; sentiment sign 152/840. Final needs_review changed 345/840. A core change means topic, intent, severity exact or sentiment sign; harmless same-sign numeric shifts are not counted.

Blinded Luna verifier differs from Jev on **235/400 eligible unique texts (58.75%)** (402 rows before exact-text collapse). On 115 eligible texts with both actual fallback and a verifier result, core disagreement with the verifier fell **82/115 → 51/115**. Corrected/regressed relative to verifier: topic 20/11; intent 14/11; severity exact 28/11; severity beyond 1 7/1; sentiment sign 10/5; needs_review 48/2. These are verifier comparisons, not human correctness; the verifier is a different blinded prompt, not an observed counterfactual fallback for unselected texts.

Incremental rank-band opportunity: in the 10–20% tranche band, verifier differs from Jev on 29/51 (56.9%); in 20–30%, 31/52 (59.6%). Both have zero severity errors beyond 1 relative to verifier. No measured 20%/30% fallback quality gain is available; do not extrapolate the lowest 10% change/correction rate to higher bands as accuracy improvement.

Human review: all 20 cases produced 5 Jev-right / 12 verifier-right / 3 both-wrong. Among the 12 fallback-eligible cases: 4 / 6 / 2. Six eligible cases actually used fallback; among five with a determinate preferred shown label, fallback matched that preference in 3 and differed in 2; the remaining both-wrong case supplies no replacement label. All four intent verdicts favored Jev over the verifier, but that does not mean all actual fallback intent answers were wrong. Only one of the four needs_review human cases was fallback-eligible: raising the cap will not fix auxiliary-only flags in the other three. Persistent context/language flags cannot be cleared by fallback, and no flag rule is changed.

## Modeled 100k options — not applied

After golden reuse: 75,874 new distinct texts, 15,174 maximum fallback slots at 20%. All options keep eight workers and the same hash.

- **10%:** 7,587 slots; **$4.50 base, 1.78h**, retain the proposed original **$6.80 cap**.
- **20%:** 15,174 slots; **$4.85 base, 1.89h**, proposed **$7.28 cap** (rounded up from 1.5× base). About **+$0.35 /+6.5 minutes** versus 10%.
- **30%:** 22,762 slots; **$5.19 base, 2.00h**, proposed **$7.79 cap**. About **+$0.69 /+12.9 minutes** versus 10%.

**Recommend 20% as a moderate development-supported expansion, not a proven human-accuracy gain.** It leaves substantial project budget and routes another 7,587 eligible texts; 30% has no measured marginal correctness benefit. More fallback can also regress correct Jev labels. The proposal is frozen independently of the golden outcomes above and **has not been applied**; actual config remains 10%. `fallback_fraction` is under controls and excluded from `label_config`; tests verify identical hashes at 10/20/30%. A changed cap can still change new output routes. Existing completed/cache results stay unchanged, and a tranche's chosen fraction must persist across resume.

Cost model includes the replacement of extraction by fallback for long texts, newly paid fallback for short texts, offline repacking at 20/30%, measured per-mode cost/repair rates and shared 1rps Luna pacing. Time normalizes the measured optimized Jev stage and finishing work for saved scores. Assumed mix/repair/latency transfer is uncertain; these are estimates, not paid worst-case guarantees. The hard invocation ledger cap may stop a run before completion.

## Production draft and preflight

`docs/100k-run-proposal-draft.json` and `docs/100k-run-plan-draft.md` propose 8 workers / 20% / $7.28 across interruption and resume. A local reviewed commit is required before starting, excluding `.env`, full raw CSV, PDFs and private notes; no push. No production commit/run has happened at this gate.

TypeSafe balance **$10.41 user-reported**; expected Jev≈$3.71 (user rounded $3.80), conservative≈$5.56 (user rounded $5.70). Recheck live before production; no old-outcome dashboard reconciliation is performed. OpenAI org limit is $20, but **actual organization remaining budget is not verified**. Project logged OpenAI spend $0.184522225 is not the org-wide total. Proposed Luna production estimate $1.15 base / $1.72 at 1.5×; verify remaining org headroom plus unbilled usage and either cover the full remaining shared invocation allowance or enforce an approved provider subcap. Disk free ≈282.73 GiB; conservative operational requirement 10 GiB, rechecked before start. At full $7.28 spend, project total would be $8.050076985, leaving $1.949923015 below $10.

The draft specifies the graceful stop-file command in a second terminal after 200 new canonical completions while 200 routed Luna IDs still await work; drain, save `checkpoint_before.json`, resume under the same shared budget/selection, then save `checkpoint_after.json` and run `audit-resume`. It proves strict subset growth, zero before IDs in resumed calls and real paid new originals. The 8-worker graceful-stop production wrapper is still a required implementation/test step, not falsely presented as runnable today. After the run, exact-text propagation is offline and all remaining nonempty out-of-scope rows are quarantined as `not_classified_partial_run`, with every original ID retained.

Stop at this gate. No automatic 100k, extra verifier, grouping or memo calls.
