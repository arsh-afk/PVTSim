"""Test for numeric literal scan (P0-9).

Rule R2: Source code may contain only the numerals 0, 1 and 2
(in algebra such as squares, halves and averages), array indices,
and no others.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


# Allowed literals in source code
ALLOWED_LITERALS = {"0", "1", "2"}

# Narrow, reviewed exceptions: preliminary screening module (Design Studio configuration)
EXCLUDED_FILES = {"design.py"}

# Numeric literal pattern (matches integers and floats, but not identifiers)
NUMERIC_LITERAL_RE = re.compile(r"\b(\d+\.?\d*|\.\d+)\b")


def scan_py_files(src_dir: Path) -> list[tuple[str, int, str]]:
    """Scan all .py files under src_dir for disallowed numeric literals.

    Returns list of (file_path, line_number, literal_value) violations.
    """
    violations = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if any(part.startswith(".") for part in py_file.parts):
            continue
        if py_file.name in EXCLUDED_FILES and "toy_fixtures" not in str(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            # Skip files with syntax errors (they'll fail elsewhere)
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if str(node.value) not in ALLOWED_LITERALS and node.value not in (0, 1, 2):
                    violations.append((str(py_file), node.lineno, str(node.value)))

    return violations


def scan_regex_py_files(src_dir: Path) -> list[tuple[str, int, str]]:
    """Regex-based scan as backup for AST failures."""
    violations = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if any(part.startswith(".") for part in py_file.parts):
            continue
        if py_file.name in EXCLUDED_FILES and "toy_fixtures" not in str(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_num, line in enumerate(source.splitlines(), start=1):
            # Skip comments and string literals
            if line.strip().startswith("#"):
                continue

            matches = NUMERIC_LITERAL_RE.findall(line)
            for match in matches:
                try:
                    value = float(match)
                    if value not in (0.0, 1.0, 2.0) and str(value) not in ALLOWED_LITERALS:
                        violations.append((str(py_file), line_num, match))
                except ValueError:
                    continue

    return violations


class TestLiteralScan:
    """Test the numeric literal scanner."""

    def test_allows_zero_one_two(self):
        """Test that 0, 1, 2 are allowed."""
        # This should pass without violations
        from tests.unit.test_literal_scan import scan_py_files
        src = Path("src")
        violations = scan_py_files(src)
        # Currently we have no violations in src/
        assert all(v[2] in ("0", "1", "2") or float(v[2]) in (0.0, 1.0, 2.0) for v in violations)

    def test_catches_violation_in_test_fixture(self):
        """Test that the planted violation is caught."""
        from tests.unit.test_literal_scan import scan_py_files
        src = Path("tests/toy_fixtures")
        violations = scan_py_files(src)

        # Should find the 42 in bad_literal_fixture.py
        assert len(violations) > 0, "Expected to catch the planted violation"
        assert any(v[2] == "42" for v in violations), "Expected to find the literal '42'"

    def test_regex_scan_finds_violation(self):
        """Test the regex-based scan also works."""
        from tests.unit.test_literal_scan import scan_regex_py_files
        src = Path("tests/toy_fixtures")
        violations = scan_regex_py_files(src)
        assert any(v[2] == "42" for v in violations)
