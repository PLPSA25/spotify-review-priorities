# Proposed group → rank → claims → memo gate (not run)

Keep the frozen classifier hash and all classifications unchanged. No new Jev calls,
fallback, golden evaluation, calibration or provider prompt caching is proposed.

1. **Group:** deterministic stable `issue-<topic>` IDs for completed complaints and
   cancellations, one membership per ID, including aliases and forced golden IDs.
   All **70,239** eligible full-coverage IDs must be assigned. One Luna group call
   names the at-most-eight issues from a bounded evidence pack, without changing
   memberships, primary labels or numeric aggregates. Exclude golden IDs **and exact
   golden texts** from discovery/naming examples; do not read human labels.
2. **Rank:** code-only baseline over **all completed rows**, using severity_sum,
   descending then ascending issue ID; half-up six-decimal means. Preserve rerank.
   Separately compute the **first 100,000 permutation IDs only**, exclude golden
   force-additions outside that prefix, keep one contribution per original sampled ID
   (including sampled duplicates), same issue IDs and arithmetic. Disclose terminal
   omissions and denominator. This secondary view is not the propagated population.
3. **Claims:** code generates baseline claims matching the grader recomputation.
   A separate namespaced `sample_claims.csv` and deterministic local validator support
   the random-prefix comparison. Do not insert sample values as baseline claims:
   the supplied checker compares claims.csv only against baseline membership.
   The memo/appendix identifies each number's scope and its claim file/ID.
4. **Memo:** one Luna call from saved baseline/sample aggregates and at most 16
   exact evidence quotes (up to two per issue), never the full corpus. Bound text
   lengths, forbid invented numbers, verify all cited claim/review IDs; render
   numbers in code. Include alternatives, partial coverage, duplicate propagation
   bias, terminal/known accuracy limitations, cancellation intent versus actual churn,
   unavailable failed-call usage, correlated verifier/fallback and checkpoint provenance.
5. **Verification provenance:** import the existing **11 succeeded blinded v3 verifier
   calls / 500 IDs** and its report into the grading call view, retaining original
   run/hash/phase/model information. No paid repeat and no claim this was a newly
   drawn production verifier sample. Recheck foreign/duplicate IDs and golden
   exclusion. The 20 owner verdicts remain independent but selected disagreement
   judgments, not a random human-accuracy sample.
6. Regenerate exports, run local claim/ranking tests and the full supplied checker.
   Remove the three pending-business flags; retain/explain deliberate partial
   classification and genuinely unavailable usage. Packaging/compression awaits
   separate approval; deployment is a later phase.

## Proposed paid envelope

Only **two root calls**: Luna group and Luna memo, standard tier, effort none,
existing configured exact model. Log actual returned model/tier/usage and inputs.
At most **four total attempts per role**, **eight calls maximum**, covering permitted
repair and connection retries together. No implicit extra verifier or dashboard calls.

Before dispatch, enforce an input bound of **24,000 tokens per attempt**, including
schema, instructions, repair suffix and protocol overhead, using the existing
conservative UTF-8-byte bound. Reject oversized payloads before reservation; never
silently truncate evidence. Group output cap **512**, memo output cap **1,200**.
This guard is part of the proposed implementation; it has not been run or measured.

Pinned planning rates: reserve Luna input at max(normal, cache-write) **$0.125/M**,
output **$0.50/M**, no prompt-cache savings. Worst case:

`4 × [(24000 × 0.125 + 512 × 0.50) + (24000 × 0.125 + 1200 × 0.50)] / 1e6`

= **$0.027424 maximum**, assuming every allowed attempt consumes its full bound.
Proposed separately approved invocation cap: **$0.03**, shared project cap stays $10.
Two full-envelope root calls cost at most **$0.006856**; this is a bound, not expected
measured usage. Project maximum at the $0.03 cap: **$5.634212288 / $10**.
No additional Jev spending. Provider balances must be rechecked before dispatch;
the earlier owner-reported $9.82 OpenAI/$10.41 TypeSafe are not current balances.

Time estimate: **2–5 minutes** for offline aggregation/validation plus **tens of
seconds** for typical model responses, unmeasured at this scope; allow extra time
for retries and checker/export I/O. Real pilot references only: group 2.859 s,
successful memo 5.218 s, two failed memo attempts 5.312/2.875 s. These are not a
production timing guarantee. Group/memo inputs stay bounded as corpus size grows.

Wait for owner approval before any paid calls. This proposal does not apply
compression, run grouping/ranking or generate a memo.
