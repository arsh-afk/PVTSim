"""Input error types and formatting."""

from __future__ import annotations


class InputError(Exception):
    """Base class for all input validation errors."""

    pass


class MissingInputError(InputError):
    """A required input is missing from the files."""

    def __init__(self, path: str, location: str, expected: str, found: str = "empty"):
        self.path = path
        self.location = location
        self.expected = expected
        self.found = found
        super().__init__(
            f"INPUT ERROR for {path}/{location}: {expected} but found '{found}'"
        )


class DraftInputError(InputError):
    """A required input has status='draft' instead of 'confirmed'."""

    def __init__(self, path: str, location: str, expected: str, found: str = "draft"):
        self.path = path
        self.location = location
        self.expected = expected
        self.found = found
        super().__init__(
            f"INPUT ERROR (draft) for {path}/{location}: {expected} but status='{found}'"
        )


class InvalidInputError(InputError):
    """A required input has an invalid value, unit, or format."""

    def __init__(self, path: str, location: str, expected: str, found: str):
        self.path = path
        self.location = location
        self.expected = expected
        self.found = found
        super().__init__(
            f"INPUT ERROR for {path}/{location}: expected {expected}, found '{found}'"
        )


def format_input_error(
    file_path: str,
    location: str,
    problem: str,
    expected: str,
    found: str,
    fix: str,
) -> str:
    """Format an error message using the mandated layout from Section 3.4."""
    return (
        "INPUT ERROR\n"
        f"file:      {file_path}\n"
        f"location:  {location}\n"
        f"problem:   {problem}\n"
        f"expected:  {expected}\n"
        f"found:     {found}\n"
        f"fix:       {fix}"
    )
