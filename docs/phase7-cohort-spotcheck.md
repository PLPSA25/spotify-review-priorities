# Phase 7 cohort spot-check v1 — owner corrections received

Superseded for review by `docs/phase7-cohort-spotcheck-v2.md`. No paid stage ran. The original examples remain unchanged below.

Offline only. Five pseudorandom member IDs per cohort, uniform over eligible IDs using SHA-256(seed + cohort + review_id); seed `spotify-phase7-cohort-spotcheck-v1`. Golden exact texts are excluded. Sampled IDs are distinct; duplicate exact texts remain eligible, preserving row weighting. This is a small qualitative check, not a random accuracy estimate.

The frozen primary topic is used first; the lexical rule only subdivides that topic. In particular, the Premium rule is never used to assign billing to a non-billing record. Contract line 36 says a Premium mention alone does not make billing; this design does not override it. A classifier topic error can still persist and must be disclosed, not relabeled silently. A complaint-specific display name will be chosen only if the sample supports it; stable issue IDs and membership need not change.

## usability--ad-interruptions

Full cohort size: 6,355 original IDs.

1. ID `a1197f0c` (full `a1197f0c-957e-4f1d-bb2e-6e764a4f8cf0`)
   Matched rule: `\bads?\b|\badvert\w*|\bcommercials?\b`
   Match: `ads` at character span 9:12.

```text
Too many ads
```

2. ID `ea50834d` (full `ea50834d-6347-4e63-901c-c8709bb44f16`)
   Matched rule: `\bads?\b|\badvert\w*|\bcommercials?\b`
   Match: `ads` at character span 8:11.

```text
So many ads in podcasts despite paying for premium
```

3. ID `8d0cae7c` (full `8d0cae7c-3e69-4a3c-8835-5bba607837ec`)
   Matched rule: `\bads?\b|\badvert\w*|\bcommercials?\b`
   Match: `advertisments` at character span 9:22.

```text
Too many advertisments!!
```

4. ID `ac352a42` (full `ac352a42-1bbe-4c73-bd88-0b1bc2919e46`)
   Matched rule: `\bads?\b|\badvert\w*|\bcommercials?\b`
   Match: `ads` at character span 9:12.

```text
Too many ads
```

5. ID `2691ccb2` (full `2691ccb2-f8db-45ad-a076-008ccc0c6db5`)
   Matched rule: `\bads?\b|\badvert\w*|\bcommercials?\b`
   Match: `ads` at character span 8:11.

```text
To many ads
```

## billing--premium-upgrade-mentions

Full cohort size: 4,465 original IDs.

1. ID `6637cb3b` (full `6637cb3b-844d-4d55-8ed8-7e9dd8b6d689`)
   Matched rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`
   Match: `premium` at character span 48:55.

```text
Worst app update ever.... Only one thing go for premium premium premium...
```

2. ID `1ca3162d` (full `1ca3162d-1a07-4cf3-b869-c87365e41e7e`)
   Matched rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`
   Match: `premium` at character span 116:123.

```text
Using it for free isn't good at all you can do the same things in other apps too Spotify is only good when you have premium why free is so bad
```

3. ID `361c0b33` (full `361c0b33-ee6b-40f9-ab61-32d2762ad312`)
   Matched rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`
   Match: `premium` at character span 57:64.

```text
The basic functions of an app has been totally turned to premium membership facilities, like wanting to loop a song, need premium, and the songs are always in shuffle, the genres that I don't listen to are always playing on repeat no matter what song I play, it's like they have literally banned our basic rights of listening to music
```

4. ID `22a864da` (full `22a864da-7f6a-4745-a6ee-0b2e29f32df4`)
   Matched rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`
   Match: `premium` at character span 109:116.

```text
From 5stars to 1star good journey by Spotify Thanks for the new update which has made even song forwarding a premium task Wishing you from Best to worst music app journey now It's not far when opening Spotify also will be a premium .
```

5. ID `5544a27c` (full `5544a27c-0634-4bc9-b83c-5ac003c2ecc8`)
   Matched rule: `\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*`
   Match: `premium` at character span 42:49.

```text
Why is playing in order only available in premium? This used to be my favourite music app before making everything available for premium.
```

## playback--stops-skips-wont-play

Full cohort size: 1,952 original IDs.

1. ID `5f37de16` (full `5f37de16-2cb8-4c87-aa1b-cc8f3d9080ee`)
   Matched rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`
   Match: `stop` at character span 90:94.

```text
Most recent update has made it impossible to use. 1 song will play then the app will just stop and you have to force close it before you can hit play on another song.
```

2. ID `162d3156` (full `162d3156-5650-4401-bbda-21e09a84cba8`)
   Matched rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`
   Match: `stop` at character span 54:58.

```text
My Spotify is having some issue, the songs would just stop playing if my phone's screen is off and would only play if the screen is on. At first I thought it must an issue of my hearing device or my network but no it is Spotify only. Only sometimes when I'm lucky, my Spotify works fine.
```

3. ID `0cf041bd` (full `0cf041bd-3827-49d6-aa2a-96fce938f6cd`)
   Matched rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`
   Match: `pauses` at character span 32:38.

```text
I love the app but it sometimes pauses on its own when I try to use another app or it stops playing entirely. It's actually frustrating because I have to stay on the app whenever I want to listen to music
```

4. ID `09d5682f` (full `09d5682f-2036-49e7-a1f1-b681f62375a3`)
   Matched rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`
   Match: `stop` at character span 109:113.

```text
Scammers, I don't even get my half an hour of music after getting in writing that I'll get 30 minutes of non stop music. Absolutely pathetic.
```

5. ID `d7aa740b` (full `d7aa740b-bc5a-4279-b97c-4335b4d0a499`)
   Matched rule: `\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b`
   Match: `pause` at character span 57:62.

```text
I work at a good time job and every time I have my music pause and I connect something to my phone it just blast my music out loud where my boss can hear it that's why I'm leaving it at 1 star view so I hate Spotify
```

## usability--queue-playlist-controls

Full cohort size: 2,061 original IDs.

1. ID `40cd0c58` (full `40cd0c58-d237-4223-a560-c4288ee63e25`)
   Matched rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`
   Match: `playlist` at character span 18:26.

```text
Cant unshuffle my playlist....cant go back to the previous song....cant seek the song thats playing ...if my liked songs are playing on shuffle i m getting songs that i haven't even liked in between...truly just ruins the experience in every way
```

2. ID `9a2f9235` (full `9a2f9235-5c31-4726-baf5-dbb5910e345c`)
   Matched rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`
   Match: `playlist` at character span 97:105.

```text
The new update is so bad I can't even swith the previous song back and I can't even listen to my playlist.
```

3. ID `866c3d04` (full `866c3d04-862d-4605-9e2a-0647d286d1eb`)
   Matched rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`
   Match: `playlists` at character span 40:49.

```text
I'm disappointed that they put all your playlists on shuffle, but you get used to it after awhile 🫤
```

4. ID `8b8c0be0` (full `8b8c0be0-13d5-4d26-9ee0-61213ec6a51d`)
   Matched rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`
   Match: `Playlist` at character span 18:26.

```text
Update removed my Playlist....we have the premium account and we're going to cancel if I can't get on the app. It won't let me play, make playlists.....anything, can't even search!
```

5. ID `4c1e568c` (full `4c1e568c-91ff-43c2-9bd2-5af5e546b10d`)
   Matched rule: `\bqueue\b|\bplaylist\w*|\bliked songs\b`
   Match: `playlist` at character span 64:72.

```text
This latest update has ruined spotify for me. I can't listen to playlist in the order i want to or play a song on repeat. If this change was made in hope of more users shifting to premium, then i think spotify are up for a rude awakening. I really loved this app. Now I'll have to find another app for streaming music
```

## access--login-credentials

Full cohort size: 1,154 original IDs.

1. ID `07691789` (full `07691789-4e1d-46d0-8740-50fcf163c416`)
   Matched rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`
   Match: `login` at character span 84:89.

```text
Can't find your number error keep showing while I have entered correct number while login 😶
```

2. ID `9e273b3c` (full `9e273b3c-c727-4511-931f-b4b8450798fb`)
   Matched rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`
   Match: `LOGIN` at character span 13:18.

```text
I CAN'T EVEN LOGIN TO MY ACCOUNT. I ALSO TRIED TO MAKE A NEW ACCOUNT BUT IT DO NOT LOGGED FROM NEW ACCOUNT. I ALSO SAT 15 MINUTES BUT IT DIDN'T OPEN
```

3. ID `10f1364d` (full `10f1364d-999b-4260-aa70-82b46cbb8b61`)
   Matched rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`
   Match: `login` at character span 31:36.

```text
I can't find the mobile number login option.. I can't access my account. Being a premium membership holder this is horrible
```

4. ID `853ad983` (full `853ad983-6c5e-4bb4-ad73-c155e50c0378`)
   Matched rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`
   Match: `login` at character span 13:18.

```text
Cant able to login
```

5. ID `1da40051` (full `1da40051-ed85-4381-9565-54ebe0a5b5c2`)
   Matched rule: `\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b`
   Match: `log in` at character span 14:20.

```text
I just cannot log in to my account! The page just shows me: something went wrong. So could you please tell me how can I log in to my account and what's the problem involved?
```

## billing--price-paywalls

Full cohort size: 1,103 original IDs.

1. ID `6489f809` (full `6489f809-f3be-490b-a5ba-1a9a97ee962f`)
   Matched rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`
   Match: `Pay` at character span 76:79.

```text
It used To be the best music app for Android But the Recent Update made it "Pay to listen" just Dont download it Its Trash
```

2. ID `2827a620` (full `2827a620-1381-461d-a515-c865c120e645`)
   Matched rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`
   Match: `pay` at character span 44:47.

```text
This is so frustrating that you have to now pay for basic features of a music player for which it has been created.Till ads or downloading songs which required premium was fine but now you guys are asking to upgrade for premium even for basic purposes of a music player. This is really annoying.
```

3. ID `498f361e` (full `498f361e-2056-47e9-98a2-98819a5b35ab`)
   Matched rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`
   Match: `pay` at character span 68:71.

```text
The new update is horrendous, spotify is just looking for people to pay in order to have users stream music the way the want.
```

4. ID `6f01f75e` (full `6f01f75e-a65e-4e5b-95dd-6c2c4576bc2b`)
   Matched rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`
   Match: `paying` at character span 184:190.

```text
I love the app its super easy to manage and use has nice features and little details and would recommend, the only issue I seem to have is you only have a good experience if you are a paying individual its not worth taking if you want a free music player because that will lead you to frustratios but overall not bad of an app
```

5. ID `e4c5f61c` (full `e4c5f61c-fee4-4662-8b09-c4d65518b921`)
   Matched rule: `\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*`
   Match: `pay` at character span 137:140.

```text
It was so good before. The ads were the only problem. Now we can't even hear the specific parts of a song, why? Why do you think we will pay just to listen our favourite parts of song? You ruined this app. This is getting worse. I'm so sad how this app turned out. You are digging your own grave. I'm pretty sure so many complained before, but you don't care. Yeah, carry on. See when you get more and more hate for this.
```
