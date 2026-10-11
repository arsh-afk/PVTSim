"""Run manifest generation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import git


class Manifest:
    """Run manifest containing all metadata for reproducibility."""

    def __init__(
        self,
        run_id: str,
        code_commit: str,
        environment_hash: str,
        input_hashes: Dict[str, str],
        gate_signoff_hashes: List[str],
        seeds: int,
        solver_settings: Dict[str, Any],
        scenario_id: str,
        start_time: str,
        end_time: Optional[str] = None,
        test_summary: Optional[Dict[str, Any]] = None,
    ):
        self.run_id = run_id
        self.code_commit = code_commit
        self.environment_hash = environment_hash
        self.input_hashes = input_hashes
        self.gate_signoff_hashes = gate_signoff_hashes
        self.seeds = seeds
        self.solver_settings = solver_settings
        self.scenario_id = scenario_id
        self.start_time = start_time
        self.end_time = end_time
        self.test_summary = test_summary or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "code_commit": self.code_commit,
            "environment_hash": self.environment_hash,
            "input_hashes": self.input_hashes,
            "gate_signoff_hashes": self.gate_signoff_hashes,
            "seeds": self.seeds,
            "solver_settings": self.solver_settings,
            "scenario_id": self.scenario_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "test_summary": self.test_summary,
        }

    def write(self, output_path: Path) -> None:
        """Write manifest to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


def write_manifest(
    run_id: str,
    output_dir: Path,
    input_hashes: Dict[str, str],
    seeds: int,
    solver_settings: Dict[str, Any],
    scenario_id: str,
    gate_signoff_hashes: Optional[List[str]] = None,
    test_summary: Optional[Dict[str, Any]] = None,
) -> Manifest:
    """Create and write a manifest file.

    Per P0-7: Write manifest.json with run metadata.
    """
    # Get current commit hash
    try:
        repo = git.Repo(search_parent_directories=True)
        code_commit = repo.head.object.hexsha[: (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1)]
    except git.InvalidGitRepositoryError:
        code_commit = "unknown"

    # Environment hash (placeholder - would be based on environment.lock)
    environment_hash = "placeholder"

    start_time = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    manifest = Manifest(
        run_id=run_id,
        code_commit=code_commit,
        environment_hash=environment_hash,
        input_hashes=input_hashes,
        gate_signoff_hashes=gate_signoff_hashes or [],
        seeds=seeds,
        solver_settings=solver_settings,
        scenario_id=scenario_id,
        start_time=start_time,
        test_summary=test_summary or {},
    )

    manifest.write(output_dir / "manifest.json")
    return manifest
