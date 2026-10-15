from pipeline.issue_preview import issue_id, preview


def test_subissues_stay_inside_primary_topic_with_deterministic_first_mention():
    assert issue_id('usability', 'Ads interrupt my playlist') == 'usability--ad-interruptions'
    assert issue_id('usability', 'My playlist breaks and ads annoy me') == 'usability--queue-playlist-controls'
    assert issue_id('playback', 'Premium customer, music crashes') == 'playback--crashes-freezes'
    assert issue_id('other', 'Ads and premium') == 'other--unspecified'
    assert issue_id('catalog', 'nothing specific') == 'catalog--unspecified'


def test_preview_excludes_noncomplaints_and_golden_text_examples():
    rows = [{'review_id': 'a', 'topic': 'playback', 'intent': 'complaint', 'severity': 4},
            {'review_id': 'b', 'topic': 'playback', 'intent': 'cancellation', 'severity': 3},
            {'review_id': 'c', 'topic': 'other', 'intent': 'praise', 'severity': 1}]
    sources = {rid: {'review_text': text} for rid, text in [('a', 'crashes'), ('b', 'crashes often'), ('c', 'nice')]}
    result = preview(rows, sources, {'crashes'})
    assert result == [{'rank': 1, 'issue_id': 'playback--crashes-freezes', 'size': 2,
                       'severity_sum': 7, 'example_review_ids': ['b']}]
    assert result == preview(list(reversed(rows)), sources, {'crashes'})
