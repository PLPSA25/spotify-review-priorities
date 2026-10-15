# Frozen v3 — final rule revision and fresh sample

Rules were frozen before computing v3 counts or viewing its fresh sample. No further tuning, regardless of resulting rankings or examples. No human golden labels were read. Rule hash: `06add6fd69f3f55fccdbdd1dbd37b5068ae86a681d0d46f6eebdbd7d572cdbc2`.

V1 had no unified cross-topic issue. V2: 3407 reviews / severity_sum 10598. V3: **4444 reviews / severity_sum 13877**.

Only owner-requested recall fixes from random spot-checks were added: plural song parts; broader negation/allowance, payment and free-tier restriction evidence; selected-song substitution as a forced-shuffle symptom. Control evidence and restriction/symptom evidence are both required; Premium alone never matches. Explicit Premium evidence and inferred control restrictions stay distinct.

## Requested review-ID checks

- `8f775fd4` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_selected_song_replaced`.
- `3a6becfb` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_selected_song_replaced`.
- `f8ac4df8` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_shuffle_restriction_contrast`.
- `fb00c755` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `708979fd` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `8ec05eaa` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `53d1007a` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `be94b3ba` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `db6da51a` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `explicit_paywall_or_premium_link`.
- `74c6a145` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.
- `cde44079` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `explicit_paywall_or_premium_link`.
- `e850f9da` → `cross-topic--free-tier-premium-controls`; matched **True**; evidence `inferred_direct_control_denial`.

## Propagated baseline top ten

1. `other--unspecified` — **36225 reviews**, severity_sum **58636**.
2. `cross-topic--free-tier-premium-controls` — **4444 reviews**, severity_sum **13877**.
3. `usability--ad-interruptions` — **6037 reviews**, severity_sum **12965**.
4. `usability--unspecified` — **4228 reviews**, severity_sum **10500**.
5. `billing--premium-upgrade-mentions` — **3152 reviews**, severity_sum **8784**.
6. `playback--unspecified` — **2727 reviews**, severity_sum **8688**.
7. `playback--stops-skips-wont-play` — **1674 reviews**, severity_sum **5590**.
8. `usability--queue-playlist-controls` — **1582 reviews**, severity_sum **4705**.
9. `access--login-credentials` — **1136 reviews**, severity_sum **4466**.
10. `catalog--unspecified` — **1126 reviews**, severity_sum **3115**.

## Random-prefix-only top ten

1. `other--unspecified` — **12002 reviews**, severity_sum **20564**.
2. `cross-topic--free-tier-premium-controls` — **4440 reviews**, severity_sum **13865**.
3. `usability--unspecified` — **3784 reviews**, severity_sum **9609**.
4. `usability--ad-interruptions` — **4088 reviews**, severity_sum **9071**.
5. `billing--premium-upgrade-mentions` — **3123 reviews**, severity_sum **8705**.
6. `playback--unspecified` — **2558 reviews**, severity_sum **8189**.
7. `playback--stops-skips-wont-play` — **1651 reviews**, severity_sum **5513**.
8. `usability--queue-playlist-controls` — **1582 reviews**, severity_sum **4705**.
9. `access--login-credentials` — **1021 reviews**, severity_sum **4008**.
10. `catalog--unspecified` — **1118 reviews**, severity_sum **3093**.

## Ten fresh random members

Seed `spotify-phase7-cohort-spotcheck-v3-final`; original IDs uniformly hash-ordered within the new issue, excluding golden exact texts and previously shown review texts. This is qualitative review, not an accuracy estimate. Sample does not determine any further rule change.

### `57f0e770` (full `57f0e770-c44b-434c-9dcc-8984ac26f9b2`)

Evidence: `inferred_update_control_restriction`; controls: skip-forward.
Restriction/symptom: "can't"

````text
I don't like this new update when you pick a specific album it play songs from other albums too, and whats the point of making a album if you can play the songs you picked? and also what is with the " you can only skip 6 songs a day" like if I don't want to hear that song then I don't want to hear that song you can't make me pay for it. Spotify you lost me I will be using other apps such as youtube
````

### `88dac7ea` (full `88dac7ea-bcf2-4eb3-ac5e-b4f38bb84a34`)

Evidence: `explicit_paywall_or_premium_link`; controls: repeat-loop.
Restriction/symptom: "have to purchase the premium"

````text
I would rather purchase YouTube Music than use Spotify Premium. Atleast, YT Music has a great collection, and I don't need to purchase it just because I want to repeate a song or want play a particular part of that song. What kind of ridiculous update is this that we have to purchase the premium membership just to avail these simple things? FYI, YT Music is much less expensive than your app which doesn't even contain various types of songs.
````

### `d9312090` (full `d9312090-f0b5-4867-ba87-ff667cc7ce59`)

Evidence: `free_tier_control_restriction`; controls: shuffle.
Restriction/symptom: "no shuffle"

````text
Terrible music app, free stations play the same 18 songs over and over again with no shuffle. As of late commercials have interrupted 30 minute commercial free listening promotions every time. Every single time stations will often change to top 100 and artists added to playlist are not all similar to the artist selected to create the station.
````

### `0f440176` (full `0f440176-d201-4eda-a885-99f93401eb30`)

Evidence: `inferred_direct_control_denial`; controls: skip-forward.
Restriction/symptom: "Can't"

````text
Know it becomes a Worse app We can not listen ur choice song Can't forward song They didn't deserve even a single star
````

### `9da0c89b` (full `9da0c89b-1318-45b9-b24e-13753dee31e7`)

Evidence: `inferred_direct_control_denial`; controls: shuffle.
Restriction/symptom: "Can't"

````text
Kind of annoying. Can't play the songs. I don't know if it's just mine, but it's really annoying. You can only listen to your snippets and can't pick your songs individually. Just shuffle. Until fixed it will stay at 3 stars.
````

### `e0c69e11` (full `e0c69e11-068f-436d-8a7f-44050a370409`)

Evidence: `explicit_paywall_or_premium_link`; controls: skip-forward.
Restriction/symptom: "need premium"

````text
CAN'T EVEN FORWARD OR BACKWARD A SONG 👎🏼 Was a great app but now you need premium even for lyrics
````

### `7e271329` (full `7e271329-4c82-403b-a59a-7fd8b6c40405`)

Evidence: `inferred_update_control_restriction`; controls: play-order-selection, shuffle, skip-forward.
Restriction/symptom: "can't"

````text
New update is worst we can't skip song from a particular timing to a particular instant and also i am not able to play songs in order it is in shuffle mode and to play in order buy premium this is the worst update ever.
````

### `5b65f062` (full `5b65f062-51bd-431f-b6fd-4498715cd5a8`)

Evidence: `inferred_direct_control_denial`; controls: play-order-selection, selected-song-replaced.
Restriction/symptom: "can't"

````text
I dont know what are the problem in this app i can't play a song that i want i choose a song and play another song fix it please 👀
````

### `75dddfca` (full `75dddfca-35d4-4cad-9f5c-45c87f580c0e`)

Evidence: `explicit_paywall_or_premium_link`; controls: repeat-loop.
Restriction/symptom: "premium, not only"

````text
This application has became worse after the recent update, actually Spotify is just indirectly making users to purchase premium. From recent update, we can't change the timeline of song bcz its for premium, we can't set the song as auto repeat bcz it's for premium, not only this but we can't even listen and vibe with the song properly as ads have became repeatative!!! So I Beg to the authority that please please please bring the old update back in which non premium users were happy too!!!
````

### `da12436b` (full `da12436b-41c7-44d3-abe1-0d7f7ca7e15f`)

Evidence: `inferred_update_control_restriction`; controls: shuffle.
Restriction/symptom: "cannot"

````text
Bad. The new updates are soooo bad that i had to rage delete this app. You literally cannot see the lyric, shuffle or even change the parts of the song. Theres literally ads every 2 seconds. It looks so cheap for a billion dollar company to be this hungry for money and not care about there reputation being one of the leading music streaming platform. Truly disappointing.
````

Frozen control patterns:

- `shuffle`: `\b(?:un)?shuffl\w*`
- `play-order-selection`: `\bin\s+(?:(?:the|my|any|a|an|desired|specific)\s+)?order\b(?!\s+to\b)|\border\s+(?:i|we|you|they)\b|\b(?:play|playing|choose|select)\s+(?:any|my|a|the|specific)\s+(?:own\s+)?(?:song|track)\b|\b(?:pick|picking|choose|choosing|select|selecting)\s+(?:a|the|my|any|specific)\s+(?:own\s+)?(?:song|track)\b`
- `previous-back`: `\bprev(?:ious)?\b|\b(?:go|going|switch|swith|skip|song|track)\b.{0,18}\bback\b|\bback\s+(?:button|song|track)\b|\bplay\s+back\s+(?:a\s+|the\s+)?(?:song|track)\b`
- `repeat-loop`: `\brepeat\w*|\bloop\w*`
- `skip-forward`: `\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b`
- `seek-rewind-parts`: `\bseek\w*|\brewind\w*|\b(?:specific|favourite|favorite)\s+parts?\s+(?:of|in)\s+(?:(?:a|the|any)\s+)?(?:songs?|tracks?)\b|\b(?:progress|seek)\s+bar\b|\bfast[ -]?forward\w*`
- `basic-player-control-paraphrase`: `\bbasic\s+(?:features|functions|purposes|controls)\b.{0,45}\bmusic\s+player\b|\b(?:stream|play|listen\s+to)\s+music\s+the\s+way\b`
- `selected-song-replaced`: `\b(?:pick\w*|choos\w*|select\w*|play|search\w*|press|hit)\b.{0,100}\b(?:song|track|play\s+button)\b.{0,180}\b(?:plays?|puts?|gives?|takes?|taking)\b.{0,45}\b(?:another|random\w*|different|something\s+else|other)\b`
