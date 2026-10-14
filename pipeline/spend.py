"""Shared SQLite spend reservations and rolling request/token admission."""

import math
import sqlite3
import time
from contextlib import closing, contextmanager
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

UNITS_PER_DOLLAR = 1_000_000_000


class SpendStop(RuntimeError):
    """Stop admission while preserving pending work."""


def money(value: str | float | Decimal) -> int:
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Cost/cap must be finite and nonnegative")
    return int((amount * UNITS_PER_DOLLAR).to_integral_value(rounding=ROUND_CEILING))


def token_cost(input_tokens: int, output_tokens: int, rates: dict[str, Any], provider: str) -> int:
    if any(type(x) is not int or x < 0 for x in (input_tokens, output_tokens)):
        raise ValueError("Token counts must be nonnegative integers")
    prefix = "jev" if provider == "typesafe" else "luna"
    cost = (Decimal(input_tokens) * Decimal(str(rates[prefix + "_input_per_million"]))
            + Decimal(output_tokens) * Decimal(str(rates[prefix + "_output_per_million"]))) / 1000000
    return money(cost)


def usage_cost(usage: dict[str, Any], rates: dict[str, Any], provider: str) -> int:
    inputs, outputs = usage["input_tokens"], usage["output_tokens"]
    base = token_cost(inputs, outputs, rates, provider)
    if provider == "typesafe":
        return base
    detail = usage.get("input_tokens_details", {})
    cached, writes = detail.get("cached_tokens", 0), detail.get("cache_write_tokens", 0)
    if any(type(value) is not int or value < 0 for value in (cached, writes)) or cached + writes > inputs:
        raise ValueError("Invalid mutually exclusive cached/write input usage")
    cost = (Decimal(inputs - cached - writes) * Decimal(str(rates["luna_input_per_million"]))
            + Decimal(cached) * Decimal(str(rates["luna_cached_input_per_million"]))
            + Decimal(writes) * Decimal(str(rates["luna_cache_write_per_million"]))
            + Decimal(outputs) * Decimal(str(rates["luna_output_per_million"]))) / 1000000
    return money(cost)


class Ledger:
    def __init__(self, path: Path, cap: float) -> None:
        self.path, self.cap = path, money(cap)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reservations(
                    id TEXT PRIMARY KEY,run_id TEXT NOT NULL,amount INTEGER NOT NULL,
                    spent INTEGER NOT NULL DEFAULT 0,state TEXT NOT NULL DEFAULT 'reserved',
                    accounting TEXT NOT NULL DEFAULT 'reserved');
                CREATE TABLE IF NOT EXISTS rate_events(
                    provider TEXT NOT NULL,at REAL NOT NULL,tokens INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS rate_time ON rate_events(provider,at);
                CREATE TABLE IF NOT EXISTS fallback_jobs(key TEXT PRIMARY KEY,run_id TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            yield db

    def totals(self) -> dict[str, int]:
        with self.connect() as db:
            spent, reserved = db.execute("SELECT COALESCE(SUM(spent),0),COALESCE(SUM("
                                         "CASE WHEN state='reserved' THEN amount ELSE 0 END),0) "
                                         "FROM reservations").fetchone()
        return {"spent_nanodollars": spent, "reserved_nanodollars": reserved}

    def reservation(self, request_id: str) -> tuple[int, str, int]:
        with self.connect() as db:
            row = db.execute("SELECT amount,state,spent FROM reservations WHERE id=?",
                             (request_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown reservation")
        return row

    def reserve(self, request_id: str, run_id: str, amount: int, run_cap: float) -> None:
        if type(amount) is not int or amount < 0:
            raise ValueError("Invalid reservation")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT COALESCE(SUM(spent + CASE WHEN state='reserved' "
                               "THEN amount ELSE 0 END),0) FROM reservations").fetchone()[0]
            run_total = db.execute("SELECT COALESCE(SUM(spent + CASE WHEN state='reserved' "
                                   "THEN amount ELSE 0 END),0) FROM reservations WHERE run_id=?",
                                   (run_id,)).fetchone()[0]
            if total + amount > self.cap or run_total + amount > money(run_cap):
                raise SpendStop("Spent + reserved + next reservation exceeds project/run cap")
            db.execute("INSERT INTO reservations(id,run_id,amount) VALUES (?,?,?)",
                       (request_id, run_id, amount))

    def settle(self, request_id: str, actual: int | None, accounting: str) -> None:
        # None means possibly billed: retain the worst-case reservation indefinitely.
        if actual is None:
            return
        if type(actual) is not int or actual < 0:
            raise ValueError("Invalid settled amount")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT amount,state,spent FROM reservations WHERE id=?",
                             (request_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown reservation")
            if row[1] != "reserved":
                raise ValueError("Reservation already settled")
            db.execute("UPDATE reservations SET spent=?,state='settled',accounting=? WHERE id=?",
                       (actual, accounting, request_id))
        if actual > row[0]:
            raise SpendStop("Actual usage exceeded conservative reservation; stop and reconcile")

    def allow_fallback(self, key: str, run_id: str, quota: int) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM fallback_jobs WHERE key=?", (key,)).fetchone():
                return True
            count = db.execute("SELECT COUNT(*) FROM fallback_jobs WHERE run_id=?", (run_id,)).fetchone()[0]
            if count >= quota:
                return False
            db.execute("INSERT INTO fallback_jobs VALUES (?,?)", (key, run_id))
            return True

    def admit(self, provider: str, tokens: int, rps: int, tps: int, rpm: int, tpm: int,
              now: float | None = None) -> float:
        """Reserve one request slot across processes; return wait instead of busy looping."""
        if type(tokens) is not int or tokens < 0 or min(rps, tps, rpm, tpm) < 1:
            raise ValueError("Invalid rate limits")
        if tokens > min(tps, tpm):
            raise SpendStop("One request exceeds configured token admission limit")
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM rate_events WHERE at<=?", (now - 60,))
            for window, request_limit, token_limit in ((1, rps, tps), (60, rpm, tpm)):
                rows = db.execute("SELECT at,tokens FROM rate_events WHERE provider=? AND at>? "
                                  "ORDER BY at", (provider, now - window)).fetchall()
                if len(rows) >= request_limit or sum(row[1] for row in rows) + tokens > token_limit:
                    return max(0.001, rows[0][0] + window - now)
            db.execute("INSERT INTO rate_events VALUES (?,?,?)", (provider, now, tokens))
        return 0.0


def fallback_quota(total_distinct: int, fraction: float) -> int:
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Invalid fallback fraction")
    return math.floor(total_distinct * fraction)
