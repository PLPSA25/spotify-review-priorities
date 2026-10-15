# 100k halt diagnosis and proposed recovery — no execution

Historical pre-approval diagnosis. The owner subsequently approved offline recovery;
applied actions, reconstructed evidence and owner-run continuation commands are in
`docs/100k-recovery-operator-guide.md` and `docs/100k-offline-recovery-result.json`.
The statements below describe the earlier diagnostic gate, not current readiness.

Offline audit only. No paid calls, resume, window/latch reset, live state mutation,
quarantine release, offline label replay or official checkpoint reconstruction was
performed. Code fixes and mock tests are prepared, not applied to the saved run.
The complete sanitized failed-call list and measured counts are in
`docs/100k-halt-diagnosis.json`.

## What stopped

Invocation `7180188e-0938-4d2f-8e2b-6bf412cf77ca`, phase `resume`, failed at
finalization with exact exception:

`SystemicFailure: Terminal failures 3/20 exceed 5% rolling threshold`

The monitor arithmetic matched the implemented rule. Its **sampling/attribution was
wrong for the two-pass pipeline**: Jev quarantines entered both the classification
monitor and the finalization monitor, while successful Jev scores entered only the
classification monitor. Thus three rare classification terminal failures were
accumulated in the otherwise empty finalization window. When final records began
completing, it read 3 failures / 20 outcomes. After eight admitted workers drained,
the saved finalization window was 3/27. Classification and connection windows were
each healthy at 0/100. The true Jev terminal fraction was 3/75,874 distinct new texts,
not a 15% Luna failure rate. This is a monitoring design defect, not an outage or
cap stop. The 5% threshold itself is unchanged in the proposed fix.

## Calls and items

Production calls (both segments): 75,949 TypeSafe Jev calls = 75,871 succeeded and
78 failed. Those failed calls involved 75 unique review IDs:

- **75 invalid-output attempts:** exact error
  `Invalid output: Choice differs from highest-probability option`.
  Sixty-nine items recovered on their permitted repair; three failed both attempts
  and remain terminal (six of the 75 failed attempts).
  Offline replay of the saved invalid attempts under the numerical fix identifies
  **eight machine-precision false rejections** and 67 attempts still invalid. This
  replay made no requests and did not rewrite calls or revive terminal records.
- **Three HTTP 499 responses**, all TypeSafe Jev during resume. The local generic
  logged message is `connection error, charge unknown, accounted as charged`, but
  `original_error` is **HTTP 499**, not a diagnosed TCP connect failure. No transport
  connect/post-send diagnostic was attached. All three recovered on bounded retry;
  $0.000654738 was pessimistically charged for their unknown outcomes. Do not
  describe them as proven connect failures, or reconcile them via dashboards.
- **Eight OpenAI extraction calls:** all returned successfully; 160 per-ID outputs,
  157 valid, three invalid quotes. Partial-valid calls are logged `succeeded` while
  recording their `validation_errors`; this does not mean every item was valid.
- **Zero production Luna fallback calls** were dispatched. Extraction batches come
  first in the persisted routing selection.

Three terminal distinct texts affect **four selected review IDs** (one exact-text
alias). They are retained, not retried. Existing imported terminal records are
separate. The three quote-invalid items remain pending: their single permitted
isolated repair was never dispatched because finalization had already halted.

Representative exact errors (full IDs, no payloads or credentials):

- `3bbab369-2722-48ea-8ab2-0739a9b3d5f7`: TypeSafe / Jev / resume, attempts 1 and 2:
  `Invalid output: Choice differs from highest-probability option`.
  Topic choice billing had probability 0.42, versus usability 0.43. Genuine local
  consistency-validation failure; do not reinterpret its label to bypass it.
- `6ee89fe5-6900-43ce-9c54-43078ac506e1`: same error on attempts 1 and 2. Billing
  0.46 versus usability 0.47000000000000003. A substantive gap, not float noise.
- `014df5d4-c2dc-4e7c-9a18-d874bd80fef5`: same error on attempts 1 and 2, **a code
  bug**: language choice nonenglish_understood has 0.45999999999999996 against
  english 0.46, a mathematical tie represented differently in binary floating
  point. Alias `ad5f72c8-46a5-4d6c-8dea-2469ee0b2ed0` shares this terminal work.
- `9c26c4a3-3935-4668-b51f-e2ff62172499`: OpenAI / extraction / resume:
  `Quote must be a nonempty exact source substring`. Same error on
  `982b0813-1eae-479b-93d9-bf39aa319e37` and
  `a34b6a36-c503-4be8-86ba-0a6423dab967`. Invalid model output, not terminal yet;
  no quote replacement/normalization is proposed.
- `547aab3e-f1a4-4771-939a-0b8177a148f3`: TypeSafe / Jev / resume: original error
  `HTTP 499`, logged as `connection error, charge unknown, accounted as charged`.
  Retry succeeded. The other two HTTP 499 IDs and all failed calls are in JSON.

The three double-invalid items occurred at 03:56:33–34, 04:00:14 and 04:10:22–23
UTC on October 15 (spread through scoring, not a startup burst). Extraction started
around 04:39:33 UTC. All times are saved provider-call log timestamps, not inferred
from the recording.

## Valid response salvage and integrity

Another code defect is exposed by the monitor: per-batch finalization stopped on
the first raised monitor exception. Across already admitted batches, only **24 of
157 valid Luna outputs** reached final records. **133 valid outputs remain durably
stored in `calls.validated_results`**, validated again by this audit against their
source text/schema/hash. They can be finalized offline under the existing succeeded
calls, with zero API calls. No paid result is lost or requires re-requesting.

Read-only checks:

- SQLite integrity: **ok**; zero held leases, zero reserved charges and zero unresolved
  call outcomes. No cap latch exists.
- **75,871 new saved Jev scores** exactly match the new-text keys with succeeded Jev
  calls; all saved score records pass structural label validation.
- New distinct work: **24 completed / 75,847 pending / 3 quarantined**.
- All **28,248 completed internal records** pass schema/reason/quote validation;
  cache origins resolve directly, without alias chains.
- `calls.jsonl`: **84,585 unique request IDs**, matching all SQLite calls by canonical
  content hash, including imported provenance. No missing, duplicated or changed
  exported call record. Summed new call accounting equals invocation ledger spend.

## Why 28,224 versus 19,719 at the interruption

Terminal A's receipt used `State.counts()`: **all internal imported development and
selected-scope reviews**. `scope-status` joins `production_scope`: only the declared
100,041 selected IDs. Difference: **8,505 completed imported IDs outside the selected
scope**, retained for provenance and direct cache origins.

At the voluntary pause: internal completed 28,224; scoped completed 19,719.
Now: internal completed **28,248**, scoped completed **19,743**; the same difference
8,505 remains. These are review-ID counts, not distinct-text or score counts. Current
selected scope: completed 19,743 / pending 80,293 / quarantined 5. No contradictory
classification result or lost completion is implied by these counting bases.

## Recording and checkpoint evidence — missing before file

There is **no production `checkpoint_before.json`** in the project, including the
expected production directory. The only matching file found is the old Phase 3
synthetic smoke-test checkpoint, which cannot be used for production. Therefore
there is no existing production before checkpoint to pronounce valid, and the
current `scope-evidence after` command cannot pass as-is.

The original pause set is recoverable deterministically: the initial segment receipt
shows no new final completions at the pause (28,224 internal), the preserved base
store identifies its completed exact texts, and the pinned selected CSV identifies
the selected source IDs. Their intersection gives exactly **19,719 before IDs**.
All subsequent production resume call IDs were checked: **zero intersect that set**.
Already 24 new scoped completions have real succeeded paid resume extraction calls;
the remaining 133 valid outputs can also be recovered without payment.

Proposed after approval: write a **clearly marked post-hoc reconstruction**, with
base-store, selection and original pause-receipt hashes and reconstruction timestamp.
Never claim that file was saved during the recording, never edit the recording or
use the old synthetic checkpoint. With that provenance, strict subset/call exclusion
proof can pass now or after continuation. The machine audit can verify the sets and
paid calls; it cannot certify that a retrospectively reconstructed file satisfies an
instructor's expectation of a contemporaneous snapshot. Disclose the limitation.
No official checkpoint file or reconstructed list was written by this diagnostic.

## Proposed fix and tests — not a live recovery

Prepared code changes:

1. Allow only absolute **1e-12 floating-point equality noise** in the Jev argmax
   consistency validator. A 0.01 gap still fails. No prompt, confidence/margin,
   label definition or quota change. Keep all three existing terminal works
   quarantined; do not change the persisted routing selection or silently revive
   the float-tie case in this run.
2. Attribute Jev terminal failures solely to its classification monitor, which
   receives both successful and failed Jev items. Finalization monitoring receives
   completed/terminal finishing items only. Keep >5%, rolling 100, minimum 20.
3. Save all valid siblings to stage results before finalization can raise. If a
   systemic monitor trips, latch the in-memory admission stop, finish persisting
   all already-paid valid siblings, and then propagate the failure. Never admit
   further repairs/new requests after the stop.

**No window has been reset or modified.** The pure proposal in
`docs/100k-monitor-migration-proposal.json` retains original windows in the unchanged
receipt, leaves classification and connection histories identical, and proposes
removing the three **duplicate-attribution** Jev failures from the finalization
window: 27 mixed observations → 24 successful finalizations. Those failures remain
in classification history/seen keys and the immutable original receipt/call logs;
no actual finalization failure is erased. This is an explicitly reviewed stage
repartition requiring approval, not a silent reset. If its exact provable history
shape differs, the migration refuses to guess. The float-case quarantine remains.

Regression tests cover float ties versus a genuine gap; Jev failures not polluting
the finishing window; all valid paid siblings committed even when the monitor
raises; and a pure migration preserving original/classification/connection histories
while refusing ambiguous histories. **162 tests passed; pipeline/tests lint passed.**

Hash remains **21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c**.
The hash does not include Python implementation bytes. The numeric fix changes
future acceptance of machine-precision ties, not the intended highest-probability
rule. Existing terminal records, labels, persisted rankings and fallback selection
remain unchanged. No paid Jev rerun, calibration rerun or 10k reprocessing is proposed.

## Proposed continuation under the same invocation

Only after explicit yes: back up the drained state/evidence; commit reviewed code
locally including the video ignore entry; pin an explicit recovery receipt to that
commit, current state, original authorization and original invocation ID; perform
the approved stage-history repartition and offline replay of 133 valid results;
then continue pending stages at eight workers. Original receipts remain immutable.
The normal `--resume` remains correctly blocked for `failed` state and changed code;
do not change status to stopped_user or fabricate a manual stop to bypass it.
A separately guarded recovery entry point/authorization is required after approval.

No failed Jev item is released. No saved Jev score is requested again. Three
quote-invalid extraction IDs get their existing single permitted repair, not a fresh
retry allowance. Original attempt histories, classification/connection health,
fallback quota/selection and ledger persist. No latch is cleared (none exists).

After proposed offline replay, pending work is 75,714 distinct texts: **54,771 local
zero-call completions**, **5,769 extraction IDs**, **15,174 fallback IDs**. Remaining
root requests upper bound **292 extraction + 759 fallback = 1,051**, including the
three already-needed isolated quote repairs; connection/output repairs can add
bounded requests. Expected paid finishing spend from the measured development mix
is **$1.165205**. Shared 1rps spacing alone requires at least 17.5 minutes for these
root requests; including observed repair incidence gives roughly 25 minutes of
request spacing, before unmeasured local/SQLite overhead. This is not measured
remaining wall-clock time or a completion promise.

- Invocation already accounted: **$3.704475953**, including all failures.
- Remaining approved invocation allowance: **$3.575524047**.
- Original total invocation cap stays **$7.28 under the same run ID**, so the ledger
  automatically allows at most the remaining amount. Do **not** replace its total
  cap with $3.575524047 while keeping that run ID: it already spent more than that.
- Additional cost under the proposed unchanged hard cap is at most
  **$3.575524047**, not a newly allocated $7.28. No raised cap is proposed.
- Project now **$4.474552938 / $10**; at the entire remaining allowance, maximum
  **$8.050076985**, leaving $1.949923015.
- Completion is not guaranteed at the cap. Conservative byte/output reservation
  totals for the remaining root batches alone are **$3.65371725**. An intentionally
  loose upper envelope charging four singleton byte-bounded attempts for every
  remaining paid item is **$87.017121**, far above the cap (and overstates normal
  batched work). That is **not authorized spend**. The runner must stop new
  admissions at the remaining $3.575524047 rather than try to fund that envelope.
  The observed-mix estimate is about one third of the remaining allowance.

Stop at this recovery gate. No paid continuation, offline replay, official checkpoint
reconstruction, live monitor migration, terminal-item release or local commit was
performed. Original authorization is not silently renewed for changed code.
