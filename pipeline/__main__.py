"""Offline preparation/labeling and explicitly confirmed enrichment commands."""

import argparse
from pathlib import Path

from pipeline.enrich import run_enrichment
from pipeline.labeler import label_golden
from pipeline.labels import create_template, validate_golden
from pipeline.prepare import prepare
from pipeline.reconcile import reconcile_charge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    command = stages.add_parser("prepare", help="Verify and ingest CSV without model calls")
    command.add_argument("--input", type=Path, required=True)
    command.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    command.add_argument("--output", type=Path, default=Path("artifacts/ingestion"))
    command.add_argument("--config", type=Path, default=Path("config.toml"))
    template = stages.add_parser("golden-template", help="Create a blank human-label copy once")
    template.add_argument("--source", type=Path, default=Path("data/golden_50_to_label.csv"))
    template.add_argument("--output", type=Path, default=Path("evals/golden_50_human.csv"))
    validator = stages.add_parser("validate-golden", help="Validate human labels offline")
    validator.add_argument("--input", type=Path, default=Path("evals/golden_50_human.csv"))
    validator.add_argument("--source", type=Path, default=Path("data/golden_50_to_label.csv"))
    validator.add_argument("--report", type=Path, default=Path("evals/golden_validation.json"))
    labeler = stages.add_parser("label-golden", help="Interactively hand-label reviews offline")
    labeler.add_argument("--source", type=Path, default=Path("data/golden_50_to_label.csv"))
    labeler.add_argument("--output", type=Path, default=Path("evals/golden_50_human.csv"))
    labeler.add_argument("--report", type=Path, default=Path("evals/golden_validation.json"))
    enrich = stages.add_parser("enrich", help="Enrich with explicit mock or confirmed paid mode")
    enrich.add_argument("--input", type=Path, required=True)
    enrich.add_argument("--output", type=Path, required=True)
    enrich.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    enrich.add_argument("--config", type=Path, default=Path("config.toml"))
    enrich.add_argument("--mock", action="store_true")
    enrich.add_argument("--confirm-spend", action="store_true")
    enrich.add_argument("--stop-after", type=int)
    reconciliation = stages.add_parser("reconcile-charge", help="Record verified unknown charges offline")
    reconciliation.add_argument("--ledger", type=Path, required=True)
    reconciliation.add_argument("--reservation", required=True)
    reconciliation.add_argument("--cost-usd", required=True)
    reconciliation.add_argument("--evidence", type=Path, required=True)
    reconciliation.add_argument("--config", type=Path, default=Path("config.toml"))
    reconciliation.add_argument("--confirm-reconciliation", action="store_true")
    args = parser.parse_args()
    if args.stage == "reconcile-charge":
        import tomllib

        config = tomllib.loads(args.config.read_text(encoding="utf-8"))
        reconcile_charge(args.ledger, args.reservation, args.cost_usd, args.evidence,
                         config["controls"]["project_api_cap_usd"], args.confirm_reconciliation)
        return
    if args.stage == "enrich":
        run_enrichment(args.input, args.output, args.config, args.manifest, args.mock,
                       args.confirm_spend, args.stop_after)
        return
    if args.stage == "label-golden":
        label_golden(args.source, args.output, args.report)
        return
    if args.stage == "golden-template":
        create_template(args.source, args.output)
        print(f"Created blank human-label copy: {args.output}")
        return
    if args.stage == "validate-golden":
        report = validate_golden(args.input, args.source, args.report)
        print(f"{report['status']}: {report['valid_records']}/50 valid; report: {args.report}")
        raise SystemExit(0 if report["status"] == "valid" else 1)
    result = prepare(args.input, args.manifest, args.output, args.config)
    print(f"Ingested {result['records']} rows; no model calls. Reports: {args.output}")


if __name__ == "__main__":
    main()
