"""Offline preparation/labeling and explicitly confirmed enrichment commands."""

import argparse
from pathlib import Path

from pipeline.calculator import replay
from pipeline.enrich import run_enrichment
from pipeline.jev_measure import measurement_plan, run_measurement
from pipeline.labeler import label_golden
from pipeline.labels import create_template, validate_golden
from pipeline.pilot import pilot_plan, run_pilot
from pipeline.pilot_repair import repair_plan, run_repair
from pipeline.preflight import preflight_plan, run_preflight
from pipeline.prepare import prepare
from pipeline.reconcile import reconcile_charge
from pipeline.sampling import scope_profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    repair = stages.add_parser("pilot-memo-repair", help="Plan memo-only continuation; paid execution requires new yes")
    repair.add_argument("--config", type=Path, default=Path("config.toml"))
    repair.add_argument("--directory", type=Path, default=Path("cost"))
    repair.add_argument("--confirm-spend", action="store_true")
    repair.add_argument("--approved-plan", type=Path)
    measurement = stages.add_parser("jev-measure", help="Plan one Jev call; execute only after explicit yes")
    measurement.add_argument("--config", type=Path, default=Path("config.toml"))
    measurement.add_argument("--output", type=Path, default=Path("artifacts/jev-v2-test"))
    measurement.add_argument("--confirm-spend", action="store_true")
    measurement.add_argument("--approved-plan", type=Path)
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
    preflight = stages.add_parser("preflight", help="Plan two tiny calls offline; execute only after yes")
    preflight.add_argument("--config", type=Path, default=Path("config.toml"))
    preflight.add_argument("--output", type=Path, default=Path("artifacts/preflight"))
    preflight.add_argument("--confirm-spend", action="store_true")
    preflight.add_argument("--approved-plan", type=Path)
    calculator = stages.add_parser("cost", help="Offline replay by default; pilot execution is explicit")
    calculator.add_argument("--directory", type=Path, default=Path("cost"))
    calculator.add_argument("--rates", type=Path)
    calculator.add_argument("--config", type=Path, default=Path("config.toml"))
    calculator.add_argument("--plan-pilot", action="store_true")
    calculator.add_argument("--execute-pilot", action="store_true")
    calculator.add_argument("--confirm-spend", action="store_true")
    calculator.add_argument("--approved-plan", type=Path)
    sample = stages.add_parser("scope-profile", help="Save sampling order and scope counts offline")
    sample.add_argument("--config", type=Path, default=Path("config.toml"))
    sample.add_argument("--output", type=Path, default=Path("artifacts/sampling"))
    args = parser.parse_args()
    if args.stage == "pilot-memo-repair":
        if args.confirm_spend:
            if args.approved_plan is None:
                raise ValueError("Supply the reviewed plan after explicit yes")
            run_repair(args.config, args.directory, args.approved_plan, True)
        else:
            plan = repair_plan(args.config, args.directory)
            print(f"Memo-only repair: max 2 calls; worst-case ${plan['worst_case_nanodollars']/1e9:.9f}. No calls made.")
        return
    if args.stage == "jev-measure":
        if args.confirm_spend:
            if args.approved_plan is None:
                raise ValueError("Supply the reviewed plan after explicit yes")
            run_measurement(args.config, args.output, args.approved_plan, True)
        else:
            plan = measurement_plan(args.config, args.output)
            print(f"Jev measurement: 1 call, no retries; worst-case ${plan['worst_case_nanodollars']/1e9:.9f}. No calls made.")
        return
    if args.stage == "scope-profile":
        import tomllib

        profile = scope_profile(tomllib.loads(args.config.read_text()), args.output)
        print(f"Selected {profile['selected_distinct_texts']} distinct texts; no model calls.")
        return
    if args.stage == "cost":
        if args.execute_pilot:
            if not args.confirm_spend or args.approved_plan is None:
                raise ValueError("Pilot needs --confirm-spend and a reviewed --approved-plan after yes")
            run_pilot(args.config, args.directory, args.approved_plan, True)
        elif args.plan_pilot:
            plan = pilot_plan(args.config, args.directory)
            print(f"Pilot: {plan['expected_initial_calls_upper']} initial calls upper; worst-case ${plan['worst_case_nanodollars']/1e9:.6f}. No calls made.")
        result = replay(args.directory, args.rates)
        print(result["status"])
        return
    if args.stage == "preflight":
        if args.confirm_spend:
            if args.approved_plan is None:
                raise ValueError("Supply the reviewed --approved-plan after explicit yes")
            run_preflight(args.config, args.output, True, args.approved_plan)
        else:
            plan = preflight_plan(args.config, args.output)
            print(f"Preflight: max {plan['maximum_calls']} calls; worst-case ${plan['worst_case_nanodollars']/1e9:.6f}. No calls made.")
        return
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
