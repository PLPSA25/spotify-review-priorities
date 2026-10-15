"""Proposed deterministic topic/sub-issue taxonomy; offline preview, not membership.

Rules are fixed independently of golden answers. A first lexical mention within the
already-frozen primary topic chooses a sub-issue; residuals remain unspecified.
"""
import hashlib
import re
from collections import Counter

from pipeline.schema import digest

# Stable rule order breaks equal-position matches only. No primary label is changed.
RULES = {
    'access': [
        ('account-security', r'\bhack\w*|\bstolen\b|\bsuspicious\b'),
        ('login-credentials', r'\blog[ -]?(?:in|out)\b|\bsign[ -]?in\b|\bpassword\b|\blogging\b'),
        ('signup-registration', r'\bsign[ -]?up\b|\bregister\w*|\bregistration\b|\bcreat\w*\s+(?:an?\s+)?account\b'),
        ('account-restrictions', r'\b(?:account|profile)\b.{0,30}\b(?:blocked|disabled|suspended|locked|deleted)\b'),
    ],
    'usability': [
        ('ad-interruptions', r'\bads?\b|\badvert\w*|\bcommercials?\b'),
        ('shuffle-controls', r'\bshuffle\w*|\brepeat\b'),
        ('queue-playlist-controls', r'\bqueue\b|\bplaylist\w*|\bliked songs\b'),
        ('interface-navigation', r'\b(?:ui|ux|interface|layout|navigation|buttons?|menus?|widgets?)\b|\bredesign\w*'),
    ],
    'playback': [
        ('crashes-freezes', r'\bcrash\w*|\bfreez\w*|\bfrozen\b|\bforce clos\w*'),
        ('buffering-connectivity', r'\bbuffer\w*|\blag\w*|\bconnection\b|\bconnectivity\b|\bload\w*|\binternet\b'),
        ('audio-quality-volume', r'\b(?:audio|sound) quality\b|\bvolume\b|\bdistort\w*|\bequaliz\w*|\bbluetooth\b'),
        ('background-resources', r'\bbackground\b|\bbattery\b|\bmemory\b|\boverheat\w*|\bscreen (?:off|lock)\b'),
        ('stops-skips-wont-play', r'\b(?:stop|paus|skip)\w*|\b(?:won.t|can.t|cannot|doesn.t|not|no longer)\s+play\w*|\bplay\w*\s+(?:anything|nothing)\b'),
    ],
    'downloads': [
        ('missing-downloads', r'\bdisappear\w*|\bmissing\b|\bdeleted\b|\bremoved\b|\blost\b'),
        ('offline-access', r'\boffline\b|\bwithout (?:internet|wi[ -]?fi|data)\b'),
        ('download-failure', r'\bdownload\w*'),
    ],
    'catalog': [
        ('lyrics', r'\blyrics?\b'),
        ('discovery-recommendations', r'\brecommend\w*|\bdiscover\w*|\b(?:daily|song|artist) mix\w*|\bradio\b'),
        ('search-results', r'\bsearch\w*|\bfind\w*'),
        ('availability-selection', r'\bmissing\b|\bunavailable\b|\bremoved\b|\bselection\b|\bvariety\b|\bcatalog\w*'),
    ],
    'billing': [
        ('charges-refunds', r'\bcharg\w*|\brefund\w*|\bpayment\w*|\bbill\w*|\bdouble\s+pa\w*'),
        ('premium-upgrade-mentions', r'\bpremium\b|\bactivat\w*|\bupgrad\w*|\bsubscrib\w*'),
        ('price-paywalls', r'\bpric\w*|\bcost\w*|\bexpensive\b|\bpaywall\w*|\bpay\w*'),
        ('subscription-cancellation', r'\bcancel\w*|\brenew\w*|\bsubscription\w*'),
    ],
    'support': [
        ('contact-response', r'\bcontact\w*|\brespond\w*|\bresponse\b|\brepl\w*|\bemail\w*|\bchat\w*'),
        ('resolution-quality', r'\bhelp\w*|\bresolv\w*|\bfix\w*|\bsupport\b'),
    ],
    'other': [],
}
VERSION = 'topic-subissue-lexical-v1-proposed'
RULE_HASH = digest({'version': VERSION, 'rules': RULES, 'selection': 'earliest-match-then-rule-order',
                    'fallback': 'unspecified', 'one_issue_per_completed_complaint': True})


def issue_id(topic, text):
    matches = []
    for order, (name, pattern) in enumerate(RULES[topic]):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matches.append((match.start(), order, name))
    subissue = min(matches)[2] if matches else 'unspecified'
    return f'{topic}--{subissue}'


def preview(records, sources, excluded_example_texts, fine=True):
    totals, sizes, examples = Counter(), Counter(), {}
    for record in records:
        if record['intent'] not in {'complaint', 'cancellation'}:
            continue
        rid, topic = record['review_id'], record['topic']
        text = sources[rid]['review_text']
        iid = issue_id(topic, text) if fine else topic
        totals[iid] += record['severity']
        sizes[iid] += 1
        if text not in excluded_example_texts:
            # A bounded, deterministic random pair of distinct exact-text examples.
            key = hashlib.sha256((VERSION + text).encode()).hexdigest()
            candidates = examples.setdefault(iid, {})
            if key not in candidates or rid < candidates[key]:
                candidates[key] = rid
            for extra in sorted(candidates)[2:]:
                del candidates[extra]
    return [{'rank': n, 'issue_id': iid, 'size': sizes[iid], 'severity_sum': totals[iid],
             'example_review_ids': [rid for _, rid in sorted(examples.get(iid, {}).items())]}
            for n, iid in enumerate(sorted(totals, key=lambda key: (-totals[key], key)), 1)]
