import pytest

from pipeline.issue_cohorts_v2 import CROSS_ID, classify, cross_evidence


@pytest.mark.parametrize('phrase', ['non stop music', 'non-stop music', 'non–stop music', 'nonstop music', 'without stopping'])
def test_promised_continuous_listening_is_not_a_playback_stop(phrase):
    issue, _ = classify('playback', 'They promised thirty minutes of '+phrase)
    assert issue == 'playback--unspecified'


def test_protected_phrase_does_not_hide_a_later_actual_failure():
    issue, details = classify('playback', 'I wanted non stop music but the music stops every song.')
    assert issue == 'playback--stops-skips-wont-play'
    assert details['matched_text'] == 'stops'


@pytest.mark.parametrize('topic', ['usability', 'billing', 'playback', 'other'])
def test_control_gate_can_span_topics_without_relabeling_primary_topic(topic):
    issue, evidence = classify(topic, 'Playing in order is only available in premium now.')
    assert issue == CROSS_ID
    assert evidence['premium_lock_is_explicit']


def test_premium_mention_alone_and_skip_ads_are_not_control_evidence():
    assert cross_evidence('Premium is expensive and I dislike it.') is None
    assert cross_evidence('I need premium to skip ads.') is None
    assert cross_evidence('I need premium for skipping ads.') is None
    assert cross_evidence('I pay for premium but playback crashes.') is None


def test_owner_update_and_forced_control_examples_are_explicitly_marked_inferred():
    issue, evidence = classify('usability', "Cant unshuffle my playlist, cant go back to previous song and cant seek.")
    assert issue == CROSS_ID
    assert evidence['evidence_tier'] == 'inferred_forced_shuffle'
    assert not evidence['premium_lock_is_explicit']
    issue, evidence = classify('usability', 'The new update means I cannot go to the previous song.')
    assert issue == CROSS_ID
    assert evidence['evidence_tier'] == 'inferred_update_control_restriction'


def test_paid_customer_without_a_paywall_link_is_not_assumed_free_tier():
    issue, _ = classify('playback', 'I have premium and after this update I cannot seek or go to the previous song.')
    assert issue != CROSS_ID


def test_algorithm_repetition_is_not_forced_shuffle_mode():
    assert cross_evidence('Algorithm only shuffles songs based on lowest cost per play. The shuffle recommendations are bad.') is None
    assert cross_evidence('I always liked shuffle but now the ads are too much.') is None


def test_conditional_not_buying_premium_is_explicit_evidence():
    evidence = cross_evidence('Cannot turn off shuffle if you do not buy premium.')
    assert evidence['premium_lock_is_explicit']


def test_supplied_checker_allows_a_single_issue_to_span_primary_topics(tmp_path):
    from pathlib import Path

    from pipeline.enrich import write_jsonl
    from pipeline.labeler import atomic_csv
    from pipeline.prepare import atomic_json, course_helper
    from pipeline.rank import aggregate
    from tests.test_enrichment import environment, record

    source, _, state, _, _ = environment(tmp_path, ('Forced shuffle on free tier.', 'Need Premium to play in order.'))
    helper = course_helper(Path('data/check_submission.py'))
    sources = list(helper.csv_rows(source))
    records = []
    for n, row in enumerate(sources):
        row['source_sha256'] = helper.row_sha(row)
        result = record(row, state.label_config)
        result.update(topic=('usability', 'billing')[n], intent='complaint', severity=n+2)
        records.append(result)
    membership, ranking, claims = aggregate(records, lambda _: CROSS_ID)
    folder = tmp_path/'submission'
    folder.mkdir()
    atomic_json(folder/'run.json', {'version': 'a5-audit-v1', 'analysis_count': 2,
                                  'analysis_sha256': helper.sha(source), 'classification_input_fields': ['review_text'],
                                  'allow_multi_issue': False})
    atomic_json(folder/'ingestion.json', helper.profile(source))
    write_jsonl(folder/'records.jsonl', records)
    atomic_csv(folder/'membership.csv', ['issue_id', 'review_id'], membership)
    atomic_csv(folder/'ranking.csv', ['rank', 'issue_id', 'complaint_count', 'severity_sum', 'mean_severity', 'priority_score'], ranking)
    atomic_csv(folder/'claims.csv', ['claim_id', 'issue_id', 'metric', 'value'], claims)
    atomic_json(folder/'checkpoint_before.json', {'completed_ids': ['0']})
    atomic_json(folder/'checkpoint_after.json', {'completed_ids': ['0', '1']})
    events = [{'request_id': 'synthetic-'+str(n), 'role': 'enrich', 'review_ids': [str(n)],
               'model': 'synthetic-offline', 'phase': 'initial' if n == 0 else 'resume', 'outcome': 'succeeded',
               'label_config': state.label_config, 'input_tokens': 1, 'output_tokens': 1} for n in range(2)]
    events += [{'request_id': 'synthetic-'+role, 'role': role, 'review_ids': [], 'model': 'synthetic-offline',
                'phase': 'initial', 'outcome': 'succeeded', 'input_tokens': 1, 'output_tokens': 1}
               for role in ('verify', 'group', 'memo')]
    write_jsonl(folder/'calls.jsonl', events)
    checked = helper.audit(folder, helper.reference(source, source))
    assert checked['status'] == 'pass', checked['issue_counts']
    assert checked['calculated_ranking'][0]['complaint_count'] == 2
    assert checked['calculated_ranking'][0]['severity_sum'] == 5
