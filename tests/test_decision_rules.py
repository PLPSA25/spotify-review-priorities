"""The declared human guide and every model role preserve the approved harm rules."""

import json
from pathlib import Path

from pipeline.classify import jev_payload


def test_declared_rules_are_present_in_both_model_prompts() -> None:
    config = {"models": {"jev": "jev-1.13.0"}}
    payload = jev_payload("synthetic input", config)
    for question in payload["questions"].values():
        instructions = question["instructions"]
        assert "concrete financial loss" in instructions
        assert "Account takeover" in instructions
        assert "Permanent library/playlist loss" in instructions
        assert "Non-English" in instructions
    criteria = json.loads(Path("prompts/jev-v1.json").read_text())["questions"]
    assert "concrete financial loss" in criteria["topic"]["criteria"]["billing"]
    assert "takeover" in criteria["topic"]["criteria"]["access"]
    assert "temporary missing items 3" in criteria["topic"]["criteria"]["usability"]
    luna = Path("prompts/luna-enrich-v1.txt").read_text()
    assert "charged after cancelling" in luna
    assert "otherwise other/unclear/1" in luna


def test_four_question_prompt_states_declared_rules_once() -> None:
    import tomllib

    config = tomllib.loads(Path("config.toml").read_text())
    assert config["enrichment"]["jev_prompt"] == "jev-v2.json"
    candidate = jev_payload("synthetic input", config)
    assert set(candidate["questions"]) == {"topic", "intent", "severity", "sentiment"}
    assert json.dumps(candidate).count("concrete financial loss") == 1
    config["enrichment"]["jev_prompt"] = "jev-v1.json"
    original = jev_payload("synthetic input", config)
    assert len(json.dumps(candidate)) < len(json.dumps(original))
