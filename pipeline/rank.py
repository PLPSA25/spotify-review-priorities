"""Deterministic baseline and claim IDs; no provider calls."""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def aggregate(records: list[dict[str, Any]], issue_for=None) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    members = []
    severity = defaultdict(list)
    for record in records:
        if record["intent"] not in {"complaint", "cancellation"}:
            continue
        issue = issue_for(record) if issue_for else "issue-" + record["topic"]
        members.append({"issue_id": issue, "review_id": record["review_id"]})
        severity[issue].append(record["severity"])
    ordered = sorted(severity, key=lambda issue: (-sum(severity[issue]), issue))
    ranking, claims = [], []
    for position, issue in enumerate(ordered, 1):
        count, total = len(severity[issue]), sum(severity[issue])
        row = {"rank": str(position), "issue_id": issue, "complaint_count": str(count),
               "severity_sum": str(total), "priority_score": str(total),
               "mean_severity": str((Decimal(total) / Decimal(count)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))}
        ranking.append(row)
        for metric in ("complaint_count", "severity_sum", "mean_severity", "priority_score"):
            claims.append({"claim_id": issue + ":" + metric, "issue_id": issue, "metric": metric, "value": row[metric]})
    return members, ranking, claims
