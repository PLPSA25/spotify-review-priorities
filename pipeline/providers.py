"""Explicit HTTP transports, with no hidden retries or calls on import."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, transient: bool = False, unknown_charge: bool = False,
                 known_uncharged: bool = False) -> None:
        super().__init__(message)
        self.transient, self.unknown_charge = transient, unknown_charge
        self.known_uncharged = known_uncharged


class Transport(Protocol):
    def request(self, provider: str, payload: dict[str, Any]) -> dict[str, Any]: ...


def reject_nonfinite(value: str) -> None:
    raise ValueError("Non-finite provider JSON")


def keys_from_env(path: Path) -> dict[str, str]:
    """Never print/log/echo values; keys are supplied only by the human's local file."""
    if not path.is_file():
        raise ValueError("Create .env yourself with OPENAI_API_KEY and TYPESAFE_API_KEY")
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"OPENAI_API_KEY", "TYPESAFE_API_KEY"}:
            values[key.strip()] = value.strip().strip("\"'")
    for name in ("OPENAI_API_KEY", "TYPESAFE_API_KEY"):
        values[name] = os.environ.get(name, values.get(name, ""))
        if not values[name]:
            raise ValueError("Set OPENAI_API_KEY and TYPESAFE_API_KEY in your local .env yourself")
    return values


class HTTPTransport:
    def __init__(self, keys: dict[str, str], timeout: float) -> None:
        self.keys, self.timeout = keys, timeout

    def request(self, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        if provider == "typesafe":
            url, name = "https://api.typesafe.ai/v1/systemone", "TYPESAFE_API_KEY"
        elif provider == "openai":
            url, name = "https://api.openai.com/v1/responses", "OPENAI_API_KEY"
        else:
            raise ValueError("Provider not on allowlist")
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Authorization": "Bearer " + self.keys[name],
                                                  "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"), parse_constant=reject_nonfinite)
                if not isinstance(result, dict):
                    raise TypeError("Provider response is not an object")
                result["_headers"] = {key: value for key, value in response.headers.items()
                                      if key.lower().startswith(("x-ratelimit-", "x-request-id"))}
                return result
        except urllib.error.HTTPError as exc:
            # Do not log response bodies: upstream errors can echo confidential inputs.
            code = exc.code
            raise ProviderError(f"HTTP {code}", transient=code in {429, 500, 502, 503, 529},
                                known_uncharged=code in {401, 403, 404, 422, 429, 529},
                                unknown_charge=code not in {401, 403, 404, 422, 429, 529}) from None
        except (TimeoutError, urllib.error.URLError):
            raise ProviderError("Timeout/connection outcome unknown; reconcile before retry",
                                unknown_charge=True) from None
        except (ValueError, TypeError, UnicodeError):
            raise ProviderError("Unreadable provider response; charge unknown",
                                unknown_charge=True) from None


class MockTransport:
    """Only for explicit simulated runs; never use its outputs as grading predictions."""
    def request(self, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
        if provider == "openai":
            name = payload.get("text", {}).get("format", {}).get("name")
            if name in {"issue_names", "pilot_memo"}:
                data = json.loads(payload["input"])
                if name == "issue_names":
                    result = {"issues": [{"issue_id": row["issue_id"], "name": row["issue_id"].replace("issue-", "")} for row in data["issues"]]}
                else:
                    priority = data["ranking"][0]["issue_id"] if data["ranking"] else ""
                    result = {"priority_issue": priority, "recommendation": "Review the observed evidence before choosing product work.",
                              "alternatives": ["Compare other categories."], "limitations": "Historical pilot evidence has limited coverage.",
                              "claim_ids": [row["claim_id"] for row in data["claims"] if row["issue_id"] == priority],
                              "review_ids": [row["review_id"] for row in data["evidence"] if row["issue_id"] == priority]}
                return {"model": payload["model"], "service_tier": "default", "status": "completed",
                        "usage": {"input_tokens": 100, "output_tokens": 20},
                        "output": [{"content": [{"type": "output_text", "text": json.dumps(result)}]}], "_simulated": True}
            packed = payload["input"].split("BEGIN_UNTRUSTED_REVIEWS_JSON\n", 1)[1].split(
                "\nEND_UNTRUSTED_REVIEWS_JSON", 1)[0]
            items = json.loads(packed)
            records = []
            for item in items:
                result = {"review_id": item["review_id"], "entities": [],
                          "evidence_quote": item["review_text"]}
                if "extraction-only" not in payload["input"].splitlines()[0]:
                    result.update(topic="other", intent="unclear", sentiment=0, severity=1,
                                  needs_review=False)
                records.append(result)
            return {"model": payload["model"], "service_tier": "default", "status": "completed",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                    "output": [{"content": [{"type": "output_text", "text": json.dumps(
                        {"records": records}, ensure_ascii=False)}]}], "_simulated": True}
        if provider != "typesafe":
            raise ValueError("Unknown mock provider")
        answers = {}
        for name, question in payload["questions"].items():
            if question["type"] == "choice":
                choices = list(question["criteria"])
                selected = {"topic": "other", "intent": "unclear", "severity": "1",
                            "language": "english"}[name]
                answers[name] = {"type": "choice", "choice": selected, "confidence": 1.0,
                                 "probabilities": {x: float(x == selected) for x in choices}}
            elif question["type"] == "score":
                answers[name] = {"type": "score", "score": 2.0, "confidence": 1.0,
                                 "probabilities": {str(i): float(i == 2) for i in range(5)}}
            else:
                answers[name] = {"type": "noul", "noul": 0.0}
        return {"model": payload["model"], "answers": answers,
                "usage": {"input_tokens": 100, "output_tokens": 20}, "_simulated": True}
