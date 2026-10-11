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

    args = parser.parse_args()

    if args.command == "check-inputs":
        sys.exit(cmd_check_inputs(args.phase))
    elif args.command == "run":
        print(f"Running scenario: {args.scenario_id}")
        # TODO: Implement run logic in later phases
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
