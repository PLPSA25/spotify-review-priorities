# Proposed issue taxonomy — offline preview only

No grading membership/ranking/claims file was populated. These are proposed lexical cohorts, not newly validated model defect labels. Classifier prompts and hash are unchanged.

Source: all 237,722 completed exported records; 70,239 complaint/cancellation IDs. Proposed rule hash: `f75aba57f835d62501f3f69b0e4d302717d16ac13d6212a7159efee07c2419c2`.

## Formation and model role

The previous option creates eight topic-only issues. Recommended refinement creates **34 nonempty topic × sub-issue cohorts**, using immutable primary topics plus explicit text regexes. Choose the earliest matching phrase within the primary topic; rule order breaks same-position ties; unmatched texts remain `unspecified`. Each completed complaint/cancellation gets exactly one stable issue ID. No stars or other metadata are used. All original IDs, including cache aliases, count separately.

Rules were fixed independently of golden answers; no human golden labels were read. Golden exact texts are excluded from example selection. Primary labels are not corrected by this grouping. English lexical rules miss paraphrases/non-English phrasing and can mistake feature mentions for defect evidence; the cohort names must not imply validated causal root causes. `premium-upgrade-mentions` is deliberately a mention cohort, not proof of entitlement failure.

Two proposed Luna calls carry `role="group"`, with at most 25 fixed issue IDs and two distinct-text examples per issue (at most 50 review IDs per call). They name/assess groups; they cannot silently change membership, frozen classifications or computed numbers. Substantive membership changes would return to a gate. Code performs the grouping/ranking; Luna supplies bounded group naming/assessment. Both calls are new production group evidence.

## Top ten finer issues by severity_sum

Priority is exactly severity_sum (complaint_count × mean severity), then ascending issue ID. The example IDs below are complete original IDs, deterministic and not selected by severity.

1. **other--unspecified** — size **36,229**, severity_sum **58,642**; examples `d2878e82-4c9d-4632-9173-c55b12aad98a`, `b394602a-0c0b-47e1-975c-57378ace5804`.
2. **usability--ad-interruptions** — size **6,355**, severity_sum **13,924**; examples `f2e4bd01-74ca-4ac1-99e4-3d70aa8ea2a8`, `33f2ee17-cd1a-405c-8d82-6e79fb83e16b`.
3. **billing--premium-upgrade-mentions** — size **4,465**, severity_sum **12,800**; examples `16aee738-325c-447e-b33b-a2a2beb51d82`, `8dae6d1b-9126-4944-afdc-742e33dc48b1`.
4. **usability--unspecified** — size **4,765**, severity_sum **12,177**; examples `2b3a32b6-1a75-43b8-baa6-f0d97869aee3`, `9bd5ba25-d9ef-40c4-9af1-4172bd4b97f6`.
5. **playback--unspecified** — size **3,018**, severity_sum **9,678**; examples `6e73e650-29c2-4592-ac20-2bc2c0c8dfa4`, `7f1c87c6-0d1c-4300-9124-61efb93bb2ee`.
6. **playback--stops-skips-wont-play** — size **1,952**, severity_sum **6,533**; examples `47288746-0440-4af3-a56e-5af24930b811`, `6ef53494-b985-4b46-ae36-bb7f28d7d8a7`.
7. **usability--queue-playlist-controls** — size **2,061**, severity_sum **6,199**; examples `c03e8f41-83c0-4bc1-bcc4-7d0a99a99c70`, `a8047c81-47dc-4b61-9667-6eebaf81aa7b`.
8. **access--login-credentials** — size **1,154**, severity_sum **4,537**; examples `f3c1f73f-e1e1-4578-97e4-e2d9ed97b2ec`, `8b41ae1e-b06a-45ae-9ddc-cdc715bc6510`.
9. **catalog--unspecified** — size **1,151**, severity_sum **3,197**; examples `bf13f074-6333-4fc9-9669-2d8028041772`, `02be6031-bf6e-4db1-a7cd-f3d86b926401`.
10. **billing--price-paywalls** — size **1,103**, severity_sum **2,914**; examples `69e7336b-502a-4ad4-840b-9ddfe44a16bd`, `cd6077ad-ef68-492c-946f-f0dc981f61f1`.

The leading `other--unspecified` cohort remains unresolved rather than being renamed as an actionable defect. Ads is the highest-ranked specifically identified cohort. The memo must show the residual bucket and compare the random-prefix-only ranking before recommending an intervention; this preview alone is not an intervention-effect estimate.

## Full proposed taxonomy

- **access:** account-security, login-credentials, signup-registration, account-restrictions, unspecified.
- **usability:** ad-interruptions, shuffle-controls, queue-playlist-controls, interface-navigation, unspecified.
- **playback:** crashes-freezes, buffering-connectivity, audio-quality-volume, background-resources, stops-skips-wont-play, unspecified.
- **downloads:** missing-downloads, offline-access, download-failure, unspecified.
- **catalog:** lyrics, discovery-recommendations, search-results, availability-selection, unspecified.
- **billing:** charges-refunds, premium-upgrade-mentions, price-paywalls, subscription-cancellation, unspecified.
- **support:** contact-response, resolution-quality, unspecified.
- **other:** unspecified.

## Eight-topic baseline, for comparison

1. **other** — size 36,229, severity_sum 58,642; examples `d2878e82-4c9d-4632-9173-c55b12aad98a`, `b394602a-0c0b-47e1-975c-57378ace5804`.
2. **usability** — size 14,917, severity_sum 37,057; examples `f2e4bd01-74ca-4ac1-99e4-3d70aa8ea2a8`, `2b3a32b6-1a75-43b8-baa6-f0d97869aee3`.
3. **playback** — size 6,588, severity_sum 21,570; examples `47288746-0440-4af3-a56e-5af24930b811`, `6ef53494-b985-4b46-ae36-bb7f28d7d8a7`.
4. **billing** — size 7,229, severity_sum 20,109; examples `16aee738-325c-447e-b33b-a2a2beb51d82`, `8dae6d1b-9126-4944-afdc-742e33dc48b1`.
5. **catalog** — size 2,558, severity_sum 7,250; examples `db8bd722-9fbd-418b-9882-59af2e43f250`, `bf13f074-6333-4fc9-9669-2d8028041772`.
6. **access** — size 1,650, severity_sum 6,486; examples `f3c1f73f-e1e1-4578-97e4-e2d9ed97b2ec`, `8b41ae1e-b06a-45ae-9ddc-cdc715bc6510`.
7. **downloads** — size 962, severity_sum 3,171; examples `1de11e7e-7bc0-41d2-b313-83db8b8ba47f`, `8932cff1-f33b-4e6c-a7e4-3988e2e0d91c`.
8. **support** — size 106, severity_sum 243; examples `6529bdf5-0936-4584-9a2e-f2b0d3278ab9`, `2ab8b76f-c111-4c07-9b79-793fbc71a84a`.

## Full finer preview

- `other--unspecified`: size 36,229; severity_sum 58,642.
- `usability--ad-interruptions`: size 6,355; severity_sum 13,924.
- `billing--premium-upgrade-mentions`: size 4,465; severity_sum 12,800.
- `usability--unspecified`: size 4,765; severity_sum 12,177.
- `playback--unspecified`: size 3,018; severity_sum 9,678.
- `playback--stops-skips-wont-play`: size 1,952; severity_sum 6,533.
- `usability--queue-playlist-controls`: size 2,061; severity_sum 6,199.
- `access--login-credentials`: size 1,154; severity_sum 4,537.
- `catalog--unspecified`: size 1,151; severity_sum 3,197.
- `billing--price-paywalls`: size 1,103; severity_sum 2,914.
- `billing--unspecified`: size 1,137; severity_sum 2,821.
- `usability--shuffle-controls`: size 943; severity_sum 2,722.
- `playback--crashes-freezes`: size 622; severity_sum 2,228.
- `playback--buffering-connectivity`: size 679; severity_sum 2,222.
- `downloads--download-failure`: size 642; severity_sum 2,108.
- `usability--interface-navigation`: size 793; severity_sum 2,035.
- `catalog--lyrics`: size 686; severity_sum 1,975.
- `access--unspecified`: size 426; severity_sum 1,653.
- `catalog--search-results`: size 324; severity_sum 998.
- `billing--subscription-cancellation`: size 334; severity_sum 974.
- `billing--charges-refunds`: size 190; severity_sum 600.
- `downloads--offline-access`: size 186; severity_sum 599.
- `playback--audio-quality-volume`: size 207; severity_sum 576.
- `catalog--availability-selection`: size 198; severity_sum 574.
- `catalog--discovery-recommendations`: size 199; severity_sum 506.
- `downloads--unspecified`: size 106; severity_sum 355.
- `playback--background-resources`: size 110; severity_sum 333.
- `support--unspecified`: size 75; severity_sum 153.
- `access--account-security`: size 31; severity_sum 149.
- `access--signup-registration`: size 36; severity_sum 136.
- `downloads--missing-downloads`: size 28; severity_sum 109.
- `support--resolution-quality`: size 20; severity_sum 56.
- `support--contact-response`: size 11; severity_sum 34.
- `access--account-restrictions`: size 3; severity_sum 11.
