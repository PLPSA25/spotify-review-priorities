# Label guide v1 — apply to review_text only

Source of truth: ../data/GRADING_CONTRACT.md. Stars, likes, app version and timestamp
are metadata and must not substitute for reading the text. Examples below are invented
for instruction, never taken from the golden reviews. No golden answers are prefilled.

## Topic

- access: login, signup, passwords or account access.
- usability: navigation, controls, layout, queue/playlist management and ad interruptions.
- playback: failed playback, crashes, lag, connection failures, audio quality or resource use.
- downloads: downloading, saved music, offline listening or disappearing downloads.
- catalog: missing songs/artists, search, discovery, recommendations or lyrics availability.
- billing: price, charges, subscriptions, paywalls or premium entitlement. Explicitly
  premium-only controls belong here.
- support: contacting support or its response.
- other: general praise/criticism, unrelated content or no supported specific topic.

For multiple problems, select the problem with the highest supported severity. If tied,
select the first specific problem mentioned. For positive reviews, select the first
specific praised feature; general praise is other. Merely mentioning a paid plan does
not select billing: playback crashes for a paying customer remain playback.

## Intent (apply in this order)

1. cancellation: explicit personal leaving, uninstalling, cancelling or threats to do so.
2. complaint: a negative experience, including mixed praise and criticism.
3. request: a desired change without a reported failure.
4. praise: positive evaluation without a higher-precedence intent.
5. unclear: unrelated, meaningless or unsupported intent. Bare boycott slogans remain
   unclear unless a product complaint or explicit personal departure is stated.

## Severity (supported impact, independent of intent and sentiment)

1. No reported problem: praise, neutral/unclear text or a pure feature request.
2. Dislike, generic criticism, minor annoyance or cosmetic issue without functional loss.
3. Degraded/restricted function, with some use or workaround remaining.
4. Clearly blocked core task, such as inability to log in or play music.
5. Explicit serious financial, privacy or data harm. High price, crashes, anger and
   cancellation intent alone do not support level 5.

Missing context should trigger needs_review; never invent a functional loss. A valid
schema is not proof of a correct interpretation.

## Worked synthetic examples

- "The navigation icons look untidy, but all controls work."
  usability / complaint / severity 2: cosmetic dislike with no functional loss.
- "The queue reorder button fails, but I can rebuild the queue manually."
  usability / complaint / severity 3: degraded function with explicit workaround.
- "My password reset never arrives and I cannot access my account."
  access / complaint / severity 4: account access is clearly blocked.
- "Two duplicate charges emptied my bank balance and left me unable to buy food."
  billing / complaint / severity 5: explicit serious financial harm.
- "Please add a compact playlist view. Nothing is broken."
  usability / request / severity 1: pure feature request.
- "Premium is active, but music cannot play at all."
  playback / complaint / severity 4: paid-plan mention does not change the defect topic.
- "I paid but Premium never activated; free playback still works."
  billing / complaint / severity 3: entitlement is restricted but use remains.
- "Ads annoy me, so I am uninstalling."
  usability / cancellation / severity 2: departure does not increase impact.
- "The lyrics page is excellent and playlist controls are easy."
  catalog / praise / severity 1: first specifically praised feature wins.
- "Saved tracks vanish offline, but streaming still works."
  downloads / complaint / severity 3: degraded offline function with remaining use.
- "Support ignores my questions; the app otherwise works normally."
  support / complaint / severity 2: dissatisfaction without demonstrated functional loss.
- "The layout looks odd. Music cannot play at all."
  playback / complaint / severity 4: greater supported severity wins over first mention.
- "Search misses the artist; queue reorder also fails. Both work after restarting."
  catalog / complaint / severity 3: equal-impact problems, first mentioned wins.
- "Boycott this company!"
  other / unclear / severity 1: no product complaint or explicit personal departure.
- "Bad app."
  other / complaint / severity 2: generic criticism does not imply a specific defect.
- "It fails sometimes."
  other / complaint / severity 2 / needs_review true: missing defect/impact context;
  conservative label pending review, without inventing a blocked task.

## Declared project decision rules

These explicit project rules supplement the shared contract. The financial rule uses
concrete stated loss as its level-5 threshold; this may be stricter than the contract's
"serious financial harm" interpretation in borderline cases and must be disclosed in
evaluation. The level-4 default for unauthorized charges is a declared project policy,
not an inference from angry language. Keep the same rules in Jev criteria/instructions.

- Unauthorized charges or being charged after cancellation: billing, severity 4 unless
  a concrete financial loss is explicitly stated, then severity 5. Synthetic example:
  "An unauthorized charge appeared; the money has not left my bank yet."
  billing / complaint / severity 4. Apply the contract's intent precedence separately.
- Account takeover by another person: access, severity 5 for privacy harm. Synthetic
  example: "A stranger took over my account and is reading my private profile."
  access / complaint / severity 5.
- Permanent library/playlist loss: severity 5 for data harm; temporarily missing items:
  severity 3. Choose the corresponding feature topic (playlist management usability,
  offline/download loss downloads). Synthetic example: "My playlists disappeared for
  ten minutes, then came back." usability / complaint / severity 3.
  Permanent-loss contrast: "All my saved playlists were permanently deleted."
  usability / complaint / severity 5.
- Non-English text: if understandable, assign supported labels and needs_review true;
  otherwise other / unclear / severity 1 / needs_review true. Synthetic example:
  "No puedo iniciar sesión en mi cuenta." access / complaint / severity 4 /
  needs_review true (understandable Spanish: cannot log in).

## Remaining label fields

sentiment: finite number from -1 (very negative) to 1 (very positive); 0 neutral/mixed.
Suggested ordered anchors: -1, -0.5, 0, 0.5, 1. Fractional values are allowed. This project
convention is separate from severity. Jev's five-level Score maps as score / 2 - 1.
Final evaluation tolerance is predeclared in config as 0.25; also report MAE.

entities: JSON array of explicitly mentioned product/feature names. Copy supported
terms conservatively, e.g. ["Premium"] or []; do not invent plan tier, account data or
customer facts. Entity substring matching is a project convention, not a checker rule.

evidence_quote: nonempty exact substring supporting the label. Copy spelling, accents,
spaces and embedded line breaks unchanged. Short reviews may use their entire text;
substring membership still needs separate human support inspection.

needs_review: lowercase true or false. Mark true for missing impact/topic context,
unclear interpretation, unsupported language or unresolved ambiguity. Evaluate this as
a prediction; it neither quarantines a record nor proves other labels correct.

## Hand-label the golden 50 safely

The supplied data/golden_50_to_label.csv remains unchanged. Edit only the separate
evals/golden_50_human.csv copy, using a UTF-8 text/CSV editor, never Excel. Preserve every
original column/value and review ID. Fill all seven label columns yourself. Do not
consult model predictions before labeling. CSV cells containing commas, quotes or
line breaks require quoting; inside quoted CSV cells double literal quotation marks.
For example, the cell value ["Premium"] is serialized as "[""Premium""]" in CSV.

Run `python -m pipeline validate-golden`. It checks all 50 IDs exactly once, unchanged
source fields, allowed labels, finite sentiment, integer severity, entity array,
boolean spelling and exact quote membership. Nonzero exit means work remains. It
writes an error report containing IDs and field errors, without suggesting labels.

Golden labels are evaluation-only: exclude them from prompts, prompt examples,
threshold tuning, routing and issue discovery. If results influence a later revision,
disclose the revision and obtain fresh held-out cases. The validator checks format and
provenance; you own semantic correctness and quote support.

Prefer `python -m pipeline label-golden` for an offline guided workflow. It shows only
one original review at a time, uses numbered topic/intent/severity menus, five sentiment
values, comma-separated entities, a full-text quote default (or an immediately validated
exact substring), and y/n for needs_review. Each complete review is saved atomically;
q at a prompt, Ctrl+C or EOF stops without saving an unfinished review. Resume with the
same command; already valid human labels are skipped. It never reads model output and
makes no network calls. If a process is forcibly killed, remove its .csv.lock file only
after verifying no labeler is running; normal exit removes the lock automatically.
