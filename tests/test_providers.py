"""HTTP request shape and secret handling using a mocked urlopen boundary."""

import json
from pathlib import Path

import pytest

from pipeline.providers import HTTPTransport, ProviderError, keys_from_env


def test_keys_checked_without_echo(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    missing = tmp_path / ".env"
    with pytest.raises(ValueError):
        keys_from_env(missing)
    missing.write_text("OPENAI_API_KEY=synthetic-only\nTYPESAFE_API_KEY=also-synthetic\n")
    assert keys_from_env(missing)["OPENAI_API_KEY"] == "synthetic-only"
    assert capsys.readouterr().out == ""


def test_http_transport_no_hidden_retries(monkeypatch) -> None:
    requests = []

    class Reply:
        def __init__(self):
            self.headers = {"x-request-id": "test-id", "secret-other-header": "do-not-save"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({"model": "jev-1.13.0"}).encode()

    def fake_open(request, timeout):
        requests.append(request)
        assert request.full_url == "https://api.typesafe.ai/v1/systemone"
        return Reply()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    result = HTTPTransport({"TYPESAFE_API_KEY": "synthetic-key"}, 60).request("typesafe", {"model": "jev-1.13.0"})
    assert len(requests) == 1
    assert result["_headers"] == {"x-request-id": "test-id"}
    assert "synthetic-key" not in json.dumps(result)


def test_unreadable_reply_has_unknown_charge(monkeypatch) -> None:
    class Reply:
        def __init__(self):
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"not-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Reply())
    with pytest.raises(ProviderError) as caught:
        HTTPTransport({"TYPESAFE_API_KEY": "synthetic-key"}, 60).request("typesafe", {})
    assert caught.value.unknown_charge
