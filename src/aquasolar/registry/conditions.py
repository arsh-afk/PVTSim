"""Evaluate `required_when` expressions against the registry."""

from __future__ import annotations

from typing import Any, Dict


# Grammar:
#   always
#   <id> == <literal>
#   <id> != <literal>
#   <id> in <a>,<b>,...
# Literals: true, false, integer, exact string (quoted)

_SIMPLE_RE = r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s*(==|!=|in)\s*(.+)$"

import re
from typing import Optional


def _parse_literal(token: str) -> Any:
    """Parse a literal token from a condition expression."""
    token = token.strip()
    if token == "true":
        return True
    if token == "false":
        return False
    # Try integer
    try:
        return int(token)
    except ValueError:
        pass
    # Try float
    try:
        return float(token)
    except ValueError:
        pass
    # Strip quotes for string literals
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1]
    return token


def _eval_condition(expr: str, registry: Dict[str, Any]) -> bool:
    """Evaluate a single `required_when` condition against the registry.

    expr: "always", "<id> == <literal>", "<id> != <literal>",
          "<id> in <a>,<b>,..."
    """
    expr = expr.strip()
    if expr == "always":
        return True

    m = re.match(_SIMPLE_RE, expr)
    if not m:
        raise ValueError(f"Cannot parse required_when expression: '{expr}'")

    var_id, op, rhs = m.group(1), m.group(2), m.group(3)

    if var_id not in registry:
        # If the referenced parameter is missing, we cannot evaluate.
        # Treat as False (parameter not required) to avoid hard failures.
        # The caller should report this as a separate issue.
        return False

    var_value = registry[var_id]

    if op == "==":
        return var_value == _parse_literal(rhs)
    if op == "!=":
        return var_value != _parse_literal(rhs)
    if op == "in":
        allowed = [item.strip() for item in rhs.split(",")]
        parsed_allowed = [_parse_literal(a) for a in allowed]
        return var_value in parsed_allowed

    raise ValueError(f"Unknown operator '{op}' in required_when expression")


def evaluate_required_when(
    expr: str, registry: Dict[str, Any]
) -> bool:
    """Public API: evaluate a required_when expression.

    Returns True if the parameter IS required, False otherwise.
    """
    return _eval_condition(expr, registry)
