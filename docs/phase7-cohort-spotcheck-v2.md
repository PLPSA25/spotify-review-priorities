# Phase 7 cohort spot-check v2 — review before all paid calls

**No Phase 7 API calls have been made.** Verifier, group and memo calls are held until the owner reviews this file. These are proposed memberships only; grading exports and classifications are unchanged.

## Cross-topic grouping is permitted

Contract `data/GRADING_CONTRACT.md:94–95`: "The required baseline uses completed `complaint` and `cancellation` records. Each must belong to at least one issue." and "Normally use one issue per complaint." No requirement confines an issue to a topic. The checker at `data/check_submission.py:255–280` validates original IDs, complaint intent and unique membership; it does not compare an issue with the primary topic. `allow_multi_issue:false` is preserved: every eligible ID belongs to exactly one issue.

## Proposed definition and precedence

**Free-tier playback controls locked behind Premium** (`cross-topic--free-tier-premium-controls`) takes precedence over all within-topic cohorts, including `other`. It requires a control-family match plus restriction/pressure evidence; Premium alone cannot match. Primary topic, severity, intent, label_config and all labels stay unchanged. Grouping-rule hash: `c6fba2ae730a765407fb06d35ac2a1f39756a6f6c9d713b0d462a295dbe873ea`.

Control families: shuffle/unshuffle; play-in-order or song selection; previous/back; repeat/loop; skip/forward (not skip ads); seek/rewind/specific or favorite song parts. The owner-cited generic Price #2/#3 descriptions additionally match the explicitly named `basic-player-control-paraphrase` rule, together with payment/upgrade restriction—not a Premium keyword alone.

**Evidence distinction:** explicit paywall/Premium linkage is separated from free-tier restriction and inferred update/forced-shuffle/multiple-controls-denied paths. Queue #1–#3 do not explicitly establish Premium gating; including those owner-selected examples therefore entails an inference. Those rows remain visibly marked inferred; the requested title is a provisional theme, not proof that every member is a free user or was paywalled. Paid-customer statements exclude inferred paths. Review the evidence tiers below before accepting this attribution.

Non-stop/non stop/non–stop/nonstop and without-stopping continuity claims no longer count as stoppage failures. Exclusion applies to the protected occurrence only, so a later actual "music stops" still counts.

## Measured offline redistribution

New cross-topic issue: **3,407 IDs**, severity_sum **10,598**. Total eligible IDs and severity_sum remain unchanged. Proposed issue count: 34 → 35.

- `access`: **15** reviews; severity_sum **60**.
- `usability`: **1,387** reviews; severity_sum **4,300**.
- `playback`: **345** reviews; severity_sum **1,168**.
- `downloads`: **18** reviews; severity_sum **61**.
- `catalog`: **43** reviews; severity_sum **136**.
- `billing`: **1,596** reviews; severity_sum **4,866**.
- `support`: **1** reviews; severity_sum **3**.
- `other`: **2** reviews; severity_sum **4**.

Evidence tiers:

- `free_tier_control_restriction`: **188** IDs; severity_sum **580**.
- `inferred_update_control_restriction`: **1,184** IDs; severity_sum **3,794**.
- `explicit_paywall_or_premium_link`: **1,735** IDs; severity_sum **5,302**.
- `inferred_multiple_controls_denied`: **217** IDs; severity_sum **680**.
- `inferred_forced_shuffle`: **83** IDs; severity_sum **242**.

Continuity-protection correction changes 10 original within-topic assignments before cross-theme precedence. The reported false positive `09d5682f` is now `playback--unspecified`.

## Top ten: current v1 ranking

1. `other--unspecified` — size **36,229**, severity_sum **58,642**.
2. `usability--ad-interruptions` — size **6,355**, severity_sum **13,924**.
3. `billing--premium-upgrade-mentions` — size **4,465**, severity_sum **12,800**.
4. `usability--unspecified` — size **4,765**, severity_sum **12,177**.
5. `playback--unspecified` — size **3,018**, severity_sum **9,678**.
6. `playback--stops-skips-wont-play` — size **1,952**, severity_sum **6,533**.
7. `usability--queue-playlist-controls` — size **2,061**, severity_sum **6,199**.
8. `access--login-credentials` — size **1,154**, severity_sum **4,537**.
9. `catalog--unspecified` — size **1,151**, severity_sum **3,197**.
10. `billing--price-paywalls` — size **1,103**, severity_sum **2,914**.

## Top ten: proposed v2 ranking

1. `other--unspecified` — size **36,227**, severity_sum **58,638**.
2. `usability--ad-interruptions` — size **6,125**, severity_sum **13,230**.
3. `usability--unspecified` — size **4,424**, severity_sum **11,106**.
4. `cross-topic--free-tier-premium-controls` — size **3,407**, severity_sum **10,598**.
5. `playback--unspecified` — size **2,875**, severity_sum **9,194**.
6. `billing--premium-upgrade-mentions` — size **3,225**, severity_sum **9,005**.
7. `playback--stops-skips-wont-play` — size **1,771**, severity_sum **5,925**.
8. `usability--queue-playlist-controls` — size **1,731**, severity_sum **5,167**.
9. `access--login-credentials` — size **1,145**, severity_sum **4,502**.
10. `catalog--unspecified` — size **1,137**, severity_sum **3,151**.

## Random-prefix-only v2 comparison

Only completed original IDs within the first 100,000 permutation IDs contribute here; forced golden additions outside the prefix and propagated out-of-prefix aliases are excluded.

1. `other--unspecified` — size **12,004**, severity_sum **20,566**.
2. `cross-topic--free-tier-premium-controls` — size **3,403**, severity_sum **10,586**.
3. `usability--unspecified` — size **3,980**, severity_sum **10,215**.
4. `usability--ad-interruptions` — size **4,176**, severity_sum **9,336**.
5. `billing--premium-upgrade-mentions` — size **3,196**, severity_sum **8,926**.
6. `playback--unspecified` — size **2,706**, severity_sum **8,695**.
7. `playback--stops-skips-wont-play` — size **1,748**, severity_sum **5,848**.
8. `usability--queue-playlist-controls` — size **1,731**, severity_sum **5,167**.
9. `access--login-credentials` — size **1,030**, severity_sum **4,044**.
10. `catalog--unspecified` — size **1,129**, severity_sum **3,129**.

## Check of the owner-cited examples

- `361c0b33` (billing--premium-upgrade-mentions #3) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.
- `22a864da` (billing--premium-upgrade-mentions #4) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.
- `5544a27c` (billing--premium-upgrade-mentions #5) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.
- `40cd0c58` (usability--queue-playlist-controls #1) → `cross-topic--free-tier-premium-controls`; evidence `inferred_forced_shuffle`.
- `9a2f9235` (usability--queue-playlist-controls #2) → `cross-topic--free-tier-premium-controls`; evidence `inferred_update_control_restriction`.
- `866c3d04` (usability--queue-playlist-controls #3) → `cross-topic--free-tier-premium-controls`; evidence `inferred_forced_shuffle`.
- `4c1e568c` (usability--queue-playlist-controls #5) → `cross-topic--free-tier-premium-controls`; evidence `inferred_update_control_restriction`.
- `2827a620` (billing--price-paywalls #2) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.
- `498f361e` (billing--price-paywalls #3) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.
- `e4c5f61c` (billing--price-paywalls #5) → `cross-topic--free-tier-premium-controls`; evidence `explicit_paywall_or_premium_link`.

## New issue: ten random members

Sampling is uniform over member original IDs via SHA-256(seed + cohort + ID); seed `spotify-phase7-cohort-spotcheck-v2`. Golden exact texts are excluded from examples. Repeated exact texts remain eligible to preserve row weighting. This is qualitative review, not an accuracy estimate.

- ID `e2e041de` (full `e2e041de-a2c9-4c9d-9008-5781e5a626c9`), frozen topic `usability`.
  Evidence tier: **inferred_forced_shuffle**; controls: shuffle.
  Control matches: `shuffle`.
  Restriction/pressure match: `Always shuffle`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.

```text
I HATE the new version 1.Ads 2.Always shuffle play 3.It's a lot different now 4.I just hate the new version
```

- ID `011a515f` (full `011a515f-375c-4b84-9e15-325a1618aa25`), frozen topic `billing`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: seek-rewind-parts, shuffle, skip-forward.
  Control matches: `forward`, `rewind`, `shuffle`.
  Restriction/pressure match: `if you do not buy premium`.
  Control rule `seek-rewind-parts`: `\bseek\w*|\brewind\w*|\b(?:specific|favourite|favorite)\s+parts?\s+(?:of|in)\s+(?:(?:a|the|any)\s+)?(?:song|track)\b|\b(?:progress|seek)\s+bar\b|\bfast[ -]?forward\w*`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.
  Control rule `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`.

```text
worst app to listen to music after the update, you cant forward/rewind songs, cant turn off shuffle if you do not buy premium. Ads were more than enough for them to earn money, like crying so much for users to buy premium version. uninstalling the app.
```

- ID `0c96c38e` (full `0c96c38e-457f-46a1-b505-0b17df1911f9`), frozen topic `usability`.
  Evidence tier: **inferred_update_control_restriction**; controls: play-order-selection.
  Control matches: `in order`.
  Restriction/pressure match: `can't`.
  Control rule `play-order-selection`: `\bin\s+(?:(?:the|my|any|a|an|desired|specific)\s+)?order\b(?!\s+to\b)|\border\s+(?:i|we|you|they)\b|\b(?:play|playing|choose|select)\s+(?:any|my|a|the|specific)\s+(?:own\s+)?(?:song|track)\b`.

```text
I been using Spotify for 3 years now I was having fun i was able get songs not available in other apps and I made a Play list for me but now this new feature is not letting me play songs in order or after some songs we then we can't even choose song's anymore we need wait one day for it so disappointing
```

- ID `eb690e36` (full `eb690e36-d499-4e1c-9780-7e17a1619da4`), frozen topic `usability`.
  Evidence tier: **inferred_update_control_restriction**; controls: play-order-selection, shuffle.
  Control matches: `play a song`, `shuffle`.
  Restriction/pressure match: `can't`.
  Control rule `play-order-selection`: `\bin\s+(?:(?:the|my|any|a|an|desired|specific)\s+)?order\b(?!\s+to\b)|\border\s+(?:i|we|you|they)\b|\b(?:play|playing|choose|select)\s+(?:any|my|a|the|specific)\s+(?:own\s+)?(?:song|track)\b`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.

```text
This aap was working nicely a few days ago but now it is giving me worst experience of my life with any music aap . Like 1.if you play a song then you can only paly next song of the playlist you can't play last song cause there's no option for that 2.if you play any playlist it can only play in shuffle you cannot play it in normal way 3.you cannot add any songs form playlist to queue like what .... Please fix those problems.Spotify has been my favourite aap i don't want to leave it. Please .....
```

- ID `de4571ba` (full `de4571ba-821b-4f07-b4da-5766658c5702`), frozen topic `billing`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: previous-back, shuffle.
  Control matches: `Shuffle`, `previous`.
  Restriction/pressure match: `features are available only in Premium`.
  Control rule `previous-back`: `\bprev(?:ious)?\b|\b(?:go|going|switch|swith|skip|song|track)\b.{0,18}\bback\b|\bback\s+(?:button|song|track)\b`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.

```text
I used to Love this App but not anymore because now the most basic features are available only in Premium. Like Seriously!!!. From Shuffle to Organising our own listening order ie. Queue and most importantly we can't listen to the previous song bor can we go to a particular part of a song. I feel that All these new update will most likely make Spotify the least used Music App and all this just to make a Profit. It's really disappointing how much Spotify has changed over the years
```

- ID `9de4d641` (full `9de4d641-234c-4902-a83a-f9faa8f90c0a`), frozen topic `usability`.
  Evidence tier: **inferred_forced_shuffle**; controls: shuffle.
  Control matches: `shuffle`.
  Restriction/pressure match: `only on shuffle`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.

```text
The recent update makes you listen only on shuffle. Well, my choices are not important I guess. Thank you very much, I am not using this app again.
```

- ID `1387ca86` (full `1387ca86-7643-4342-a0ea-7d4697b3f631`), frozen topic `billing`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: previous-back, skip-forward.
  Control matches: `go back`, `skips`.
  Restriction/pressure match: `premium locked features. Only`.
  Control rule `previous-back`: `\bprev(?:ious)?\b|\b(?:go|going|switch|swith|skip|song|track)\b.{0,18}\bback\b|\bback\s+(?:button|song|track)\b`.
  Control rule `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`.

```text
While I love Spotify for giving me many recommendations, your app literally sucks now. You're losing users with all of the premium locked features. Only 6 skips an hour, can't go back, can't pick time of song, can't pick individual songs. Now you can only play the same song ONCE A DAY?? Lyrics are premium now??? That's fed up. The only things that should be premium are downloading, offline, and skips. Maybe raise to like 10 skips an hour. Jeez, you guys are so money hungry. Do better.
```

- ID `55b1de63` (full `55b1de63-9cc0-4b8a-afe1-29567f362d2b`), frozen topic `billing`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: repeat-loop, skip-forward.
  Control matches: `forward`, `repeat`.
  Restriction/pressure match: `have to buy premium`.
  Control rule `repeat-loop`: `\brepeat\w*|\bloop\w*`.
  Control rule `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`.

```text
Now with the update we cant repeat ..and simply cant forward a part of song or repeat it...for that we have to buy premium.Seriously....thinking of uninstalling it ...before this update i was very satisfied with app...but now its disappointing me..
```

- ID `4b3f810a` (full `4b3f810a-6884-41b3-9812-5181363a2998`), frozen topic `billing`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: skip-forward.
  Control matches: `skipping`.
  Restriction/pressure match: `features like replaying songs, skipping them to premium`.
  Control rule `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`.

```text
I am not one to usually put bad reviews but spotify turning basic features like replaying songs, skipping them to premium is next level bad like please just let the app be like it was, tjis unacceptable!
```

- ID `a48afb08` (full `a48afb08-2384-4ed0-8f36-268aad4c8f63`), frozen topic `usability`.
  Evidence tier: **explicit_paywall_or_premium_link**; controls: shuffle, skip-forward.
  Control matches: `shuffled`, `skips`.
  Restriction/pressure match: `unless it's a 'for you' playlist. I subscribe to premium`.
  Control rule `shuffle`: `\b(?:un)?shuffl\w*`.
  Control rule `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`.

```text
The ads are incredibly annoying. You only get 6 skips per hour, and songs are always shuffled unless it's a 'for you' playlist. I subscribe to premium every month, but for the 200tk I pay, there aren't many great perks. They either need to lower the price or enhance the benefits of Spotify Premium.
```


## Cohorts that lost members: five random remaining members each

These samples come from each **remaining** cohort, not its transferred rows, so the owner can assess what is left. Transfers and residual sizes are shown first. If fewer than five eligible remaining examples exist, all are shown rather than fabricated.

### billing--premium-upgrade-mentions

Moved **1,240** IDs / severity_sum **3,795** to the new issue. Remaining **3,225** IDs.

- ID `aee1d7b5` (full `aee1d7b5-4f98-46bf-928f-dcd53182c8dd`), frozen topic `billing`.
  Remaining-cohort rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`.
  Match: `premium`.

```text
Greedy asf, begging to buy premium
```

- ID `d6c873fc` (full `d6c873fc-367a-4832-85ab-bd7ac327a4c7`), frozen topic `billing`.
  Remaining-cohort rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`.
  Match: `Premium`.

```text
Spotify Free is Terrible and un-usable! No complaints about the Premium.
```

- ID `4f959b66` (full `4f959b66-5645-4c74-a7b4-78792a9f7d7b`), frozen topic `billing`.
  Remaining-cohort rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`.
  Match: `premium`.

```text
Come on! You can't just cut out the lyrics for those who do not buy premium. This is worst.
```

- ID `00f233c2` (full `00f233c2-8c24-4230-b264-6da2ca0ebbc2`), frozen topic `billing`.
  Remaining-cohort rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`.
  Match: `premium`.

```text
the new update is just bad tbh. everything has become premium now
```

- ID `f8ac4df8` (full `f8ac4df8-5294-4c4d-b051-1cd1fccf3dd6`), frozen topic `billing`.
  Remaining-cohort rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`.
  Match: `premium`.

```text
Far too many ads. Theres nothing that makes spotify premium better than YouTube premium. YouTube is cheaper, you can play in the background, you get the videos you want to watch ad free as well. I think spotify would be better if spotify had the mobile edition the same as the iPad or PC edition where you can skip as many times as you like and play songs and playlists not just shuffled.
```

### usability--shuffle-controls

Moved **435** IDs / severity_sum **1,342** to the new issue. Remaining **508** IDs.

- ID `708979fd` (full `708979fd-813a-4785-b0b7-7cfa04fa44d8`), frozen topic `usability`.
  Remaining-cohort rule: `\bshuffle\w*|\brepeat\b`.
  Match: `SHUFFLE`.

```text
This app makes me mad, I can't even listen to music on my phone when there is SHUFFLE. Like I want to pick my song?? I don't want it to be shuffled up on a song I don't want to listen? Can't this app get any better? 😐
```

- ID `be94b3ba` (full `be94b3ba-bd71-4288-b705-e24316aaf978`), frozen topic `usability`.
  Remaining-cohort rule: `\bshuffle\w*|\brepeat\b`.
  Match: `shuffle`.

```text
I didn't liked the terms you have changed of playing songs in any order , play back song and etc . The thing that you have started is not acceptable that shuffle mode and all. This app was the only app where we used to listen music without any problem but you have changed that also. 😞😞😕👎🏻👎🏻👎🏻👎🏻
```

- ID `543c96b7` (full `543c96b7-c43b-41dc-9eeb-8bce057a8c9c`), frozen topic `usability`.
  Remaining-cohort rule: `\bshuffle\w*|\brepeat\b`.
  Match: `shuffle`.

```text
Pros and cons from long term ex premium subscriber point of view: Cons: -no artist info (bio) -no shortcut to album info (year) -no shuffle play in android -inferior sound quality vs other services (with good speakers or LDAC / AAC) -commercials every 2-3 songs -commercials play sideways (portrait) while in landscape mode Pros: "Free" ad supported music but WAY too many ads!
```

- ID `8ec05eaa` (full `8ec05eaa-28ac-4cf2-8c5c-a55c66526b85`), frozen topic `usability`.
  Remaining-cohort rule: `\bshuffle\w*|\brepeat\b`.
  Match: `shuffle`.

```text
Keeps putting on random songs whenever I pick a song it puts on a different one and I can't press the shuffle or replay button because they aren't there lol 😂
```

- ID `53d1007a` (full `53d1007a-d58b-44c7-a58d-8c17678635b4`), frozen topic `usability`.
  Remaining-cohort rule: `\bshuffle\w*|\brepeat\b`.
  Match: `shuffle`.

```text
We don't listen song in play in order and shuffle this is very bad update 😠
```

### usability--unspecified

Moved **341** IDs / severity_sum **1,071** to the new issue. Remaining **4,424** IDs.

- ID `4587acd8` (full `4587acd8-b54b-4b25-9d4a-a6bf60cfec0f`), frozen topic `usability`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Recent update was so ugly
```

- ID `a2a41b1d` (full `a2a41b1d-48e1-4468-8790-c8a809d5c82e`), frozen topic `usability`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Horrible app to use. Literally unusable in the free version.
```

- ID `7a207b43` (full `7a207b43-d217-46a3-8e52-89085d638418`), frozen topic `usability`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I can't open my play list and play any song
```

- ID `00f86d5c` (full `00f86d5c-350e-4eb8-8782-3f149f7418ec`), frozen topic `usability`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Spotify was great, then they decided to release an update that made it so when you save a song, it doesn't automatically save the album. It's extremely inconvenient and frustrating in daily use. A setting for this would be an easy solution.
```

- ID `b68a3e9d` (full `b68a3e9d-35ca-43fa-bb59-621bf2cb07c1`), frozen topic `usability`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Too much adds and now it's worst
```

### usability--queue-playlist-controls

Moved **330** IDs / severity_sum **1,032** to the new issue. Remaining **1,731** IDs.

- ID `137f6281` (full `137f6281-6f00-4968-8dfc-15f7fd36e6ed`), frozen topic `usability`.
  Remaining-cohort rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`.
  Match: `Playlist`.

```text
I love the music, I love the ease of operating the app, I love how easy it is to add things to Playlist and favorites. I am giving a 1 star review however, because when I create a play list I DO NOT want Spotify adding anything to it. If I don't put a song on my list it doesn't belong there, and until they stop auto adding songs to my Playlists my review will remain at 1 star.
```

- ID `46069a88` (full `46069a88-3223-410d-aa41-38923f9605be`), frozen topic `usability`.
  Remaining-cohort rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`.
  Match: `playlists`.

```text
I hate the new home page screen, please change it back, it make finding my playlists and things I listened to infinitely harder. Spotify, please change the home page back, I swear, at least make the thing optional so we can pick 😭
```

- ID `fb00c755` (full `fb00c755-5842-40b5-bd8b-0401bd6bba92`), frozen topic `usability`.
  Remaining-cohort rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`.
  Match: `playlist`.

```text
Spotify is a pretty good app to listen to music, the only thing that bothers me is that there isn't an option to loop a song or play the playlist in order.
```

- ID `0d1304af` (full `0d1304af-5598-44f1-aa98-7ae19562d226`), frozen topic `usability`.
  Remaining-cohort rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`.
  Match: `playlist`.

```text
This is the only app I use for music, I really like and enjoy it all the music on my Liked playlist. I can no longer get into my Liked playlist. It's visible in my library but clicking on it results in a blank page. The same thing occurs when looking music up and clicking on albums or things other than the music/artist. Please fix this.
```

- ID `34ac5cd8` (full `34ac5cd8-9582-4f4a-bf34-f02170082367`), frozen topic `usability`.
  Remaining-cohort rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`.
  Match: `playlists`.

```text
-1 star for automatic updates on playlists. There's no playback history and I keep losing songs bc playlists change before I can save them, it makes listening with the app annoying. -1 star for forced data usage, you are a drain on my monthly mobile bill and WiFi only downloads should have been an option 10 years ago. -1 star for no option to mark as "not interested" or ability to block artists. Get with the times, you're already copying tiktok with scrolling genres, give us control to say no!
```

### billing--price-paywalls

Moved **247** IDs / severity_sum **733** to the new issue. Remaining **856** IDs.

- ID `9c6b78e9` (full `9c6b78e9-1b2b-4434-9f03-efcd44e649f0`), frozen topic `billing`.
  Remaining-cohort rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`.
  Match: `pay`.

```text
I like the app but the reason I rated it 4 stars because so I really would like to change the icon of my videos on my playlist but nope you have to pay money each month just to have that people say that they can't even pick the videos in there playlist please make less things premium I actually want to enjoy music
```

- ID `457d32d5` (full `457d32d5-a0d8-4fd5-a809-fcaa5abf896e`), frozen topic `billing`.
  Remaining-cohort rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`.
  Match: `expensive`.

```text
Too expensive
```

- ID `2949d8dd` (full `2949d8dd-8977-45c2-8020-8e4a88fb94d7`), frozen topic `billing`.
  Remaining-cohort rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`.
  Match: `pay`.

```text
Forcing users to pay for subscription...Cheap tactics
```

- ID `571fb9f7` (full `571fb9f7-df22-4438-8fff-c41b771204f9`), frozen topic `billing`.
  Remaining-cohort rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`.
  Match: `Pay`.

```text
Pay to listen songs!!
```

- ID `3cb1face` (full `3cb1face-2755-4b99-829b-cd5da0c63a79`), frozen topic `billing`.
  Remaining-cohort rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`.
  Match: `pay`.

```text
absolute trash with the new update man,like why tf did u have to make it pay to play so bad just why
```

### usability--ad-interruptions

Moved **230** IDs / severity_sum **694** to the new issue. Remaining **6,125** IDs.

- ID `d5fe3ca4` (full `d5fe3ca4-265d-468c-a7fa-b5e95586f778`), frozen topic `usability`.
  Remaining-cohort rule: `\bads?\b|\badvert\w*|\bcommercials?\b`.
  Match: `ads`.

```text
To many ads
```

- ID `eb911339` (full `eb911339-bf39-4ce2-847b-68ef5e634ef3`), frozen topic `usability`.
  Remaining-cohort rule: `\bads?\b|\badvert\w*|\bcommercials?\b`.
  Match: `ads`.

```text
Good but too many ads
```

- ID `81f04d2b` (full `81f04d2b-d704-42b1-aea1-f871d0e4c5c3`), frozen topic `usability`.
  Remaining-cohort rule: `\bads?\b|\badvert\w*|\bcommercials?\b`.
  Match: `ads`.

```text
Confusing need less ads
```

- ID `6f7681f2` (full `6f7681f2-8216-42a8-8a01-cdce7d536b22`), frozen topic `usability`.
  Remaining-cohort rule: `\bads?\b|\badvert\w*|\bcommercials?\b`.
  Match: `ads`.

```text
Too many ads
```

- ID `21db576e` (full `21db576e-b17c-4117-89df-862109689fa5`), frozen topic `usability`.
  Remaining-cohort rule: `\bads?\b|\badvert\w*|\bcommercials?\b`.
  Match: `Ads`.

```text
Ads are too much
```

### playback--stops-skips-wont-play

Moved **171** IDs / severity_sum **576** to the new issue. Remaining **1,771** IDs.

- ID `0df6c4a1` (full `0df6c4a1-25bd-4550-81a7-205773a87c61`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`.
  Match: `stops`.

```text
The songs suddenly stops and after every song there is a ad and plz add songs like pehli Mohabbat, tu mileya etc
```

- ID `b3f2983f` (full `b3f2983f-73c9-435b-8207-899a06a8aeaf`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`.
  Match: `doesn't play`.

```text
Half of the songs in Spotify which are trending are unplayable then what is use of paying you guys for premium membership when the app doesn't play trending songs
```

- ID `fc8089fd` (full `fc8089fd-1ba5-47d3-a0a0-f275f249e295`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`.
  Match: `stopped`.

```text
Spotify stopped working all of a sudden
```

- ID `95cb96a0` (full `95cb96a0-6668-48d3-bd98-2908876ccd54`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`.
  Match: `not play`.

```text
Its getting worse now. Spotify will just not play anything at all. Pay for premium and not even an option to report errors. Its been random but getting more and more frequent. Wont even start playing and just have to give up about half the time now. Its prob an easy fix but cant find it and no option to report the bug which is just dumb. So heres your 1 star
```

- ID `1c50672b` (full `1c50672b-3dbc-4d06-bb31-1df03c79e05c`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`.
  Match: `doesn't playing`.

```text
App is not working properly and doesn't playing any song
```

### playback--unspecified

Moved **151** IDs / severity_sum **510** to the new issue. Remaining **2,875** IDs.

- ID `f82dba43` (full `f82dba43-8c87-4a57-a0d5-d0cce778e5a2`), frozen topic `playback`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Just uninstalled because Spotify connect is the dumbest thing I've ever experienced from a music player and they've already said they're not willing to get rid of it. Seriously, there are so many less obnoxious ways to listen to music, pass on this one.
```

- ID `e850f9da` (full `e850f9da-2449-420d-8105-7504dca41cb5`), frozen topic `playback`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
When I play a specific song, the app just plays another, and I can't get rid of it. It's so annoying
```

- ID `74c6a145` (full `74c6a145-5c92-4445-a487-ef786cae3061`), frozen topic `playback`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Worst music app ever now you can't able to listen to your favourite parts of songs literally iam deleting my Spotify enough
```

- ID `ac7d457c` (full `ac7d457c-2653-4069-91fb-c6032af27e48`), frozen topic `playback`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
It keeps playing songs that aren't even on my playlist other than that it's okau
```

- ID `adafc272` (full `adafc272-af4a-4c02-96f5-cdcc21ee8970`), frozen topic `playback`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Playing well and all the songs I search are available. But unable to open 80% of albums. The screen goes all black when I try to access any albums.
```

### billing--unspecified

Moved **71** IDs / severity_sum **219** to the new issue. Remaining **1,066** IDs.

- ID `cde44079` (full `cde44079-2849-459f-9b98-c9b40908246b`), frozen topic `billing`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Worst app ! It literally compels you to buy the prime membership. If you have not paid it doesn't allow you to go to the previous song , it doesn't allow to drag the ongoing music back or ahead , there are tooo many ads. Seriously worst app ever !
```

- ID `0b56c2ca` (full `0b56c2ca-a701-4048-bc8e-b0c84b7d63f0`), frozen topic `billing`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Very bad app you just need primium to just take a step. It simply means that for literally every thing you need primium...
```

- ID `10677ff1` (full `10677ff1-aee2-4241-a940-dd968d686f48`), frozen topic `billing`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
If you only want money then why kept the download free. Free users cannot view lyrics
```

- ID `07ae21f3` (full `07ae21f3-e328-440f-8075-ae175607c15c`), frozen topic `billing`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
After the latest update only asks for membership
```

- ID `82b9a4b8` (full `82b9a4b8-e037-49e4-82eb-64fb7601aa0e`), frozen topic `billing`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Nvm, free spotify sucks
```

### usability--interface-navigation

Moved **51** IDs / severity_sum **161** to the new issue. Remaining **742** IDs.

- ID `8f775fd4` (full `8f775fd4-f31a-408c-9277-7c07f860547f`), frozen topic `usability`.
  Remaining-cohort rule: `\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*`.
  Match: `button`.

```text
This app keeps on taking me to other songs i dkn't even want to watch when₩ i press the play button it plays another song please fix this!
```

- ID `f9325008` (full `f9325008-5152-490d-9db6-399d455cbe34`), frozen topic `usability`.
  Remaining-cohort rule: `\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*`.
  Match: `button`.

```text
The new "like" button for the songs is awfull and very annoying, not only does it not make sense to be a check but it's also disproportionally big making it a distraction when using the app. Overall 3/10 for the new look.
```

- ID `2f480197` (full `2f480197-3ea4-4bf5-a58f-703f273f28e9`), frozen topic `usability`.
  Remaining-cohort rule: `\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*`.
  Match: `interface`.

```text
Lovely app. Fabulous collection of songs. The user interface is also very simple and easy to use. Though it a very smooth experience, the constant ads disrupt this. They pop up every 10 minutes and it becomes annoying.
```

- ID `4963ad8c` (full `4963ad8c-ca50-4871-a331-e1e1de3ff12c`), frozen topic `usability`.
  Remaining-cohort rule: `\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*`.
  Match: `UI`.

```text
Please fix the UI. Everyone I know has the bottom title/pause bar disappear regularly.
```

- ID `d9fcaf6e` (full `d9fcaf6e-187a-4d93-ac4a-8685e424f66b`), frozen topic `usability`.
  Remaining-cohort rule: `\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*`.
  Match: `UI`.

```text
The new UI is literally unusable. All I want is to see my recently played and daily mixes. Why would you take away the option for us to easily access these things? Guys, I don't know if you know this, but not every app has to be TikTok-ified. Christ Almighty. Also WHY, WHY, WHY does every one of these cards auto-play?! It makes me not even want to open the app and risk getting blasted in the face with podcasts I'm not interested in.
```

### billing--subscription-cancellation

Moved **28** IDs / severity_sum **89** to the new issue. Remaining **306** IDs.

- ID `b697b0d7` (full `b697b0d7-f49f-43e1-8fde-31ccecd894eb`), frozen topic `billing`.
  Remaining-cohort rule: `\bcancel\w*|\brenew\w*|\bsubscription\w*`.
  Match: `subscription`.

```text
One of the worst music apps Ive ever had. No matter how updated everything is, it cuts off in the middle of songs and when I open the app again, the song is restarted. It also skips in the middle of songs like Im listening to a CD. My subscription, although cancelled, still is hitting my account.
```

- ID `db6da51a` (full `db6da51a-eb0c-4d44-95bb-d3fab1934bba`), frozen topic `billing`.
  Remaining-cohort rule: `\bcancel\w*|\brenew\w*|\bsubscription\w*`.
  Match: `subscription`.

```text
You need to buy subscription even for rewinding the song. Lame app
```

- ID `437bf5a0` (full `437bf5a0-be18-42e0-b50f-a70ea1df1251`), frozen topic `billing`.
  Remaining-cohort rule: `\bcancel\w*|\brenew\w*|\bsubscription\w*`.
  Match: `subscription`.

```text
Now I don't like this app because each and everything do we need subscription...
```

- ID `3271b8d6` (full `3271b8d6-decc-4482-b7fa-a0b7a1547a92`), frozen topic `billing`.
  Remaining-cohort rule: `\bcancel\w*|\brenew\w*|\bsubscription\w*`.
  Match: `subscription`.

```text
Without subscription you'll not use this app for a minute to play a single song after a song played it have too many adds listen useless application.
```

- ID `d573bff2` (full `d573bff2-2502-4657-a386-992a3a249379`), frozen topic `billing`.
  Remaining-cohort rule: `\bcancel\w*|\brenew\w*|\bsubscription\w*`.
  Match: `subscription`.

```text
This app becomes worst app 'cause of new subscription.....
```

### catalog--lyrics

Moved **16** IDs / severity_sum **50** to the new issue. Remaining **670** IDs.

- ID `950d3984` (full `950d3984-9f2f-44be-91eb-7c5aff2acd62`), frozen topic `catalog`.
  Remaining-cohort rule: `\blyrics?\b`.
  Match: `lyrics`.

```text
i will say that this app is nice, but i would like spotify creaters to put the lyrics of Bollywood songs (Hindi songs) in Hindi only, rather than lyrics coming in english font. i don't know why but I don't like this fact that you are putting the lyrics of Korean, Arabic, Japanese etc songs in their own language font but in Hindi songs you're using english as the font, so please change the font! I HOPE YOU'LL NOT IGNORE THIS.
```

- ID `2c98b130` (full `2c98b130-3102-486d-b0c2-5e78886e6a50`), frozen topic `catalog`.
  Remaining-cohort rule: `\blyrics?\b`.
  Match: `lyrics`.

```text
Bekar hai lyrics toh show hoti ni
```

- ID `eb17b67c` (full `eb17b67c-2616-4d79-9017-66b65c77a62a`), frozen topic `catalog`.
  Remaining-cohort rule: `\blyrics?\b`.
  Match: `lyrics`.

```text
U morons really added lyrics to premium 🤡🤡🤡
```

- ID `6708d47f` (full `6708d47f-adfb-4fc7-af16-c790ce83d0da`), frozen topic `catalog`.
  Remaining-cohort rule: `\blyrics?\b`.
  Match: `lyrics`.

```text
Very good most of the time, however recently, I have had issues with the lyrics for songs. The lyric box says 'couldnt load lyrics for this song' on songs it would load in the past. I don't know if this is an issue on my end or something others experience, but it's made an impact on my user experience.
```

- ID `ae73448e` (full `ae73448e-e451-4784-ac75-97b717ba242f`), frozen topic `catalog`.
  Remaining-cohort rule: `\blyrics?\b`.
  Match: `lyrics`.

```text
I am using this app from 1year and it had a good experience.All the artists which we like , we can add to library.That's good thing. The unlike feature is the ads which are not related to music otherwise the ads of songs are fine, no problem at all.The adds are minor ones so I'm giving it a 5-star rating. This app deserve much more. But sometimes the lyrics don't come that's also the problem,but it should be there. And thanks to the app maker 'cause it have the podcasts too😃.
```

### catalog--unspecified

Moved **14** IDs / severity_sum **46** to the new issue. Remaining **1,137** IDs.

- ID `d67ec25a` (full `d67ec25a-0a0f-4164-9c29-d8b32679c4c0`), frozen topic `catalog`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I don't how crazy that the biased and Islamphobia reached music platforms, so you're deleting the song (dammi Philistine) for ne reason except that it's about palestine? I'm deleting this app and canceling my subscription now Disgusting.
```

- ID `9f27dace` (full `9f27dace-25f0-4626-bbc6-6be99f7b2e84`), frozen topic `catalog`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
So far maybe not so good because now they're removing music so that's why I bought myself a CD player and I'm buying rare music from off CDs from across the world so you better get your act in the game Spotify stop removing music that I like.
```

- ID `e2fd6729` (full `e2fd6729-e9f1-4621-8439-b8e4ee7bbd47`), frozen topic `catalog`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I can't get my choice of songs
```

- ID `d8fd7400` (full `d8fd7400-c71b-49ba-b518-fe172c1fb00d`), frozen topic `catalog`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Some songs are not available
```

- ID `0e2bc0ae` (full `0e2bc0ae-c9df-42f6-848d-6b84b164d8c9`), frozen topic `catalog`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Ap many popular songs are not available in Spotify anymore. They keep on removing good songs everyday so disappointing
```

### downloads--download-failure

Moved **13** IDs / severity_sum **43** to the new issue. Remaining **629** IDs.

- ID `d63f736a` (full `d63f736a-448d-4e14-a050-900f25b2c724`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdownload\w*`.
  Match: `download`.

```text
This app become very bad after update i want to say you that don't download this app! the app which name is black hole music is very much better than this because in black hole music you dowload the songs without adds or anything and all songs of spotify also present in black hole..
```

- ID `b40b04da` (full `b40b04da-9183-4d6e-83cb-b7fc22681249`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdownload\w*`.
  Match: `download`.

```text
The app no longer lets me download my playlists for offline listening. I currently have none download. I've tried many things to try and fix the problem but it still doesn't work.
```

- ID `80efaa7b` (full `80efaa7b-6bb8-4d3a-ae18-061e62b6e471`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdownload\w*`.
  Match: `downloaded`.

```text
Paid for premium, downloaded a bunch of albums and Playlists for a road trip. None of the offline music worked. Canceled premium as it was a waste of $10
```

- ID `7de58598` (full `7de58598-bff8-4450-a542-a9572c766ee6`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdownload\w*`.
  Match: `downloaded`.

```text
Spotify really needs to fix bugs. Sometimes I can't even play my downloaded songs when I'm offline!
```

- ID `bc733fb8` (full `bc733fb8-98f4-4114-86df-1c627a740eef`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdownload\w*`.
  Match: `downloaded`.

```text
I'm loving Spotify but the fact that almost everyday when I connect to my wifi the music I had starts being downloaded again isn't on. I mean it automatically delete my music and download them everytime.
```

### playback--crashes-freezes

Moved **12** IDs / severity_sum **45** to the new issue. Remaining **610** IDs.

- ID `471db400` (full `471db400-28c6-4a14-933c-6ca90933697a`), frozen topic `playback`.
  Remaining-cohort rule: `\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*`.
  Match: `crashing`.

```text
I've had a great experience with Spotify until I finally got an issue and could not resolve it. I can't click any song in my liked songs without it crashing the app, but when I go to report the issue the help page brings me somewhere that doesn't show me where to post my issue (even though it says "Browse to one of the help categories listed below and ask a question to the community." There is nothing beneath it. I'm not in a position where I am able to message support so I dont know what to do.
```

- ID `b818e250` (full `b818e250-a48d-481c-874a-6303667445ea`), frozen topic `playback`.
  Remaining-cohort rule: `\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*`.
  Match: `Crashing`.

```text
I don't know why my Spotify is Crashing(I'm Having Premium) when Im trying to play a Song....I have Android 12 on my Smartphone V23.... Expect Spotify to Fix this ASAP.
```

- ID `94e663f0` (full `94e663f0-ff50-4b97-92cf-b459e3925b60`), frozen topic `playback`.
  Remaining-cohort rule: `\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*`.
  Match: `freezes`.

```text
I have premium and when I change songs it goes blank and freezes.
```

- ID `011dec6e` (full `011dec6e-9dbc-4188-a0ce-63416ff7932b`), frozen topic `playback`.
  Remaining-cohort rule: `\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*`.
  Match: `crashes`.

```text
Still one of my favorite listening apps. At times the app crashes unsurprisingly tends to be when a huge artist drops. Overall I enjoy it.
```

- ID `f0fd6b7b` (full `f0fd6b7b-7b25-47f7-b7ce-f06a95591dfc`), frozen topic `playback`.
  Remaining-cohort rule: `\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*`.
  Match: `crashing`.

```text
Application keeps on crashing😪😪😪
```

### billing--charges-refunds

Moved **10** IDs / severity_sum **30** to the new issue. Remaining **180** IDs.

- ID `a2f72cdb` (full `a2f72cdb-a243-4183-ab42-cc49f3d2cbb5`), frozen topic `billing`.
  Remaining-cohort rule: `\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*`.
  Match: `charge`.

```text
I love Spotify but I hate how they try to charge you for you listening to your own damn music that you love!
```

- ID `2e225c36` (full `2e225c36-8f12-43fb-aa51-ffd11eede835`), frozen topic `billing`.
  Remaining-cohort rule: `\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*`.
  Match: `Payments`.

```text
Payments are not reflected in my premium plan it just keeps the adds not advise to use premium anymore
```

- ID `43fd0517` (full `43fd0517-c30d-461a-907b-53487ffae3c7`), frozen topic `billing`.
  Remaining-cohort rule: `\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*`.
  Match: `payment`.

```text
If you make payment it will not get credited.
```

- ID `e71e3197` (full `e71e3197-512a-4407-93ee-32cd33a3ea04`), frozen topic `billing`.
  Remaining-cohort rule: `\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*`.
  Match: `payment`.

```text
They don't accept payment from all Debit cards in india. Their prepaid doesn't allow Very high quality audio. I want high quality audio. I can't change my card only for this app only.
```

- ID `cd262906` (full `cd262906-7f2f-4502-96c4-b077e6536aba`), frozen topic `billing`.
  Remaining-cohort rule: `\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*`.
  Match: `CHARGE`.

```text
WATCH OUT, PLEASE! DO NOT DOWNLOAD IT! THEY CHARGE ME MONTHLY EVEN AFTER NOT USING THE PREMIUM ANYMORE. YOU CAN'T QUIT. THEY WILL CHARGE YOU FORVER. I STILL PAY FOR 4 or 5 M OK MONTHS NOW WITHOUT HAVING THE PREMIUM! I CONTACT AND INFORMED THEM MANY TIMES. BUT THEY CAN'T DO IT BY THEMSELVES. THEY WILL ASK MANY BANK INFOS. WHOM CAN YOU GIVE SUCH?
```

### access--login-credentials

Moved **9** IDs / severity_sum **35** to the new issue. Remaining **1,145** IDs.

- ID `c4a01c9e` (full `c4a01c9e-0569-4d06-a196-173493990b62`), frozen topic `access`.
  Remaining-cohort rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`.
  Match: `login`.

```text
Cannot able login with number worst app
```

- ID `8d8f9149` (full `8d8f9149-f7bb-4f20-b0ed-1ef9632f7776`), frozen topic `access`.
  Remaining-cohort rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`.
  Match: `login`.

```text
Very bad.... unable to login Cant hear songs offline even after the membership
```

- ID `5bcbb92f` (full `5bcbb92f-1f14-4023-b624-d37d2760cba3`), frozen topic `access`.
  Remaining-cohort rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`.
  Match: `login`.

```text
I have 3 accounts linked to Spotify and I try to login into one of them "user not found" or I enter in the right password and email "wrong email and password" I'm sorry but you guys have the worst login system I've ever seen.
```

- ID `98b98a36` (full `98b98a36-892c-452e-ac39-5dbc89c794dd`), frozen topic `access`.
  Remaining-cohort rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`.
  Match: `login`.

```text
I've been trying to login in the app using number in a new device but it is not letting me. I already have a premium for that account
```

- ID `152244a2` (full `152244a2-0479-44eb-9f96-f854bc5476c9`), frozen topic `access`.
  Remaining-cohort rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`.
  Match: `login`.

```text
Installed this on my phone today. It won't allow me to login to my account! I am getting a head ache now from too many attempts to fix this. Really disappointed. Uninstalling the app from my phone and smart watch. Never had an experience like this from other music apps. Now it's saying i can't login due to too many attempts. I even changed my password. Thanks a lot for ruining my pre workout mood. I would have bought a premium version if there was one.
```

### playback--buffering-connectivity

Moved **8** IDs / severity_sum **27** to the new issue. Remaining **671** IDs.

- ID `dc058584` (full `dc058584-0d53-4494-ae21-a3af2c708eaf`), frozen topic `playback`.
  Remaining-cohort rule: `\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b`.
  Match: `Internet`.

```text
The bug that shows No Internet on some wifi networks is pretty annoying. Still I love the app.
```

- ID `5860bc2c` (full `5860bc2c-d36b-48c1-94e4-52ca5d54d1c3`), frozen topic `playback`.
  Remaining-cohort rule: `\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b`.
  Match: `lags`.

```text
Sometimes it lags
```

- ID `bee7a69e` (full `bee7a69e-e9d1-4fe3-b220-f7d5c816a0b3`), frozen topic `playback`.
  Remaining-cohort rule: `\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b`.
  Match: `internet`.

```text
It's great for the most part but the moment that I walk outside my house it doesn't work and then when I do get to somewhere with WiFi the internet doesn't show as working for it
```

- ID `a7a659d3` (full `a7a659d3-7224-45c0-bd6e-73e598d6836d`), frozen topic `playback`.
  Remaining-cohort rule: `\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b`.
  Match: `internet`.

```text
I am loving spotify but it is having very much ads and sometimes the podcasts or songs doesn't start if you are having internet then also . But im using samsung phone recently i uninstalled the app and when i re installed it keeps crashing . The app is not starting at all . Spotify PLEASE help
```

- ID `88305448` (full `88305448-b031-4ab7-a265-6320aedaef44`), frozen topic `playback`.
  Remaining-cohort rule: `\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b`.
  Match: `laggy`.

```text
I used to have premium, had to cancel for a while, then recently got it again, and since then, the app is slow, laggy, often freezes, etc.. I use the liked songs then filter by genre(which isn't always correct, btw) and removing or adding a filter often causes the freeze. I've tried clearing the cache, etc to fix it, but it still has a lot of issues. At this point I would almost rather deal with ads and NOT pay for premium purely because of all the issues I've had since getting premium!
```

### access--unspecified

Moved **6** IDs / severity_sum **25** to the new issue. Remaining **420** IDs.

- ID `ec1e4859` (full `ec1e4859-b233-4f41-bb39-f3ce463b6622`), frozen topic `access`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I can't update my Spotify account
```

- ID `d7409261` (full `d7409261-f32d-4efe-8f88-3531f084e3d4`), frozen topic `access`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Someone else's playlist was on my Spotify.
```

- ID `3a35ab0d` (full `3a35ab0d-a1a6-4ff1-981c-919bc5c5dcfc`), frozen topic `access`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
All my stuff got deleted and now i cant even get on spotify
```

- ID `c20fddc7` (full `c20fddc7-f7cf-4bc7-b0a6-6ded4533a2ce`), frozen topic `access`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Someone keeps going on my Spotify and messing with it and idk what is happening
```

- ID `c6e325f9` (full `c6e325f9-e135-49bc-96f1-963c93946466`), frozen topic `access`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I paid my Spotify subscription and I can't access with my number.
```

### catalog--search-results

Moved **6** IDs / severity_sum **20** to the new issue. Remaining **318** IDs.

- ID `be41bcc5` (full `be41bcc5-0d5d-4531-96f5-73347ff1e1cf`), frozen topic `catalog`.
  Remaining-cohort rule: `\bsearch\w*|\bfind\w*`.
  Match: `finding`.

```text
Why is there a download option when I can play music offline? Apart from this issue, I think the app is a great app. Also there are some songs I'm not finding on the app. But it is a great app to sort, enjoy and discover loveable music
```

- ID `758e9395` (full `758e9395-2d80-4a28-95ac-355086a5ded9`), frozen topic `catalog`.
  Remaining-cohort rule: `\bsearch\w*|\bfind\w*`.
  Match: `find`.

```text
this app make me found out the music I want,but not all have the song I want to,but at all the sounds of the song it's very clear. good app if you consider to find all of kind music
```

- ID `829a1a01` (full `829a1a01-5bb8-421b-b187-c38e12acf43b`), frozen topic `catalog`.
  Remaining-cohort rule: `\bsearch\w*|\bfind\w*`.
  Match: `searched`.

```text
I searched and played "ram siya ram" song and like all othermusic player I have used earlier (JioSaavn, YouTube music, YouTube, Gaana) I expect similar songs (either related to Ram or bhajan or bhakti or modern bhakti song or latest similar songs) but Spotify never plays a single relevant song. Is this your recommendation ? Seriously 😐😑😐 ?
```

- ID `3a6becfb` (full `3a6becfb-0790-46b9-8081-a52ada3c723b`), frozen topic `catalog`.
  Remaining-cohort rule: `\bsearch\w*|\bfind\w*`.
  Match: `search`.

```text
The app won't play the songs I want, if I search a song and hit play it randomly gives my something else, and no matter what I try I don't getcthe song I wanted
```

- ID `7f8f46b0` (full `7f8f46b0-34cf-48e6-b0fc-694459084e53`), frozen topic `catalog`.
  Remaining-cohort rule: `\bsearch\w*|\bfind\w*`.
  Match: `search`.

```text
AI algorithm is very biased to location and weights for play history and search history are very low.
```

### catalog--discovery-recommendations

Moved **4** IDs / severity_sum **11** to the new issue. Remaining **195** IDs.

- ID `10776810` (full `10776810-ec56-41d7-bfd5-2d6608bf22a5`), frozen topic `catalog`.
  Remaining-cohort rule: `\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b`.
  Match: `recommend`.

```text
Nice app!! I recommend downloading, also I do not know how to describe this so don't call me bot btw there's a few glitches like if there's a song on Spotify it won't show but if u make a new account it shows for some reason -shaifan
```

- ID `ea6b1744` (full `ea6b1744-5a91-4434-abe5-9dd973b6129c`), frozen topic `catalog`.
  Remaining-cohort rule: `\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b`.
  Match: `radio`.

```text
I heart radio by far ALOT BETTER . I don't like that I have to listen to people I'm not into some are not talented at all
```

- ID `00a20de3` (full `00a20de3-39ad-464b-ad2c-fd050912614e`), frozen topic `catalog`.
  Remaining-cohort rule: `\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b`.
  Match: `recommendations`.

```text
The music recommendations it's horrible, when you listen rap 90's music, Spotify recommends pop music, because the band now play pop music...
```

- ID `77062f85` (full `77062f85-98de-4041-9609-c9c3544c847f`), frozen topic `catalog`.
  Remaining-cohort rule: `\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b`.
  Match: `Discovery`.

```text
The new tik tok like UI is absolutely horrible. Discovery is harder than ever, can't seem to get any more than one daily mix any more,.. it's just horrendous. I'll be getting an album list out of here and into another app. It's been long overdue anyways.
```

- ID `896b5d5a` (full `896b5d5a-7429-4851-aa47-e8bc7d6a2bf5`), frozen topic `catalog`.
  Remaining-cohort rule: `\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b`.
  Match: `radio`.

```text
Love Spotify, the only thing is when you use the radio it plays the same songs.
```

### catalog--availability-selection

Moved **3** IDs / severity_sum **9** to the new issue. Remaining **195** IDs.

- ID `75716c24` (full `75716c24-84e3-4ad4-a5c5-7fd542ee505c`), frozen topic `catalog`.
  Remaining-cohort rule: `\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*`.
  Match: `missing`.

```text
Many songs are missing like chunar, ve mehi and many more
```

- ID `9a147d05` (full `9a147d05-588e-4739-882c-93d118b56240`), frozen topic `catalog`.
  Remaining-cohort rule: `\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*`.
  Match: `Removed`.

```text
Removed dammi falastini song
```

- ID `5b8aa0f4` (full `5b8aa0f4-f958-4443-9991-241ab4aedaff`), frozen topic `catalog`.
  Remaining-cohort rule: `\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*`.
  Match: `removed`.

```text
Many Bollywood Albums/Songs are not here and have been removed. Eg. Kalank, Bhediya, Raees, Kedarnath, and many more albums have disappeared. What's even the use of Spotify. I'd better pay for YouTube premium.
```

- ID `6e7c514e` (full `6e7c514e-9ecb-479c-84e1-42f3d28c6c76`), frozen topic `catalog`.
  Remaining-cohort rule: `\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*`.
  Match: `unavailable`.

```text
Lot of songs unavailable to play.
```

- ID `c3742796` (full `c3742796-330a-4d2d-8d1f-6e02b78291fd`), frozen topic `catalog`.
  Remaining-cohort rule: `\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*`.
  Match: `removed`.

```text
I mean, it's a well built music app, theyre not that expensive and they have student plans which helped with that, I only wish they would stop removing songs from their platform, there were some really good ones that got removed and I'm still a little butthurt about it.
```

### downloads--offline-access

Moved **3** IDs / severity_sum **12** to the new issue. Remaining **183** IDs.

- ID `ee6f9812` (full `ee6f9812-43d1-4831-92db-df49b787b498`), frozen topic `downloads`.
  Remaining-cohort rule: `\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b`.
  Match: `offline`.

```text
The app is pretty good - better than most music listening apps if I'm honest, but I had to dock a star because it randomly stops playing my music at times which is really annoying. I'm taking this down to 3 stars because now I can't play my liked songs offline even though I have premium
```

- ID `e273c172` (full `e273c172-4960-479a-925d-c6404edef36e`), frozen topic `downloads`.
  Remaining-cohort rule: `\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b`.
  Match: `offline`.

```text
My offline downloaded music won't play offline, I've removed and redownloaded them to no avail
```

- ID `474fbbb6` (full `474fbbb6-ad0b-402e-87e5-1f29b14b58ea`), frozen topic `downloads`.
  Remaining-cohort rule: `\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b`.
  Match: `offline`.

```text
Some issues with my saved songs loading when offline.
```

- ID `b9b2a4a7` (full `b9b2a4a7-0a9a-484f-9bac-e95bb93bb2c6`), frozen topic `downloads`.
  Remaining-cohort rule: `\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b`.
  Match: `OFFLINE`.

```text
OFFLINE PLAY LIST DO not work what the heck If the hole reason I downloaded the app
```

- ID `1f6b2977` (full `1f6b2977-c0c5-41c3-a840-39bdfd48d49f`), frozen topic `downloads`.
  Remaining-cohort rule: `\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b`.
  Match: `offline`.

```text
I love this app, but Im paying Premium and my liked songs cannot be played offline, and as someone who doesnt make playlists at all this is dumb. My discover weekly and every single other playlist Ive tried downloading work fine. Its only the liked songs and its driving me nuts.
```

### other--unspecified

Moved **2** IDs / severity_sum **4** to the new issue. Remaining **36,227** IDs.

- ID `7de24315` (full `7de24315-dc2c-41af-83bd-c31a986d063c`), frozen topic `other`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Very bad
```

- ID `712a0805` (full `712a0805-e563-4348-8b90-f8130e562e58`), frozen topic `other`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Worst!!!!!! Gonna uninstall.
```

- ID `539a95bb` (full `539a95bb-eebb-40eb-8577-0ce692a95bb3`), frozen topic `other`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
bad
```

- ID `21bf5d77` (full `21bf5d77-1a4f-4e24-8b10-946a1551dae4`), frozen topic `other`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Hate this application
```

- ID `2e733151` (full `2e733151-75cd-4c45-a7e2-f24a7eaddd36`), frozen topic `other`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Very bad app
```

### playback--audio-quality-volume

Moved **2** IDs / severity_sum **7** to the new issue. Remaining **207** IDs.

- ID `17aa6f58` (full `17aa6f58-4975-4429-a905-7eede9d63732`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b`.
  Match: `volume`.

```text
Love the app, love the ease of use, love the variety in my personal mixes (other apps just play the genre most recently listened to.) My only complaint is that the DJ volume in the DJ mix is wildly louder than the music, to the point that I've found myself ripping out my ear buds because Mr. AI is screaming out the upcoming music.
```

- ID `683b8de6` (full `683b8de6-0ac0-4a29-8d2c-90268a993094`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b`.
  Match: `sound quality`.

```text
Has pretty much all music that exists, though the sound quality is much worse compared to other streaming services, especially Tidal.
```

- ID `c40b5703` (full `c40b5703-02ba-4d77-816e-ef544d07769b`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b`.
  Match: `Bluetooth`.

```text
App is constantly having issues getting stuck when trying to play songs over Bluetooth. Songs get auto paused and it can't be fixed unless you go into the app which is not doable while driving. I'm paying for premium for a broken app.
```

- ID `4cc47dcf` (full `4cc47dcf-2128-4ff0-976f-786aa7a286c8`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b`.
  Match: `Bluetooth`.

```text
Recognition in the app of Bluetooth connections is awful. Doesn't recognise active devices. Update: seems the standard comment from Spotify to all issues is uninstall & reinstall. How about making sure updates work?
```

- ID `df2030ec` (full `df2030ec-63c7-4e6c-bee6-854bd0b15917`), frozen topic `playback`.
  Remaining-cohort rule: `\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b`.
  Match: `volume`.

```text
It okay for me cos it accurate, I hate to say this but I love this app, Oh and one more thing the beat of all songs or the volume is not loud, so you guys should put more efforts on the volume
```

### downloads--missing-downloads

Moved **1** IDs / severity_sum **3** to the new issue. Remaining **27** IDs.

- ID `b00c858f` (full `b00c858f-fdac-4f53-9a0c-8938d445dc82`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b`.
  Match: `lost`.

```text
Unsubscribed just to subscribe on the day I want to be billed why can't we have an option to choose the billing date now it's not even playing even after updating and I've lost all my downloads big let down
```

- ID `65f72409` (full `65f72409-0c61-42d5-a355-ca23cd88f6ee`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b`.
  Match: `deleted`.

```text
The app restarted after everything was deleted within a second, like why do I pay it if it is going to delete my songs , This app has nice features but it sucks I'm going to use YouTube music
```

- ID `f9506a5d` (full `f9506a5d-140d-4930-acda-7332debdbdd5`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b`.
  Match: `disappear`.

```text
Songs disappear randomly. In addition, I have to download the songs on PC, and save the cache at specific location. And when I try to restore the songs with same cache after reinstalling the OS, the cache doesn't work. Again I have to download the all the songs. It's the waste of my time, money and data, after paying all that money to spotify.
```

- ID `26921ea8` (full `26921ea8-01cd-4b5a-a960-0fcb725aab8a`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b`.
  Match: `removed`.

```text
Am going to Uninstall this app because they removed the song safar!!! And worst app can't download any song simply waste
```

- ID `2e0e910d` (full `2e0e910d-a8b8-4ea6-a43c-38ee4a926168`), frozen topic `downloads`.
  Remaining-cohort rule: `\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b`.
  Match: `missing`.

```text
Very good music App But one thing missing out is the fact that we can't DOWNLOAD JUST A SONG OFF AN ALBUM. Why do we have to download All??? Work on that, aside that...it's superb
```

### downloads--unspecified

Moved **1** IDs / severity_sum **3** to the new issue. Remaining **105** IDs.

- ID `4cbb09bd` (full `4cbb09bd-0e48-4ed4-8bbd-f818b5f2f0a8`), frozen topic `downloads`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
هو حلو بس ازاي مينفعش نحفظ الاغنيه او نسمعها مره وحده بدون نت
```

- ID `5f261d98` (full `5f261d98-a21e-42da-80ad-1ca821625f0e`), frozen topic `downloads`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
Good but it eats ur storage more and more 👎
```

- ID `5e828d27` (full `5e828d27-1027-4c3f-882a-76450a8143e6`), frozen topic `downloads`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
This is a very useless app, it doesn't work once you delete it.
```

- ID `682e77ea` (full `682e77ea-3c37-4a46-a33c-4de26f1af494`), frozen topic `downloads`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
I have redownload songs sometimes and it's annoying
```

- ID `54d76a03` (full `54d76a03-f72f-4dae-8edd-c8216f9f605b`), frozen topic `downloads`.
  Remaining-cohort rule: `No unprotected specific match`.
  Match: `none`.

```text
So many advertisement and the song that you save can't play
```

### playback--background-resources

Moved **1** IDs / severity_sum **3** to the new issue. Remaining **109** IDs.

- ID `607db303` (full `607db303-525d-4226-a86c-749430f2378d`), frozen topic `playback`.
  Remaining-cohort rule: `\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b`.
  Match: `background`.

```text
Edit: I now regularly have to uninstall and reinstall just to get the app to work on my Fold 5. Customer service is still just as unhelpful. Highly recommend using a different service. This app no longer runs in the background even though all settings for it are turned on. Customer service is near impossible to get a hold of and they only parrot lines from a script when you do.
```

- ID `5ca27f03` (full `5ca27f03-0308-4d24-b1c2-13f3b7b2bbd2`), frozen topic `playback`.
  Remaining-cohort rule: `\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b`.
  Match: `memory`.

```text
Can't run spotify after last update - "not enough memory" (yeah, ofc..)
```

- ID `e3c53862` (full `e3c53862-d310-48b0-8475-10602bbe5e12`), frozen topic `playback`.
  Remaining-cohort rule: `\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b`.
  Match: `background`.

```text
absolutely dogshit music player you can literally use phone's default background stream on YouTube to play songs
```

- ID `3ffde422` (full `3ffde422-a8e6-4938-9c06-bf10c5746f99`), frozen topic `playback`.
  Remaining-cohort rule: `\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b`.
  Match: `background`.

```text
Good app for what it is. Great variety of content. The one thing that needs to be fixed is how it runs in the background. I will go days without using the application but as soon as I connect to the Bluetooth the application begins to play. Because the application was never actually open, I then have to go into my apps settings and force stop the program.
```

- ID `45c91edb` (full `45c91edb-cca8-46f6-bd37-21b680feef5c`), frozen topic `playback`.
  Remaining-cohort rule: `\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b`.
  Match: `background`.

```text
Looks like I'm having the same problem every one is having after my phone update, no playlist on my phone's background, and the app won't stay active after I press pause, now there is a ritual, I have to go thru just to start playing my music. I've noticed there is no feed back from Spotify on what's happening. Thanks for making this app worse👍. Guess it's time to go back to Pandora 😐.
```

### support--resolution-quality

Moved **1** IDs / severity_sum **3** to the new issue. Remaining **19** IDs.

- ID `5782aeec` (full `5782aeec-f1e0-4730-a0c4-51ba54303b27`), frozen topic `support`.
  Remaining-cohort rule: `\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b`.
  Match: `support`.

```text
Rough experience with Duo plan technical issues. Customer support has no power to credit users for lost service. We paid for duo for a month before we managed to get it working with tech support. No credit. No discount. No refund (even partial) I entreat Spotify to make it right. I'll likely change my opinion if they do.
```

- ID `3d7573d1` (full `3d7573d1-85e8-4ca4-a620-c1f8901ce015`), frozen topic `support`.
  Remaining-cohort rule: `\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b`.
  Match: `support`.

```text
I'll never download music again. You have the world of music at your fingertips for a reasonable price. That being said when I point out music to technical support that has explicit lyrics that are not marked accordingly I get a 45-minute chat run around with no resolution. Extremely bad service in that regard. All they have to do is play the piece that I pointed out to them and they would see within a minute.
```

- ID `6529bdf5` (full `6529bdf5-0936-4584-9a2e-f2b0d3278ab9`), frozen topic `support`.
  Remaining-cohort rule: `\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b`.
  Match: `helpdesk`.

```text
For issue regarding payment no helpdesk or customer care no.
```

- ID `5196c13b` (full `5196c13b-59ac-4955-9c2d-8f8785418b1b`), frozen topic `support`.
  Remaining-cohort rule: `\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b`.
  Match: `support`.

```text
Constant ads with worse frequency than terrestrial radio. Unhelpful support that blame you or your device. Not worth premium price.
```

- ID `89cfd88d` (full `89cfd88d-be20-4625-890f-de2462aabff1`), frozen topic `support`.
  Remaining-cohort rule: `\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b`.
  Match: `support`.

```text
It's been a sub par music service since it started. The ups are when the competitors screw up. Lack of any support when it's down and most feedback goes unheard. Spotify video across all platforms.
```


## Premium residual display name and stop condition

Do not retain the control-specific display name "Premium-only controls and upgrade pressure" for the residual. The five residual examples mix upgrade pressure, free-tier dissatisfaction, lyrics access and platform comparison. Proposed residual display name: "Premium subscription and upgrade complaints"; stable issue ID stays `billing--premium-upgrade-mentions`. No primary topic changes.

Stop here for owner review. No production verifier, group or memo call; no change to frozen labels, no human golden labels read, no final membership/claims applied, and no grading gzip rewrite/recommit. V2 must be accepted before adapting the pending Phase 7 runner and its group evidence packs.

## Offline rule-validation refinement and reproducibility

The initial forced-shuffle matcher also caught algorithm-only repetition (only shuffling particular songs). It was narrowed to forced mode/control wording, with regression tests. Conditional "if you do not buy Premium" is now explicit gating. The initial candidate and sample are preserved in `artifacts/phase7/cohort-v2/initial-candidate/`; the same seed was retained and no examples were hand-swapped. This report uses the revised rule hash above.

Reproduce with `.venv/Scripts/python.exe -m pipeline.cohort_v2_report`. Full rules are in `pipeline/issue_cohorts_v2.py`. A synthetic cross-topic fixture passes the actual supplied checker; this is a mechanical test, not model execution evidence.
