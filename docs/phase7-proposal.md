# Revised Phase 7 gate — not approved, no paid calls

This supersedes the earlier two-call/$0.03 proposal. Keep the frozen classifier
prompt, 0.60/0 flags and hash unchanged. No new Jev/enrichment calls or golden
evaluation. No development verifier calls will be merged as production evidence.

## Fresh production verification

The proposed sample is **500 uniform completed original IDs** from the final
propagated export, excluding the 50 golden IDs: population **237,672**. The immutable
seed is `spotify-final-production-verify-500-v1`; sort SHA-256(seed + ':' + review_id)
and take the first 500. Sample IDs/digest, source CSV digest and input bounds are
saved in `phase7-production-verifier-proposal.json`. The source CSV remains local
under ignored runtime artifacts. Selection uses no labels, flags or routing.

The sample has **371 distinct exact texts**. Do not deduplicate it: repeated texts
are part of the completed-row population. Golden IDs are excluded; other IDs sharing
a golden text are eligible, preserving row weighting. No human golden answers were
read or sent. This is a quality estimate for completed rows, not all 660,609 nonempty
rows and not a distinct-text accuracy sample.

Ten initial **50-record** calls carry **role verify**. Each sees only original IDs,
review text, contract rubric and the existing blinded verifier instructions/schema,
including independent language/context diagnostics. Jev/fallback/final predictions
are withheld. Schema/role output limits are operational verifier settings and do
not change classification identity. Compare final stored labels only afterward:
topic, intent, severity exact and ±1, sentiment sign, needs_review; split by final
flagged/unflagged and fallback/nonfallback. Report unresolved items explicitly and
exclude them from disagreement denominators. Entities are outside this accuracy
comparison. Preserve row/unique-text counts and dependence limitations.

This is **verifier agreement, not human accuracy**. Luna also supplied fallback;
blindness to predictions does not remove model self-agreement. The earlier 20 human
verdicts are independent but selected disagreements, not a random accuracy sample.
No prompt/threshold/routing updates will be made from this final check.

Every valid item is saved before isolated repair of invalid siblings. One semantic
repair per invalid item, bounded connection retries/backoff, pessimistic accounting,
**four total attempts per sampled ID across batch and singleton repair**, existing
separate >5% rolling failure monitors (100-window, minimum 20 observations). No
whole-batch rerun after receiving valid siblings. An item exhausted after repair or
connection retries is terminal; continue unless a systemic monitor stops the stage.
Do not redraw replacements or automatically resume a halted invocation.

### Verifier worst case

Pinned reservation rates: input max(normal, cache-write) **$0.125/M**, output
**$0.50/M**; no prompt-cache savings. Each root payload is fixed and bounded by its
canonical UTF-8 bytes plus 2,048 protocol tokens (11,633–13,572); root output cap
10,000. Singleton repair input bounds are computed from each fixed repair payload
(maximum 7,444), output cap 200. Before execution enforce these stored bounds on
**every attempt**, and reject changed samples/config/payloads before dispatch.

For each 50-ID batch let R be the root reservation and S the sum of 50 singleton
repair reservations. With at most four attempts per ID, its envelope is
`max(t*R + (4-t)*S for t in 1..4)`. Here each maximum is `R + 3*S`:
one root response can leave all 50 invalid, then each singleton repair may consume
three attempts including connection retries. This bound deliberately ignores savings
from early failure-monitor halts. Maximum total verifier calls: **1,510**.

- Ten roots, no repairs/retries: **$0.065724125** reservation upper bound.
- One semantic repair for all 500, no extra HTTP retries: **$0.55177825**.
- Including all permitted connection/total attempts: **$1.5238865 worst case**.

These are conservative byte/output bounds, not expected spend. No first-pass or
repair incidence is assumed. Bounds sum integer nanodollar reservations in the JSON.
An earlier $0.755 verifier budget would not fund this full four-attempt envelope.

## Group → rank → claims → memo

Recommended grouping: **34 deterministic topic × sub-issue cohorts**, rather than
just eight topics. Full taxonomy, eight-topic comparison, all counts and top-ten
pairs of original example IDs: `phase7-taxonomy-preview.md` and JSON.
This is an **offline proposal**, not applied production membership/ranking.

Use frozen primary topic and earliest matching within-topic lexical rule; equal
positions use fixed rule order; residuals stay unspecified. One membership per
completed complaint/cancellation; stable issue IDs and separate grouping-rule hash.
English lexical cohorts are not semantically validated defect clusters and can
misinterpret feature mentions. **46,907 / 70,239 rows (66.8%) remain unspecified**;
this must not be disguised as an actionable defect. `other--unspecified` remains
baseline rank one. Ads is the largest specifically identified cohort by priority;
the memo must compare the random-prefix ranking before recommending an action.

Two new **role group** Luna calls each consume at most 25 fixed issue IDs, up to two
distinct-text examples per group (at most 50 input review IDs), no golden exact-text
examples. They produce bounded names/assessments, not arbitrary membership or label
changes. Any substantive rule/membership revision returns to a gate. These are the
calls that supply production group-role evidence. Group output cap 2,048; input
bound 24,000 per attempt including schema, instructions, protocol and repair suffix;
at most four total attempts per call, eight group attempts maximum.

Code-only ranking uses **all 237,722 completed rows**, membership for all **70,239**
complaints/cancellations, priority=severity_sum, descending then issue ID, means
six-decimal half-up. Separately rank the **first 100,000 permutation IDs only**
(exclude forced golden additions outside prefix), one contribution per original
sampled ID; disclose terminal omissions and repeated-text propagation bias.

Code generates baseline claims matching the checker; a separately namespaced
`sample_claims.csv` and local validator support secondary-view numbers. Never insert
sample values into baseline claims.csv: the provided checker compares only baseline
membership. Every memo/appendix number identifies its scope, file and claim ID.

One new **role memo** Luna call receives saved aggregates and bounded evidence, never
full corpus. Input bound 24,000 per attempt, output cap 1,200, up to four attempts.
Validate cited claim/review IDs; render numbers in code. Include alternatives,
partial/lexical limitations, duplicate bias, cancellation intent versus observed
churn, verifier correlation, unknown usage and checkpoint provenance. No live models
in the dashboard. If the bounded pack does not fit, stop rather than silently raise
its envelope or truncate required evidence.

### Combined cost gate

- Fresh production verifier: **$1.5238865**.
- Two group calls, all four attempts: `2*4*(24000*.125+2048*.50)/1e6`
  = **$0.032192** (finer grouping well below the requested $0.50 ceiling).
- Memo, all four attempts: `4*(24000*.125+1200*.50)/1e6` = **$0.0144**.
- **Combined worst case: $1.5704785**.
- Proposed separate invocation cap **$1.58**, shared project cap stays **$10**.
- Normal root count **13** (10 verify + 2 group + 1 memo); maximum **1,522 attempts**.
- Current project **$5.604212288**; at worst case **$7.174690788**, at full proposed
  cap **$7.184212288**. Recheck actual OpenAI credits before dispatch; earlier
  user-reported balances are stale. This does not reuse or reset the completed
  production invocation or any of its failure windows.

All requests use the pinned Luna model, effort none, standard tier; log returned
model/tier, payloads, usage, attempt, outcome and artifact references. Fail closed
on changed model/rates/payload/scope. Stage envelopes and the combined ledger cap
must be enforced before network calls. Those paid-run guards require implementation
and tests before dispatch; this document authorizes none of it.

After the approved stages: merge **new** production role logs (not development
verification), regenerate grading files in a fresh staging directory, gzip level 9,
verify round-trip hashes, rerun the full checker. Partial-scope and genuinely
unavailable-usage flags remain disclosed. Deployment is a later gate.

## Offline submission work already authorized and completed

Both full JSONL exports are gzip level 9, deterministic header, exact decompression
hashes verified: calls **26,686,127 bytes**, records **52,450,579 bytes**. Both are
under 100,000,000 bytes and are committed directly under grading/. The explicit
owner instruction allows the records gzip above the earlier 50 MB limit. Raw copies
remain local/ignored under `artifacts/scope-100k/submission-raw/`. No release asset,
LFS, field removal, fake token usage or video commit. See packaging manifest/checker
comparison and README grader command. No paid stage ran. Stop at this gate.

Offline validation at this revised gate: **176 tests passed**;
`ruff check pipeline tests` passed. Gzip grader results match the plain export
except filename/hash inventory. Production ledger still $5.604212288, no reserved
funds or pending leases, frozen classification hash unchanged.
