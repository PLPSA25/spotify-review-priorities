# Phase 3 enrichment and recovery

Current implementation update (offline pre-production gate): `scope-run` now has an
eight-worker graceful stop-file wrapper for a prepared store. It drains admitted work,
persists the shared invocation budget and health windows, and resumes only a clean
voluntary pause. See `docs/offline-preproduction-gate.md`; historical Phase 3 notes
below describe the earlier interface. Caching means our exact-text **result cache**
and saved-stage reuse. OpenAI reports 0% provider prompt-cache hits; no savings from
provider prompt caching are claimed or implemented. Fallback and blinded verifier
both use Luna, so verifier-agreement gains partly reflect self-agreement; the owner's
20 judgments supply independent human evidence.

No real provider execution has been performed. Phase 4 must verify the keys, exact
Jev version, returned Luna model and account limits with separately approved tiny calls.
The 500-review milestone is urgent; Class 7's actual date is unknown.

## Human labels

Run `python -m pipeline label-golden`. The interface reads original text and existing
human labels only, never model output. Complete reviews save atomically to
evals/golden_50_human.csv; q/Ctrl+C/EOF leaves the current incomplete review unchanged.
Resume with the same command. Each session has an exclusive .csv.lock file.
Run `python -m pipeline validate-golden` to check the human CSV separately.

## Explicit enrichment

The CLI accepts development or fresh supplied CSVs with the six source fields. Known
course inputs are checksum-checked; every stored original ID gets the supplied helper's
exact row hash. No stars or human answer columns are sent to a provider.

```powershell
# Simulated development only: mocked labels/usage, no keys or network.
python -m pipeline enrich --input data/checkpoint_500.csv --output artifacts/mock-500 --mock

# Later, only after Phase 4 preflight and explicit spending approval:
python -m pipeline enrich --input data/checkpoint_500.csv --output artifacts/checkpoint-500 --confirm-spend
```

The live command prints a conservative projection and requires CONFIRM SPEND, then
checks local key presence silently. Importing modules, tests, help and mock mode never
make paid calls. Never put real keys in command arguments or paste them into chat.
The raw full corpus is guarded until Phase 6 adds the saved-permutation selection;
the approved final scope is 100k plus forced golden IDs, not full classification.

State lives under the chosen output directory. Use a fresh enrichment directory, not
the Phase 1 ingestion database. Reuse the same output path for extension/resume. The
SQLite store refuses changed source fields or changed label_config. It stores the
source strings, hashes, statuses, attempts, work leases, saved stage results and calls.
Distinct-text jobs are claimed transactionally; identical rows keep individual IDs.
Aliases copy all label fields and point directly to a non-cache original with succeeded
enrichment evidence. Cache hits do not create provider-call entries.

The current synchronous adapter sends one review per Jev request and one per Luna
extraction/fallback request, within the 1–50 limit. Thus an invalid review cannot discard
other reviews from a multi-review response. Packing larger Luna batches remains an
optional optimization to evaluate with the pilot; asynchronous Batch and Flex are off.

Request shapes were checked against the official [TypeSafe API](https://docs.typesafe.ai/api)
and [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
Documentation is not evidence that the configured models are available to this account.

Jev asks topic/intent/severity Choices and a sentiment Score in the same request, plus
language and missing-context judgments. Sentiment maps score / 2 - 1. Approved harm
rules are in both prompts; confidence/probabilities are validated but do not certify
semantic accuracy. Short texts use full-text evidence plus explicit entity-term matches.
Longer texts use structured Luna extraction. Low-confidence fallback admission is capped
by floor(distinct texts × fallback fraction); its quota persists across resumes.
Cases outside the quota remain needs_review rather than triggering an expensive switch.

## Controls and calls

Workers share SQLite-backed rolling request/token limits and one project ledger at
artifacts/spend.sqlite3. Mock runs have separate mock ledgers. Defaults: one worker,
Jev 60 requests/s, project API cap $10, per-invocation cap $0.50, fallback fraction 10%.
OpenAI limits are conservative provisional settings, not verified account limits.
Both per-second and per-minute admission are enforced; Phase 4 records actual capacity.

Before each dispatch reserve a conservative byte-based input envelope plus protocol
overhead and the output-token cap. A potential cache-write rate of $0.125/M is reserved
as a conservative documentation-based assumption, not a confirmed measured charge.
Input/output usage is logged verbatim when available. Current settlement calculates
standard uncached-token cost without claiming prompt-cache savings; the Phase 4
calculator will reconcile billing details against saved raw usage and actual tier.
These calculations are estimates from rates, not provider receipts. Byte-envelope
assumptions must be checked against live reported usage; if exceeded, halt admission.

Calls are recorded in SQLite before dispatch, immediately after receiving a response,
and after validation. Each attempt has unique local request ID, role enrich, provider,
requested/returned model, tier, settings, prompts/schema, input IDs, usage, latency,
outcome and initial/resume phase. Raw request/response evidence contains no key headers.
SDK-free HTTP clients have no hidden retries. Reject unapproved models and stop on
Jev version mismatch or any change in Luna's returned model string.

Invalid output gets one repair with the validation error, then quarantine. Retry
transient known-uncharged rejections with bounded exponential backoff and jitter.
Persist retry counts. Unknown responses/timeouts retain their worst-case reservation
and lease, and stop the run instead of silently spending on another attempt. Missing
usage stays null, not invented zero; such events can trigger the checker's invalid_usage
flag and must be explained/reconciled in final evidence.

## Interruption and recovery

Use one worker and `--stop-after N` to stop after N distinct work items. The initial
stop saves checkpoint_before.json. Rerun without stop-after to process only remaining
pending work and save checkpoint_after.json. This is operational support; a real paid
interruption recording and nonempty strict checkpoint extension remain Phase 6 evidence.

Completed rows are never redispatched. After lease expiry, saved validated Jev/Luna
outputs are restored from durable call evidence without another call. In-flight work
with no known outcome remains blocked. A second run also refuses nonexpired active
leases. Do not remove leases to bypass uncertain billing.

If you obtain verified local cost evidence for an unknown reservation, reconcile it:

```powershell
python -m pipeline reconcile-charge --ledger artifacts/spend.sqlite3 --reservation LOCAL-CALL-ID --cost-usd VERIFIED-AMOUNT --evidence PATH-TO-LOCAL-EVIDENCE --confirm-reconciliation
```

This offline command records the evidence hash and verified cost; it does not invent
token counts or copy receipt contents. After lease expiry, rerun the same enrichment
command. Without a saved reply, classification may need another confirmed attempt;
the previous possible charge remains in the ledger. Delayed provider billing and lost
responses prevent an absolute exactly-once billing guarantee.

Exports: enriched.jsonl has completed records, quarantine.jsonl records reasons,
calls.jsonl has attempt evidence, summary.json reports internal pending/completed/
quarantined counts and ledger totals. These are stage artifacts, not the final grading
adapter. Partial-scope export, sampling, verification, grouping, ranking and memo remain
later phases. Mock outputs are clearly marked simulated and must never be submitted as
real predictions, usage, accuracy, measured runtime or cost.
