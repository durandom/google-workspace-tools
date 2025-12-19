"""Output mode management for CLI."""

import contextvars
from enum import Enum


class OutputMode(str, Enum):
    """Output mode for CLI commands."""

    HUMAN = "human"  # Rich console output (colorful, interactive)
    JSON = "json"  # Machine-readable JSON output


# Thread-local context for output mode
_output_mode_var: contextvars.ContextVar[OutputMode] = contextvars.ContextVar(
    "output_mode", default=OutputMode.HUMAN
)


def set_output_mode(mode: OutputMode) -> None:
    """Set the output mode for the current context.

    Args:
        mode: The output mode to set (HUMAN or JSON)
    """
    _output_mode_var.set(mode)


def get_output_mode() -> OutputMode:
    """Get the current output mode.

    Returns:
        The current output mode (defaults to HUMAN)
    """
    return _output_mode_var.get()


def is_json_mode() -> bool:
    """Check if current output mode is JSON.

    Returns:
        True if in JSON mode, False otherwise
    """
    return get_output_mode() == OutputMode.JSON


def is_human_mode() -> bool:
    """Check if current output mode is HUMAN.

    Returns:
        True if in HUMAN mode, False otherwise
    """
    return get_output_mode() == OutputMode.HUMAN
