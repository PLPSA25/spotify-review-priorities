import pytest

from pipeline.issue_cohorts_v3 import CROSS_ID, classify, cross_evidence


@pytest.mark.parametrize('text', [
    "I can't even listen when there is shuffle. I want to pick my song.",
    "You changed playing songs in any order. This shuffle mode is not acceptable.",
    "Whenever I pick a song it puts on a different one and I can't press shuffle.",
    "We don't listen song in play in order and shuffle. Bad update.",
    "If you have not paid it doesn't allow you to go to the previous song.",
    "You need to buy subscription even for rewinding the song.",
    "Now you can't listen to your favourite parts of songs.",
    "When I play a specific song the app plays another and I can't get rid of it.",
    "There isn't an option to loop a song or play the playlist in order.",
    "I search a song and hit play it randomly gives me something else.",
    "When I press the play button it plays another song.",
    "I wish you could skip as many times as you like and play playlists not just shuffled.",
])
def test_owner_recall_error_forms_are_included_without_changing_topic(text):
    assert classify('other', text)[0] == CROSS_ID


@pytest.mark.parametrize('text', [
    'Premium is expensive.', 'Please buy premium.', 'Need to buy a subscription.',
    'I need premium to skip ads.', 'I want thirty minutes of non-stop music.',
    'I like shuffle and repeat; the app is good.',
])
def test_control_and_restriction_are_both_required(text):
    assert cross_evidence(text) is None


def test_frozen_paid_customer_exclusion_remains_for_inferred_restrictions():
    assert cross_evidence('I have premium and cannot seek this song.') is None
