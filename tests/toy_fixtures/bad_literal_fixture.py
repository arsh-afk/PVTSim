"""Fixture with a deliberate numeric literal violation.

This file is used by the literal scan test (P0-9) to prove the scanner catches violations.
It should NEVER be imported by src/ - only used in tests/.
"""

# DELIBERATE VIOLATION: 42 is not in {0, 1, 2}
# The literal scan test should catch this.
CONST_VIOLATION = 42
