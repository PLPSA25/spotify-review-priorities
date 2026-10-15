# Dashboard copy and layout review

The page now starts with the recommendation and a plain-language reading guide. The methodology, glossary, stored outputs and hashes are collapsed at the bottom. The approved memo is unchanged; its claim links are rendered as muted superscripts.

Verification completed on 2026-10-15: production build, TypeScript, all six contract tests and all seven browser tests passed. Browser checks cover both rankings, search, claims downloads, review links, mobile overflow, keyboard controls, unavailable data, HTML injection safety, human-check figures and methodology disclosure. The final fixes additionally verify a single memo link, all five severity definitions verbatim against `docs/labels.md`, every methodology subsection collapsed on load, and the readable verifier split at 390px width. Deployment-source and browser-bundle secret scan: 20 source files, 25 browser assets, zero findings. The full Git-history scan remains part of final submission work.

SHA-256 comparisons confirmed no changes to either snapshot, the local preview snapshot, both ranking files, both claims files, the approved memo, configuration or grading archives. No paid calls or deployment were made.

The human-check figures were copied from the existing aggregate evaluation report only: topic 37/50 (74%), intent 42/50 (84%), severity exact 36/50 (72%), severity within one level 48/50 (96%), sentiment sign 41/50 (82%). No human-label CSV was read and no evaluation was rerun. The report's hash is recorded in `web/lib/human-check.json` and the methodology disclosure.

The five-level severity legend uses the exact wording from `docs/labels.md`, including the level-5 qualification. The group-call disclosure states that display names were finalized by the owner and that these are the model's proposed names. The original model memo stays inside a collapsed subsection. The final approved fixes are included in this review.

Local preview: [http://127.0.0.1:3002](http://127.0.0.1:3002). Screenshots below are from the rebuilt app, using the unchanged local snapshot.

## Answer

![Answer card](C:/dev/Spotify/artifacts/dashboard/copy-revision/01-answer.png)

## How to read this page

![Reading guide](C:/dev/Spotify/artifacts/dashboard/copy-revision/02-how-to-read.png)

## Partial scope

![Partial scope](C:/dev/Spotify/artifacts/dashboard/copy-revision/03-scope.png)

## Key numbers

![Key numbers](C:/dev/Spotify/artifacts/dashboard/copy-revision/04-key-numbers.png)

## Controls versus ads

![Controls versus ads](C:/dev/Spotify/artifacts/dashboard/copy-revision/05-controls-vs-ads.png)

## Ranking

![Ranking](C:/dev/Spotify/artifacts/dashboard/copy-revision/06-ranking.png)

## Example reviews

![Example reviews](C:/dev/Spotify/artifacts/dashboard/copy-revision/07-examples.png)

## Review mix

![Review mix](C:/dev/Spotify/artifacts/dashboard/copy-revision/08-review-mix.png)

## Human-check flags

![Human-check flags](C:/dev/Spotify/artifacts/dashboard/copy-revision/09-human-flags.png)

## Label quality

![Label quality](C:/dev/Spotify/artifacts/dashboard/copy-revision/10-quality.png)

## Approved memo

![Approved memo](C:/dev/Spotify/artifacts/dashboard/copy-revision/11-memo.png)

## Methodology, collapsed by default

![Collapsed methodology](C:/dev/Spotify/artifacts/dashboard/copy-revision/12-methodology.png)

## Methodology, expanded

![Expanded methodology](C:/dev/Spotify/artifacts/dashboard/copy-revision/13-methodology-expanded.png)

## Mobile layout

![Mobile layout](C:/dev/Spotify/artifacts/dashboard/copy-revision/dashboard-mobile.png)
