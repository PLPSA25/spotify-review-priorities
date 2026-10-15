"""Offline v2 proposal: cross-topic playback controls, with explicit evidence tiers.

Primary classifications never change. Specific controls are required; Premium by
itself never selects this issue. Inferred tier attribution is visible for review.
"""
import re

from pipeline.issue_preview import RULES
from pipeline.schema import digest

CROSS_ID = 'cross-topic--free-tier-premium-controls'
CROSS_NAME = 'Free-tier playback controls locked behind Premium'
CONTROL_RULES = {
    'shuffle': r'\b(?:un)?shuffl\w*',
    'play-order-selection': r'\bin\s+(?:(?:the|my|any|a|an|desired|specific)\s+)?order\b(?!\s+to\b)|\border\s+(?:i|we|you|they)\b|\b(?:play|playing|choose|select)\s+(?:any|my|a|the|specific)\s+(?:own\s+)?(?:song|track)\b',
    'previous-back': r'\bprev(?:ious)?\b|\b(?:go|going|switch|swith|skip|song|track)\b.{0,18}\bback\b|\bback\s+(?:button|song|track)\b',
    'repeat-loop': r'\brepeat\w*|\bloop\w*',
    'skip-forward': r'\bskip\w*\b(?!\s+(?:ads?|advert\w*)\b)|\bforward(?:ing)?\b',
    'seek-rewind-parts': r'\bseek\w*|\brewind\w*|\b(?:specific|favourite|favorite)\s+parts?\s+(?:of|in)\s+(?:(?:a|the|any)\s+)?(?:song|track)\b|\b(?:progress|seek)\s+bar\b|\bfast[ -]?forward\w*',
    # Owner-supplied paraphrases from Price #2/#3. These are marked separately;
    # they are less precise than a named control, and never match Premium alone.
    'basic-player-control-paraphrase': r'\bbasic\s+(?:features|functions|purposes|controls)\b.{0,45}\bmusic\s+player\b|\b(?:stream|play|listen\s+to)\s+music\s+the\s+way\b',
}
PAYWALL_RULE = (
    r'\b(?:need|needs|require\w*|have\s+to|must|forced\s+to|asking\s+to|pushing|locked|upgrade\w*)\b.{0,90}\b(?:premium|upgrad\w*|subscrib\w*|pay\w*|paid)\b'
    r'|\b(?:premium|paid)\b.{0,55}\b(?:only|exclusive|features?|tasks?|facilit\w*|restrict\w*|unlock\w*|requir\w*|membership)\b'
    r'|\b(?:only|unless|without)\b.{0,65}\b(?:premium|paid|pay|upgrade)\b'
    r'|\bpay\w*\b.{0,30}\b(?:for|to|in\s+order)\b.{0,70}\b(?:basic|features?|controls?|listen|play|stream|song|music)\b'
    r'|\b(?:everything|features?|controls?|functions?|song\s+(?:forwarding|skipping))\b.{0,55}\b(?:premium|paywall|paid)\b'
    r"|\bif\b.{0,25}\b(?:not|don[’']t)\s+(?:buy|have|pay)\b.{0,25}\bpremium\b"
)
DENIAL_RULE = r"\b(?:can[’']?t|cannot|cant|unable|not\s+able|not\s+allowed|won[’']?t\s+let|no\s+longer|removed|taken\s+away|took\s+away|lost|forced|ruined)\b|\bno\s+(?:skip\w*|repeat|previous|shuffle|order)\b"
UPDATE_RULE = r'\b(?:updat\w*|used\s+to|before|now|anymore|no\s+longer|bring\s+back|removed|new\s+version|latest\s+version)\b'
FREE_RULE = r'\bfree\b|\bnon[ -]?premium\b|\bwithout\s+premium\b'
PAID_CUSTOMER_RULE = r"\b(?:i|we)\s+(?:already\s+)?(?:have|had|pay\s+for|paid\s+for|bought)\s+(?:a\s+)?(?:premium|subscription)|\b(?:i[’']?m|i\s+am|as\s+a)\s+(?:a\s+)?(?:premium|paying)\b|\bpremium\s+(?:account|customer|user|subscriber)\b"
FORCED_SHUFFLE_RULE = (
    r'\b(?:force\w*|stuck)\b.{0,50}\bshuffl\w*'
    r'|\b(?:always|only)\s+(?:(?:on|in|with)\s+)?shuffle\b'
    r'|\bonly\s+(?:play|playing|listen|listening)\s+(?:on\s+|in\s+)?shuffle\b'
    r'|\bput\w*\b.{0,50}\b(?:all|every|your|my)\b.{0,35}\b(?:playlists?|songs?)\b.{0,25}\b(?:on|in|to)\s+shuffle\b'
    r"|\b(?:can[’']?t|cant|cannot|unable)\b.{0,25}\b(?:unshuffle|(?:turn|switch).{0,15}off.{0,15}shuffle)\b"
    r"|\bshuffle\b.{0,30}\b(?:always\s+on|only\s+option|forced|can[’']?t\s+turn\s+off|cant\s+turn\s+off)\b"
)
PROTECTED_STOP_PREFIX = r"\b(?:non[\s\-‐‑‒–—]*|without\s+|never\s+|does\s+not\s+|doesn[’']t\s+|will\s+not\s+|won[’']t\s+)$"
VERSION = 'cross-topic-controls-v2-proposed'
RULE_HASH = digest({'version': VERSION, 'base': RULES, 'controls': CONTROL_RULES,
                    'paywall': PAYWALL_RULE, 'denial': DENIAL_RULE, 'update': UPDATE_RULE,
                    'free': FREE_RULE, 'paid_customer': PAID_CUSTOMER_RULE,
                    'forced_shuffle': FORCED_SHUFFLE_RULE, 'protected_stop': PROTECTED_STOP_PREFIX,
                    'precedence': ['cross-topic-controls', 'earliest-unprotected-within-topic', 'unspecified'],
                    'nearby_characters': 180})


def matches(pattern, text):
    return list(re.finditer(pattern, text, re.IGNORECASE))


def near(a, b):
    return max(0, max(a.start(), b.start())-min(a.end(), b.end())) <= 180


def cross_evidence(text):
    controls = [(kind, hit) for kind, pattern in CONTROL_RULES.items() for hit in matches(pattern, text)]
    # Backtracking in \w* must not turn "skip ads" into a partial control token.
    controls = [(kind, hit) for kind, hit in controls if not (kind == 'skip-forward' and
                re.match(r'\s+(?:ads?|advert\w*)\b', text[hit.end():], re.IGNORECASE))]
    if not controls:
        return None
    gates, denials = matches(PAYWALL_RULE, text), matches(DENIAL_RULE, text)
    paid = bool(matches(PAID_CUSTOMER_RULE, text))
    tier, signal = None, None
    matching_gate = next((gate for gate in gates if any(near(control, gate) for _, control in controls)), None)
    if matching_gate:
        tier, signal = 'explicit_paywall_or_premium_link', matching_gate.group()
    elif not paid and any(near(control, free) and near(control, denied)
                          for _, control in controls for free in matches(FREE_RULE, text) for denied in denials):
        tier, signal = 'free_tier_control_restriction', denials[0].group()
    elif not paid and denials and matches(UPDATE_RULE, text) and any(near(control, denied) for _, control in controls for denied in denials):
        tier, signal = 'inferred_update_control_restriction', denials[0].group()
    elif not paid and matches(FORCED_SHUFFLE_RULE, text):
        tier, signal = 'inferred_forced_shuffle', matches(FORCED_SHUFFLE_RULE, text)[0].group()
    elif not paid and len({kind for kind, _ in controls}) >= 2 and any(near(control, denied) for _, control in controls for denied in denials):
        tier, signal = 'inferred_multiple_controls_denied', denials[0].group()
    if tier is None:
        return None
    return {'evidence_tier': tier, 'control_families': sorted({kind for kind, _ in controls}),
            'control_matches': sorted({hit.group() for _, hit in controls}), 'restriction_match': signal,
            'premium_lock_is_explicit': tier == 'explicit_paywall_or_premium_link'}


def within_topic(topic, text):
    candidates, ignored = [], []
    for order, (name, pattern) in enumerate(RULES[topic]):
        for hit in matches(pattern, text):
            if topic == 'playback' and name == 'stops-skips-wont-play' and hit.group().lower().startswith('stop') and re.search(PROTECTED_STOP_PREFIX, text[max(0, hit.start()-25):hit.start()], re.IGNORECASE):
                ignored.append(hit.group())
                continue
            candidates.append((hit.start(), order, name, hit.group(), pattern))
            break
    if not candidates:
        return topic+'--unspecified', {'matched_rule': 'No unprotected specific match', 'ignored_continuity_matches': ignored}
    _, _, subissue, hit, pattern = min(candidates)
    return topic+'--'+subissue, {'matched_rule': pattern, 'matched_text': hit, 'ignored_continuity_matches': ignored}


def classify(topic, text):
    evidence = cross_evidence(text)
    if evidence is not None:
        return CROSS_ID, evidence
    return within_topic(topic, text)
