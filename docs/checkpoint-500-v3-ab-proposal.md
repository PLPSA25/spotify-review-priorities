# Current-rule audit and checkpoint v2/v3 proposal — October 14, 2026

No paid calls or proposed flag-policy adoption. Current hash remains
`c79a70421de9caad53c9932393f0eb6420f6d80e249cb9097dd5af3eb9d8eba9`.

## Exact wording and correction

GRADING_CONTRACT.md, line 49:

> Cancellation intent does not automatically raise severity. Missing context should trigger `needs_review`; do not invent impact. Write examples of how you applied these shared definitions.

This explicitly says missing context **should** trigger the flag. It does not say
that a provisional first-model judgment is authoritative, or that flags must remain
sticky after independent fallback. The earlier claim that this sentence requires
preserving every Jev missing-context flag after fallback was an interpretation,
and was too strong. Likewise it does not mandate preserving a low-confidence
flag after another classifier supplies a replacement prediction.

The semantic project declaration in docs/labels.md lines 122–124 is:

> needs_review: lowercase true or false. Mark true for missing impact/topic context,
> unclear interpretation, unsupported language or unresolved ambiguity. Evaluate this as
> a prediction; it neither quarantines a record nor proves other labels correct.

Current independent Luna fallback is instructed to flag missing context, and can
reassess the original text. Therefore clearing a Jev context/low-confidence signal
does not by itself demonstrate a semantic contract/declaration violation. A final
prediction that overlooks genuinely unresolved missing context would violate the
rule; model disagreement is evidence to inspect, not human proof of that fact.

The non-English declaration at docs/labels.md lines 102–105 requires flagging
understandable non-English and unsupported language. Current parser enforces the
original non-English flag after fallback (pipeline/classify.py lines 181–182);
all 265 model-identified language flags remain true.

There **is a documentation/implementation discrepancy** in the freeze snapshot:
docs/frozen-label-config.json line 51 says "Every returned non-English/not-understood
language result or missing_context >= 0.5 forces needs_review; missing auxiliary
answers invalidate v3 output." Read as a final sticky guarantee, this overstates
the implemented context behavior. Jev parsing enforces both initial triggers;
fallback enforces original language but independently reassesses context/core flags.
That snapshot description was written too broadly. It is metadata, not a hashed
enrichment field, and does not itself describe an implemented invariant.
Keeping the implemented hash is reasonable if this is documented accurately;
no runtime/hash change is needed to clarify the description. The historical
snapshot has been left intact here; this audit records the discrepancy explicitly.

Of 3,000 slice rows, 191 initially flagged rows became unflagged after fallback.
All 191 had low core confidence; 73 also had initial missing-context signals;
zero had a language flag. In the 500-row verifier sample, 38 such rows were cleared,
and the verifier still reports missing context/needs_review on five. This is a
potential semantic disagreement to disclose, not grounds for declaring the entire
60.77% final-flag behavior mechanically invalid. The sticky-rule proposal in
v3-verifier-gate.md remains optional, unapproved and unapplied.

## Same-row A/B proposal — requires a new yes

Re-enrich data/checkpoint_500.csv in a new cold store under the existing frozen
v3 config, two workers, one transient attempt, one permitted invalid-output repair.
500 original IDs / 479 distinct texts; 21 exact duplicates get direct-source aliases.
Keep current fallback flag semantics; do not apply the proposed sticky rule.
Deterministic fallback ranks confidence → margin → text hash → canonical ID,
persists selection before dispatch, and permits at most 47 distinct fallback texts.
No existing v2 output is reused as v3 enrichment evidence.

Use the fixed existing 500 valid checkpoint verifier predictions, without any new
verifier calls or golden evaluation. Audit of all 95 stored checkpoint verifier
requests found that the delimited records contain only original review_id and
review_text, never Jev outputs or first enrichment labels. The role uses the rubric
and independent classification. The labels are **blinded to first predictions**;
this does not imply human truth or statistical independence from a shared model.
Their file SHA256 is pinned in checkpoint-500-v3-ab-proposal.json.

Primary comparison: four core Jev answers v2 versus v3 on the same original texts,
using the identical decoder for both and excluding auxiliary-language overrides.
The shared rules and four core question definitions are identical in the two
prompt files; the prompt change adds language/context questions. This historical
matched-input prompt comparison removes the different-input confound of scaling.
It remains a historical comparison, not simultaneous randomized execution; model
stochastic variation can remain even with the same pinned version.

Secondary comparison: operational Jev-v3 output including language overrides and
final enriched v2/v3 labels. Final enrichment is **not a pure prompt-only contrast**:
v2 used .75/.15 thresholds and earlier quota/allocation behavior (including the
quota defect); v3 uses .60/0 and the corrected deterministic 10% allocation.
Report this separately rather than attribute final-label differences solely to
the Jev prompt.

For both views show topic, intent, severity exact and within ±1, and sentiment sign,
plus sentiment absolute tolerance .25. Report v2/v3 agreement and disagreement,
paired improvements/regressions, shared valid denominator, terminal failures,
and exact-text clustered uncertainty. Show both original-ID and distinct-text views.

Existing v2 baseline (disagreements out of 500, order topic / intent / severity
exact / beyond ±1 / sentiment sign): core Jev **54 / 37 / 64 / 5 / 40**;
final enrichment **54 / 34 / 60 / 5 / 37**. V3 results are not yet measured.

## Reviewed worst-case envelope

- 479 initial Jev requests, up to 479 repairs: Jev bound **$0.249835488**.
- 38 long distinct texts plus up to 47 fallback texts give at most 85 Luna
  enrichment IDs (overlap can reduce this). Batched at configured maximum 20;
  conservatively bound up to 85 singleton initial requests plus 85 repairs:
  Luna bound **$0.155406000**.
- Maximum **1,128 calls**, total **$0.405241488**. Proposed invocation cap
  **$0.406**. No verifier, group or memo calls.

Rates are the pinned project rates: Jev $0.042/M input; Luna conservative
max(input/cache-write) $0.125/M input and $0.50/M output. Input bounds use
actual canonical UTF-8 payload bytes +2,048 protocol overhead +1,024 repair bytes.
Each permitted initial/repair request is bounded, Luna at 200 output tokens per
review. Select the 85 largest singleton Luna envelopes, and sum two attempts
per allowed distinct item; no prompt-cache discount is assumed.
The runner must enforce per-call/stage limits and project reservations before
dispatch and pin config/rates/source/reference hashes. Current project spend is
$0.266722386; full envelope would yield $0.671963874, with no outstanding charges.
Observed scaling-mix estimate is about $0.0279, not a guarantee or approval cap.
Stop after the paired report; remaining analysis_10000 and all other work remain gated.

## Flag reason observability without a hash change

Final records currently store only needs_review, not explicit reason fields.
Raw Jev language choice, Noul context probability, core confidence/probabilities
and initial stage results persist in SQLite/call logs. They can be exported offline
as per-record **initial signals**, with the final boolean and fallback provenance.
This does not change labels, prompts, routing or the label hash.

An offline export is now saved at artifacts/scaling/flag-reasons.csv, with a
summary at flag-reasons-summary.json; reproduce using python -m pipeline.flag_reasons.
Initial overlapping counts: language 265, missing context 1,369, low confidence
1,242. Final flagged records with known original attribution: language 265,
non-fallback context 1,198, non-fallback low confidence 942 (overlapping).
109 final flagged fallback records also carry **fallback_judgment_unattributed**;
Luna did not return a reason schema, so it is not honest to force these into the
three initial buckets as known final causes. That category may overlap language.
The export separates cleared initial flags and marks incomplete final attribution.

Dashboard/README can display the three initial signal counts, final flag rate,
cleared flags, and the unattributed fallback category with no hash change.
Requesting new final reasons from Luna would change its enrichment schema/prompt;
that is separate work, not performed here. Do not alter or rehash model-call
evidence merely to fill unavailable reasons.
