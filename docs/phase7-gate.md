# Phase 7 measured gate — memo draft

Update: the [memo](phase7-memo-draft.md) is now owner approved; see
[approval and content hash](phase7/memo-owner-approval.json). The execution
receipt below preserves the earlier stop-at-draft state. Deployment remains a
[proposal](phase8-deployment-proposal.md), not an executed phase.

V3 is final. No golden labels informed grouping. Classifier prompt and hash are unchanged.

Classifier hash: `21e3786452ae54d189d625badf85d2d04b212b7ffab3517896a83484509ec19c`.

Cross-topic controls history: v1 had no unified issue (0); v2 3,407 rows / severity_sum 10,598; v3 4,444 / 13,877. All twelve cited recall cases now match. Changes address recall errors identified in random development spot-checks. No further tuning follows these results.

The ten fresh full review texts and matching evidence are in [the v3 spot-check](phase7-cohort-spotcheck-v3.md). The station/no-shuffle example `d9312090` remains an ambiguous fit; inferred restrictions do not prove a Premium cause.

## Production verifier agreement

Blinded Luna agreement, not human accuracy; fallback also uses Luna. Duplicate texts induce dependence. Entities excluded.

Sampled 500; terminal verifier items 0.

### overall (n=500)

- topic: 471/500 (94.2%).
- intent: 465/500 (93.0%).
- severity_exact: 453/500 (90.6%).
- severity_within_one: 499/500 (99.8%).
- sentiment_sign: 469/500 (93.8%).
- needs_review: 170/500 (34.0%).

### flagged (n=399)

- topic: 378/399 (94.7%).
- intent: 369/399 (92.5%).
- severity_exact: 361/399 (90.5%).
- severity_within_one: 398/399 (99.7%).
- sentiment_sign: 370/399 (92.7%).
- needs_review: 69/399 (17.3%).

### unflagged (n=101)

- topic: 93/101 (92.1%).
- intent: 96/101 (95.0%).
- severity_exact: 92/101 (91.1%).
- severity_within_one: 101/101 (100.0%).
- sentiment_sign: 99/101 (98.0%).
- needs_review: 101/101 (100.0%).

### fallback (n=38)

- topic: 33/38 (86.8%).
- intent: 32/38 (84.2%).
- severity_exact: 35/38 (92.1%).
- severity_within_one: 38/38 (100.0%).
- sentiment_sign: 36/38 (94.7%).
- needs_review: 22/38 (57.9%).

### no_fallback (n=462)

- topic: 438/462 (94.8%).
- intent: 433/462 (93.7%).
- severity_exact: 418/462 (90.5%).
- severity_within_one: 461/462 (99.8%).
- sentiment_sign: 433/462 (93.7%).
- needs_review: 148/462 (32.0%).

### Flag-policy comparison

Saved flag comparison: `{"pipeline_flagged": 399, "pipeline_reason_counts_overlapping": {"language_non_english": 16, "language_not_understood": 31, "low_confidence": 90, "missing_context": 368}, "pipeline_verifier_confusion": {"False/False": 101, "True/False": 330, "True/True": 69}, "verifier_flagged": 69}`.

Reason counts overlap. The frozen pipeline keeps missing-context signals through fallback; the blinded verifier makes its own judgment. This comparison does not validate either as human truth and does not authorize any threshold or flag-policy change.

## Raw group-call outputs

These calls name fixed deterministic cohorts; they do not change memberships or ranking. Owner-approved display names override model names where noted.

### group-01

- `other--unspecified`: General dissatisfaction — no stated cause.
- `cross-topic--free-tier-premium-controls`: Restrictions on song choice and playback controls. Final display: Free-tier playback controls locked behind Premium.
- `usability--ad-interruptions`: Frequent or intrusive advertisements.
- `usability--unspecified`: Usability complaints with no specific cause stated.
- `billing--premium-upgrade-mentions`: Premium subscription and upgrade complaints.
- `playback--unspecified`: Playback complaints with no specific cause stated.
- `playback--stops-skips-wont-play`: Playback stops, skips, or songs won't play.
- `usability--queue-playlist-controls`: Playlist and queue problems.
- `access--login-credentials`: Login and sign-in problems.
- `catalog--unspecified`: Catalog complaints with no specific cause stated.
- `billing--unspecified`: Billing complaints with no specific cause stated.
- `playback--buffering-connectivity`: Buffering, loading, or connectivity problems.
- `playback--crashes-freezes`: App crashes or freezes.
- `billing--price-paywalls`: Prices and paywalls.
- `downloads--download-failure`: Download problems.
- `catalog--lyrics`: Lyrics unavailable or restricted.
- `usability--interface-navigation`: Interface and navigation problems.
- `access--unspecified`: Access complaints with no specific cause stated.
- `usability--shuffle-controls`: Shuffle and repeat controls not working as expected.
- `catalog--search-results`: Search and finding music problems.
- `billing--subscription-cancellation`: Subscription cancellation and renewal complaints.
- `downloads--offline-access`: Downloaded music or podcasts unavailable offline.
- `playback--audio-quality-volume`: Bluetooth playback and audio quality problems.
- `billing--charges-refunds`: Payment, charge, and refund problems.
- `catalog--availability-selection`: Missing or removed content and limited selection.

### group-02

- `catalog--discovery-recommendations`: Unwanted or inconvenient recommendations and discovery.
- `downloads--unspecified`: Download problems — unspecified.
- `playback--background-resources`: Battery, memory, or background resource drain.
- `support--unspecified`: Support complaints — unspecified.
- `access--account-security`: Hacked or compromised accounts.
- `access--signup-registration`: Sign-up and registration problems.
- `downloads--missing-downloads`: Downloaded songs or files disappearing or missing.
- `support--resolution-quality`: Poor support and unresolved issues.
- `support--contact-response`: Problems contacting support or getting a response.
- `access--account-restrictions`: Accounts blocked, disabled, or locked.

## Propagated baseline top ten

1. General dissatisfaction — no stated cause (`other--unspecified`): 36225 members; severity_sum/priority 58636.
2. Free-tier playback controls locked behind Premium (`cross-topic--free-tier-premium-controls`): 4444 members; severity_sum/priority 13877.
3. Frequent or intrusive advertisements (`usability--ad-interruptions`): 6037 members; severity_sum/priority 12965.
4. Usability complaints with no specific cause stated (`usability--unspecified`): 4228 members; severity_sum/priority 10500.
5. Premium subscription and upgrade complaints (`billing--premium-upgrade-mentions`): 3152 members; severity_sum/priority 8784.
6. Playback complaints with no specific cause stated (`playback--unspecified`): 2727 members; severity_sum/priority 8688.
7. Playback stops, skips, or songs won't play (`playback--stops-skips-wont-play`): 1674 members; severity_sum/priority 5590.
8. Playlist and queue problems (`usability--queue-playlist-controls`): 1582 members; severity_sum/priority 4705.
9. Login and sign-in problems (`access--login-credentials`): 1136 members; severity_sum/priority 4466.
10. Catalog complaints with no specific cause stated (`catalog--unspecified`): 1126 members; severity_sum/priority 3115.

## Random-prefix-only top ten

1. General dissatisfaction — no stated cause (`other--unspecified`): 12002 members; severity_sum/priority 20564.
2. Free-tier playback controls locked behind Premium (`cross-topic--free-tier-premium-controls`): 4440 members; severity_sum/priority 13865.
3. Usability complaints with no specific cause stated (`usability--unspecified`): 3784 members; severity_sum/priority 9609.
4. Frequent or intrusive advertisements (`usability--ad-interruptions`): 4088 members; severity_sum/priority 9071.
5. Premium subscription and upgrade complaints (`billing--premium-upgrade-mentions`): 3123 members; severity_sum/priority 8705.
6. Playback complaints with no specific cause stated (`playback--unspecified`): 2558 members; severity_sum/priority 8189.
7. Playback stops, skips, or songs won't play (`playback--stops-skips-wont-play`): 1651 members; severity_sum/priority 5513.
8. Playlist and queue problems (`usability--queue-playlist-controls`): 1582 members; severity_sum/priority 4705.
9. Login and sign-in problems (`access--login-credentials`): 1021 members; severity_sum/priority 4008.
10. Catalog complaints with no specific cause stated (`catalog--unspecified`): 1118 members; severity_sum/priority 3093.

## Checker and measured spend

Validation: 220 tests passed; Ruff checks passed. Tests make no paid calls.

Call counts by stage: `{"group-01": 1, "group-02": 1, "memo": 1, "verify": 11}`.

Call outcomes: `{"succeeded": 14}`.

Verification used ten initial batches and one singleton repair; no verifier items were terminal. The rendered memo clarifies the model phrase "unclassified complaint" as "complaint with an unspecified cause"; the original response is preserved in phase7/memo-draft.json.

Tracked gzip hash comparisons: `{"grading\\calls.jsonl.gz": true, "grading\\records.jsonl.gz": true}`.

Working submission: artifacts/phase7/grading-check; tracked grading/*.gz were not rewritten.

Checker flags: `{"invalid_usage": 20, "unfinished_classification": 1}`.

The partial-scope unfinished_classification flag counts unclassified/quarantined nonempty rows; it is the declared scope limitation. Twenty invalid_usage fields belong to ten historical connection failures with unknown charged token usage. Nulls are retained honestly. Any additional flag must be investigated rather than treated as expected.

Invocation status: memo_draft_awaiting_owner_review; actual spend $0.025751725 against the shared $1.58 cap.

Ledger totals (nanodollars): `{"reserved_nanodollars": 0, "spent_nanodollars": 5629964013}`.

[Owner-approved memo](phase7-memo-draft.md). Baseline evidence: [claims.csv](phase7/claims.csv); separately labeled secondary figures: [secondary claims](phase7/secondary-claims.csv). The deployment phase has not started.
