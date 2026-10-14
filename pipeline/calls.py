"""One auditable dispatch path for reservations, rate limits, usage and retries."""

import copy
import random
import time
import uuid
from collections.abc import Callable
from threading import Event
from typing import Any

from pipeline.providers import ProviderError, Transport
from pipeline.schema import canonical
from pipeline.spend import Ledger, SpendStop, token_cost
from pipeline.state import ConfigMismatch, State


class InvalidOutput(ValueError):
    """Output remained invalid after the single repair attempt."""


class Calls:
    def __init__(self, state: State, ledger: Ledger, transport: Transport,
                 config: dict[str, Any], run_id: str, phase: str, simulated: bool = False,
                 sleep: Callable[[float], None] = time.sleep,
                 jitter: Callable[[], float] = random.random) -> None:
        self.state, self.ledger, self.transport, self.config = state, ledger, transport, config
        self.run_id, self.phase, self.simulated = run_id, phase, simulated
        self.fallback_scope = str(state.path.resolve()) + ":" + state.label_config
        self.sleep, self.jitter = sleep, jitter
        self.stop = Event()

    def invoke(self, provider: str, payload: dict[str, Any], ids: list[str], stage: str,
               parse: Callable[[dict[str, Any]], dict[str, Any]], role: str = "enrich",
               prompt_version: str | None = None, schema_version: str = "record-v1") -> dict[str, Any]:
        if role not in {"enrich", "verify", "group", "memo"}:
            raise ValueError("Unsupported model role")
        minimum = 1 if role in {"enrich", "verify"} else 0
        if not minimum <= len(ids) <= 50 or len(ids) != len(set(ids)):
            raise ValueError("Bounded roles require valid unique input review IDs")
        with self.state.connect() as db:
            if any(not db.execute("SELECT 1 FROM reviews WHERE review_id=?", (rid,)).fetchone() for rid in ids):
                raise ValueError("Foreign call review ID")
        controls, rates = self.config["controls"], self.config["planning_rates"]
        previous = self.state.events_for(ids[0], stage) if ids else []
        attempt = max((event["attempt"] for event in previous), default=0)
        malformed = sum(str(event.get("error", "")).startswith("Invalid output:") for event in previous)
        transient = sum(str(event.get("error", "")) in {"HTTP 429", "HTTP 529", "429"} for event in previous)
        if malformed > controls["invalid_output_retries"]:
            raise InvalidOutput("Persisted invalid-output retry limit reached")
        if transient >= controls["max_transient_attempts"]:
            raise ProviderError("Persisted transient retry limit reached", transient=True,
                                known_uncharged=True)
        payload = copy.deepcopy(payload)
        while True:
            if self.stop.is_set():
                raise SpendStop("Admission stopped by another worker")
            attempt += 1
            request_id = str(uuid.uuid4())
            # Conservative byte-based token envelope, plus editable protocol overhead.
            tokens = len(canonical(payload).encode("utf-8")) + controls["token_overhead_bound"]
            output_bound = 0 if provider == "typesafe" else payload["max_output_tokens"]
            reservation = token_cost(tokens, output_bound, rates, provider)
            if provider == "openai":
                # Reserve potential write pricing too; measured caching savings come later.
                worst_rates = dict(rates)
                worst_rates["luna_input_per_million"] = max(
                    rates["luna_input_per_million"], rates["luna_cache_write_per_million"])
                reservation = token_cost(tokens, output_bound, worst_rates, provider)
            limits = self.config["rate_limits"][provider]
            limits = dict(limits)
            if provider == "typesafe":
                limits.update(rps=controls["jev_requests_per_second"],
                              tps=controls["jev_input_tokens_per_second"])
            while True:
                if self.stop.is_set():
                    raise SpendStop("Admission stopped while waiting for rate capacity")
                delay = self.ledger.admit(provider, tokens, **limits)
                if not delay:
                    break
                self.sleep(min(delay, 1.0))
            self.ledger.reserve(request_id, self.run_id, reservation, controls["run_api_cap_usd"])
            if self.stop.is_set():
                self.ledger.settle(request_id, 0, "cancelled_before_dispatch")
                raise SpendStop("Admission stopped before dispatch")
            event: dict[str, Any] = {
                "request_id": request_id, "run_id": self.run_id, "role": role, "stage": stage,
                "review_ids": ids, "provider": provider, "model": payload["model"],
                "phase": self.phase, "outcome": "failed", "label_config": self.state.label_config,
                "input_tokens": None, "output_tokens": None, "attempt": attempt,
                "prompt_version": prompt_version or ("jev-v1" if provider == "typesafe" else "luna-enrich-v1"),
                "schema_version": schema_version, "settings": self.config["models"],
                "service_tier_requested": payload.get("service_tier", "standard"),
                "service_tier": None, "simulated": self.simulated,
                "reservation_nanodollars": reservation, "accounting": "unknown_charge",
                "error": "dispatch_started_outcome_unresolved", "request": payload,
            }
            self.state.save_call(event)
            started = time.monotonic()
            response: dict[str, Any] | None = None
            settled = False
            try:
                response = self.transport.request(provider, payload)
                event["response"] = response
                self.state.save_call(event)  # durable response before usage settlement/interpretation
                event["model"] = response.get("model", "")
                event["provider_request_id"] = response.get("id")
                event["service_tier"] = response.get("service_tier", "standard" if provider == "typesafe" else None)
                usage = response.get("usage", {})
                inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
                if any(type(value) is not int or value < 0 for value in (inputs, outputs)):
                    raise ProviderError("Usage unavailable/invalid; reservation retained", unknown_charge=True)
                event.update(input_tokens=inputs, output_tokens=outputs)
                actual = token_cost(inputs, outputs, rates, provider)
                event.update(cost_nanodollars=actual, accounting="calculated_standard_no_cache_savings")
                self.ledger.settle(request_id, actual, event["accounting"])
                settled = True
                event["reservation_settled"] = True
                self.state.save_call(event)
                if self.ledger.totals()["spent_nanodollars"] > self.ledger.cap:
                    raise SpendStop("Provider-reported charges exceed the project cap; reconcile immediately")
                if not isinstance(event["model"], str) or not event["model"]:
                    raise ConfigMismatch("Response omitted exact model string")
                if provider == "typesafe" and event["model"] != self.config["models"]["jev"]:
                    raise ConfigMismatch("Requested Jev version unavailable or returned model changed")
                self.state.observed_model(provider, event["model"])
                if provider == "openai" and event["service_tier"] not in {"default", "standard"}:
                    raise SpendStop("Billed service tier missing/changed; stop to reconcile rates")
                result = parse(response)
                event.update(outcome="succeeded", error=None)
                return result
            except ProviderError as exc:
                event["error"] = str(exc)
                if exc.known_uncharged:
                    self.ledger.settle(request_id, 0, "provider_rejection_no_inference")
                    settled = True
                    event["accounting"] = "provider_rejection_no_inference"
                if exc.unknown_charge:
                    event["accounting"] = "unknown_charge_reservation_retained"
                    raise
                transient += 1
                if not exc.transient or transient >= controls["max_transient_attempts"]:
                    raise
                self.sleep(min(controls["backoff_max_seconds"],
                               controls["backoff_base_seconds"] * 2 ** (transient - 1)
                               + self.jitter() * controls["backoff_jitter_seconds"]))
            except (ValueError, KeyError, TypeError) as exc:
                if isinstance(exc, ConfigMismatch):
                    event["error"] = str(exc)
                    raise
                event["error"] = "Invalid output: " + str(exc)
                malformed += 1
                if malformed > controls["invalid_output_retries"]:
                    raise InvalidOutput(event["error"]) from None
                if provider == "typesafe":
                    payload["state"]["validation_error"] = event["error"]
                else:
                    payload["input"] += "\nVALIDATION_ERROR: " + event["error"]
            finally:
                if response is None and not settled:
                    event["accounting"] = "unknown_charge_reservation_retained"
                event["latency_seconds"] = time.monotonic() - started
                event["reservation_settled"] = settled
                self.state.save_call(event)
