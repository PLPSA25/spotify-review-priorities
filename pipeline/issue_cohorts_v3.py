"""Final owner-requested recall refinement. Freeze before viewing v3 samples."""
import re

from pipeline import issue_cohorts_v2 as v2
from pipeline.schema import digest

CROSS_ID, CROSS_NAME = v2.CROSS_ID, v2.CROSS_NAME
CONTROL_RULES = dict(v2.CONTROL_RULES)
CONTROL_RULES['seek-rewind-parts'] = CONTROL_RULES['seek-rewind-parts'].replace('(?:song|track)\\b', '(?:songs?|tracks?)\\b')
CONTROL_RULES['play-order-selection'] += r'|\b(?:pick|picking|choose|choosing|select|selecting)\s+(?:a|the|my|any|specific)\s+(?:own\s+)?(?:song|track)\b'
CONTROL_RULES['previous-back'] += r'|\bplay\s+back\s+(?:a\s+|the\s+)?(?:song|track)\b'
SELECTION_SYMPTOM = (
    r'\b(?:pick\w*|choos\w*|select\w*|play|search\w*|press|hit)\b.{0,100}'
    r'\b(?:song|track|play\s+button)\b.{0,180}\b(?:plays?|puts?|gives?|takes?|taking)\b'
    r'.{0,45}\b(?:another|random\w*|different|something\s+else|other)\b'
)
CONTROL_RULES['selected-song-replaced'] = SELECTION_SYMPTOM
PAYWALL_EXTRA = (
    r'\b(?:need\w*|have\s+to|must|compel\w*)\b.{0,50}\b(?:buy|purchase|pay|paid)\b.{0,35}\b(?:premium|subscription|membership)\b'
    r'|\bif\b.{0,35}\b(?:have\s+not|haven[’\x27]t|not)\s+paid\b'
    r'|\bwithout\s+(?:premium|paying|payment|a\s+subscription)\b'
)
DENIAL_EXTRA = (
    r"\b(?:doesn[’']?t|don[’']?t|won[’']?t|does\s+not|do\s+not|will\s+not|not)\s+(?:even\s+)?(?:allow\w*|let\w*)\b"
    r"|\bnot\s+letting\b|\b(?:can[’']?t|cant|cannot|unable(?:\s+to)?)\b"
    r"|\b(?:isn[’']?t|is\s+not|no)\s+(?:an?\s+)?(?:option|way|button)\b"
    r"|\b(?:don[’']?t|do\s+not)\s+(?:listen|play|have|get)\b|\bnot\s+acceptable\b"
)
FREE_EXTRA = r'\bfree\s+(?:version|users?|tier|account|plan)\b'
FORCED_EXTRA = r'\bnot\s+just\s+shuffl\w*'
VERSION = 'cross-topic-controls-v3-final'
RULE_HASH = digest({'version': VERSION, 'v2_rule_hash': v2.RULE_HASH, 'controls': CONTROL_RULES,
                    'paywall_extra': PAYWALL_EXTRA, 'denial_extra': DENIAL_EXTRA,
                    'free_extra': FREE_EXTRA, 'forced_extra': FORCED_EXTRA,
                    'precedence': ['control-plus-explicit-gate', 'control-plus-free-restriction',
                                   'v2-supported-paths', 'control-plus-direct-denial', 'selected-song-replaced',
                                   'restricted-shuffle-contrast', 'within-topic'], 'nearby_characters': 180})


def cross_evidence(text):
    controls = [(kind, hit) for kind, pattern in CONTROL_RULES.items() for hit in v2.matches(pattern, text)]
    controls = [(kind, hit) for kind, hit in controls if not (kind == 'skip-forward' and
                re.match(r'\s+(?:ads?|advert\w*)\b', text[hit.end():], re.IGNORECASE))]
    if not controls:
        return None
    gates = v2.matches(v2.PAYWALL_RULE+'|'+PAYWALL_EXTRA, text)
    denials = v2.matches(v2.DENIAL_RULE+'|'+DENIAL_EXTRA, text)
    paid = bool(v2.matches(v2.PAID_CUSTOMER_RULE, text))
    gate = next((g for g in gates if any(v2.near(c, g) for _, c in controls)), None)
    if gate:
        tier, signal = 'explicit_paywall_or_premium_link', gate.group()
    elif not paid and any(v2.near(c, f) and v2.near(c, d) for _, c in controls
                          for f in v2.matches(v2.FREE_RULE+'|'+FREE_EXTRA, text) for d in denials):
        tier, signal = 'free_tier_control_restriction', denials[0].group()
    else:
        old = v2.cross_evidence(text)
        if old:
            return old
        denial = next((d for d in denials if any(v2.near(c, d) for _, c in controls)), None)
        symptom = v2.matches(SELECTION_SYMPTOM, text)
        forced = v2.matches(FORCED_EXTRA, text)
        if not paid and denial:
            tier, signal = 'inferred_direct_control_denial', denial.group()
        elif not paid and symptom:
            tier, signal = 'inferred_selected_song_replaced', symptom[0].group()
        elif not paid and forced:
            tier, signal = 'inferred_shuffle_restriction_contrast', forced[0].group()
        else:
            return None
    return {'evidence_tier': tier, 'control_families': sorted({kind for kind, _ in controls}),
            'control_matches': sorted({hit.group() for _, hit in controls}), 'restriction_match': signal,
            'premium_lock_is_explicit': tier == 'explicit_paywall_or_premium_link'}


def classify(topic, text):
    evidence = cross_evidence(text)
    return (CROSS_ID, evidence) if evidence else v2.within_topic(topic, text)
