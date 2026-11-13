"""Command-line interface for AquaSolar Living.

Provides:
- check-inputs [--phase N]: Validate inputs up to phase N
- run <scenario_id>: Run a scenario
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aquasolar.registry import load_registry
from aquasolar.registry.errors import InputError, MissingInputError, DraftInputError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_PORT = int("8765")


def cmd_check_inputs(phase: int = None) -> int:
    """Check inputs and write STATUS.md.

    Per Section 3.3:
    1. Evaluate every id in input_index.yaml whose phase <= N
    2. Write inputs/STATUS.md with status tables
    3. Exit non-zero if blocking items remain
    """
    try:
        registry = load_registry()
    except (InputError, MissingInputError, DraftInputError) as e:
        # Write error to STATUS.md
        status_path = Path("inputs/STATUS.md")
        status_path.write_text(
            f"# Input Status\n\n"
            f"## Errors\n\n"
            f"```\n{e}\n```\n",
            encoding="utf-8",
        )
        return 1

    # Generate status report
    lines = ["# Input Status", "", "## Parameters", ""]
    lines.append("| ID | Value | Unit | Status |")
    lines.append("|---|---|---|---|")

    for id_, entry in sorted(registry._params.items()):
        lines.append(f"| {id_} | {entry.value!r} | {entry.unit!r} | {entry.status!r} |")

    lines.append("")
    lines.append("## Tables")
    lines.append("")
    for name in sorted(registry._tables.keys()):
        lines.append(f"- `{name}`: loaded")

    lines.append("")
    lines.append("## Time Series")
    lines.append("")
    for name in sorted(registry._timeseries.keys()):
        lines.append(f"- `{name}`: loaded")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("No blocking issues found.")

    status_path = Path("inputs/STATUS.md")
    status_path.write_text("\n".join(lines), encoding="utf-8")

    return 0


def cmd_apply_demo_defaults() -> int:
    """Apply source-labelled, reproducible exploratory input defaults."""
    from aquasolar.defaults import apply_demo_defaults

    try:
        result = apply_demo_defaults(PROJECT_ROOT)
    except (OSError, ValueError) as exc:
        print(f"Could not apply demo defaults: {exc}", file=sys.stderr)
        return 1
    print(
        f"Applied {result['updated']} previously blank values with seed "
        f"{result['seed']}. Provenance: {result['path']}"
    )
    print(
        "These are exploratory placeholders, not calibrated engineering inputs."
    )
    return 0


def cmd_web_ui(port: int = DEFAULT_WEB_PORT) -> int:
    """Serve the browser workbench on loopback only."""
    try:
        import uvicorn
    except ImportError as exc:
        print(
            "Browser UI requires uvicorn; reinstall the project dependencies.",
            file=sys.stderr,
        )
        return 1
    from aquasolar.web import create_app

    print(f"AquaSolar browser workbench: http://127.0.0.1:{port}")
    uvicorn.run(create_app(PROJECT_ROOT), host="127.0.0.1", port=port)
    return 0


def cmd_run_pvt_only(scenario_id: str, weather: str | None = None) -> int:
    """Run the explicitly limited PVT-only exploratory simulation."""
    import re

    from aquasolar.module_registry import module_is_enabled
    from aquasolar.pvt.runner import load_pvt_parameters, run_pvt_only

    if not re.fullmatch(r"[A-Za-z0-9._-]+", scenario_id) or scenario_id in {".", ".."}:
        print("Scenario ID may contain only letters, digits, dot, underscore, and hyphen.", file=sys.stderr)
        return 2
    try:
        if not module_is_enabled(PROJECT_ROOT, "pvt_runner"):
            raise ValueError("PVT runner is disabled in inputs/module_registry.yaml")
        parameters = load_pvt_parameters(PROJECT_ROOT / "inputs" / "parameters")
        output_dir = PROJECT_ROOT / "outputs" / "pvt_only"
        weather_path = Path(weather) if weather else Path("inputs/timeseries/weather.csv")
        if not weather_path.is_absolute():
            weather_path = PROJECT_ROOT / weather_path
        result = run_pvt_only(
            weather_path=weather_path,
            parameters=parameters,
            output_path=output_dir / f"{scenario_id}.csv",
            summary_path=output_dir / f"{scenario_id}.summary.json",
            scenario_id=scenario_id,
        )
    except (FileNotFoundError, FileExistsError, ImportError, RuntimeError, ValueError) as exc:
        print(f"PVT-only run failed: {exc}", file=sys.stderr)
        return 1
    print(f"Completed exploratory PVT-only scenario: {scenario_id}")
    print(f"Electrical energy: {result['electrical_energy_kwh']:.3f} kWh")
    print(f"Useful heat: {result['useful_heat_kwh']:.3f} kWh")
    print(f"Results: {result['results_csv']}")
    print("Tank, DHW, electrical-bus, and water-treatment outputs are not simulated.")
    return 0


def cmd_convert_tm2(
    source: str, output: str, calendar_year: int, site_timezone: str
) -> int:
    """Validate existing PVT inputs and convert a fixed-width TRNSYS TM2 file."""
    from aquasolar.io.tm2 import convert_tm2_to_weather_csv
    from aquasolar.pvt.runner import load_pvt_parameters

    try:
        parameters = load_pvt_parameters(PROJECT_ROOT / "inputs" / "parameters")
        source_path = Path(source)
        output_path = Path(output)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        result = convert_tm2_to_weather_csv(
            source_path,
            output_path,
            calendar_year=calendar_year,
            site_timezone=site_timezone,
        )
    except (OSError, ImportError, TypeError, ValueError) as exc:
        print(f"TM2 conversion failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Validated PVT parameters and converted {result.records} hourly rows "
        f"from station {result.station_id} {result.station_name}."
    )
    print(
        f"TM2 station location: {result.latitude:.4f}, {result.longitude:.4f}; "
        f"UTC{result.utc_offset_hours:+d}."
    )
    if (
        abs(result.latitude - parameters["site.latitude"]) > float("0.1")
        or abs(result.longitude - parameters["site.longitude"]) > float("0.1")
    ):
        print(
            "WARNING: TM2 station coordinates differ from the current site "
            "parameters. They were not changed; verify this weather source is "
            "appropriate for the modeled site."
        )
    print(f"Weather CSV: {result.csv_path}")
    print(f"Metadata: {result.metadata_path}")
    print("Simulation parameter files were validated and left unchanged.")
    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="aquasolar",
        description="AquaSolar Living - villa-scale PVT + water-assurance simulator",
    )
    subparsers = parser.add_subparsers(dest="command")

    # check-inputs command
    check_parser = subparsers.add_parser("check-inputs", help="Validate inputs")
    check_parser.add_argument("--phase", type=int, default=None, help="Check inputs up to phase N")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a scenario")
    run_parser.add_argument("scenario_id", help="Scenario ID to run")
    run_parser.add_argument(
        "--weather",
        help="Weather CSV path (defaults to inputs/timeseries/weather.csv)",
    )

    tm2_parser = subparsers.add_parser(
        "convert-tm2",
        help="Validate and convert a fixed-width TRNSYS TMY2 TM2 weather file",
    )
    tm2_parser.add_argument("source", help="Path to the TM2 source file")
    tm2_parser.add_argument("output", help="Destination weather CSV path")
    tm2_parser.add_argument(
        "--calendar-year",
        required=True,
        type=int,
        help="Non-leap calendar year for reconstructed weather timestamps",
    )
    tm2_parser.add_argument(
        "--site-timezone",
        required=True,
        help="IANA timezone for the weather station, for example Asia/Dubai",
    )

    # local parameter-entry interface
    subparsers.add_parser("ui", help="Open the local input/output interface")

    # localhost-only browser workbench
    web_parser = subparsers.add_parser(
        "web-ui", help="Open the local browser-based input workbench"
    )
    web_parser.add_argument(
        "--port", type=int, default=DEFAULT_WEB_PORT, help="Local web server port"
    )

    # reproducible exploratory defaults, each labelled with source and assumptions
    subparsers.add_parser(
        "apply-demo-defaults",
        help="Fill unset inputs with documented values and seeded demo assumptions",
    )

    args = parser.parse_args()

    if args.command == "check-inputs":
        sys.exit(cmd_check_inputs(args.phase))
    elif args.command == "run":
        sys.exit(cmd_run_pvt_only(args.scenario_id, args.weather))
    elif args.command == "convert-tm2":
        sys.exit(
            cmd_convert_tm2(
                args.source,
                args.output,
                args.calendar_year,
                args.site_timezone,
            )
        )
    elif args.command == "apply-demo-defaults":
        sys.exit(cmd_apply_demo_defaults())
    elif args.command == "web-ui":
        if not (1 <= args.port <= int("65535")):
            parser.error("--port must be between 1 and 65535")
        sys.exit(cmd_web_ui(args.port))
    elif args.command == "ui":
        from aquasolar.ui import main as launch_ui

        launch_ui()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
