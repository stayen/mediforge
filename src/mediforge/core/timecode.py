"""Timecode parsing and conversion utilities."""

from decimal import Decimal
import re
from typing import Union

# Pattern: H:MM:SS.mmm or M:SS.mmm or SS.mmm or just seconds
# Also supports MM:SS or H:MM:SS without milliseconds
TIMECODE_PATTERN = re.compile(
    r'^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?$'
)

# Pattern for just seconds with optional milliseconds
SECONDS_PATTERN = re.compile(r'^(\d+)(?:\.(\d{1,3}))?$')


def parse_timecode(value: str) -> Decimal:
    """
    Parse timecode string to Decimal seconds.

    Formats:
        - "H:MM:SS.mmm" -> hours, minutes, seconds, milliseconds
        - "M:SS.mmm" -> minutes, seconds, milliseconds
        - "SS.mmm" -> seconds, milliseconds
        - "H:MM:SS" -> hours, minutes, seconds (no milliseconds)
        - "M:SS" -> minutes, seconds

    Args:
        value: Timecode string

    Returns:
        Decimal seconds with millisecond precision

    Raises:
        ValueError: If format is invalid
    """
    value = value.strip()

    # Try seconds-only pattern first
    seconds_match = SECONDS_PATTERN.match(value)
    if seconds_match:
        secs = int(seconds_match.group(1))
        ms_str = seconds_match.group(2)
        if ms_str:
            # Pad to 3 digits for consistent millisecond parsing
            ms_str = ms_str.ljust(3, '0')
            ms = int(ms_str)
        else:
            ms = 0
        return Decimal(secs) + Decimal(ms) / Decimal(1000)

    # Try timecode pattern
    match = TIMECODE_PATTERN.match(value)
    if not match:
        raise ValueError(f"Invalid timecode format: '{value}'. "
                         f"Expected format: H:MM:SS.mmm, M:SS.mmm, or SS.mmm")

    hours_str, mins_str, secs_str, ms_str = match.groups()

    hours = int(hours_str) if hours_str else 0
    mins = int(mins_str)
    secs = int(secs_str)

    # Validate ranges
    if mins >= 60:
        raise ValueError(f"Minutes must be less than 60, got {mins}")
    if secs >= 60:
        raise ValueError(f"Seconds must be less than 60, got {secs}")

    # Parse milliseconds, padding to 3 digits if needed
    if ms_str:
        ms_str = ms_str.ljust(3, '0')
        ms = int(ms_str)
    else:
        ms = 0

    total_seconds = Decimal(hours * 3600 + mins * 60 + secs) + Decimal(ms) / Decimal(1000)
    return total_seconds


def format_timecode(seconds: Decimal | float | int, precision: int = 3) -> str:
    """
    Format Decimal seconds as timecode string.

    Args:
        seconds: Time in seconds
        precision: Decimal places for milliseconds (default 3)

    Returns:
        Formatted timecode string "H:MM:SS.mmm"
    """
    if not isinstance(seconds, Decimal):
        seconds = Decimal(str(seconds))

    if seconds < 0:
        raise ValueError(f"Seconds cannot be negative: {seconds}")

    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_secs = total_ms // 1000
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60

    if precision == 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    else:
        ms_str = str(ms).zfill(3)[:precision]
        return f"{hours}:{mins:02d}:{secs:02d}.{ms_str}"


def parse_duration(value: Union[str, float, int, Decimal]) -> Decimal:
    """
    Parse duration value (accepts timecode string or numeric seconds).

    Args:
        value: Duration as timecode string or numeric value

    Returns:
        Decimal seconds
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        # Check if it looks like a number
        try:
            return Decimal(value)
        except Exception:
            # Try parsing as timecode
            return parse_timecode(value)
    raise ValueError(f"Cannot parse duration from: {value!r}")
