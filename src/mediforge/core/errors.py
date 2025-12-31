"""Custom exceptions with source location tracking."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SourceLocation:
    """Location in a source file for error reporting."""

    file: Path
    line: int
    column: Optional[int] = None
    context_lines: list[str] = field(default_factory=list)

    def format(self) -> str:
        """Format location for error message."""
        loc = f"{self.file}:{self.line}"
        if self.column is not None:
            loc += f":{self.column}"
        return loc


class MediforgeError(Exception):
    """Base exception for all Mediforge errors."""

    pass


class ValidationError(MediforgeError):
    """Error in scenario or configuration validation."""

    def __init__(
        self,
        message: str,
        location: Optional[SourceLocation] = None,
        expected: Optional[str] = None,
        found: Optional[str] = None,
    ):
        self.message = message
        self.location = location
        self.expected = expected
        self.found = found
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format complete error message with context."""
        lines = [f"Error: {self.message}"]

        if self.expected and self.found:
            lines.append(f"  Expected: {self.expected}")
            lines.append(f"  Found: {self.found}")

        if self.location:
            lines.append(f"  At: {self.location.file}:{self.location.line}")
            if self.location.context_lines:
                lines.append("")
                for i, ctx_line in enumerate(self.location.context_lines):
                    # Line numbers are 1-based, context starts at line-1
                    line_num = self.location.line - 1 + i
                    marker = ">>>" if i == 1 else "   "
                    lines.append(f"  {marker} {line_num:4d} | {ctx_line}")

        return "\n".join(lines)


class MediaFileError(MediforgeError):
    """Error with a media file (missing, unsupported format, corrupt)."""

    def __init__(
        self,
        message: str,
        path: Path,
        scenario_location: Optional[SourceLocation] = None,
    ):
        self.message = message
        self.path = path
        self.scenario_location = scenario_location
        super().__init__(f"{message}: {path}")


class FFmpegError(MediforgeError):
    """Error during FFmpeg execution."""

    def __init__(
        self,
        message: str,
        command: list[str],
        stderr: str,
        stage: Optional[str] = None,
        temp_dir: Optional[Path] = None,
    ):
        self.message = message
        self.command = command
        self.stderr = stderr
        self.stage = stage
        self.temp_dir = temp_dir
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error with command and output."""
        lines = [f"FFmpeg error: {self.message}"]
        if self.stage:
            lines.append(f"  Stage: {self.stage}")
        if self.temp_dir:
            lines.append(f"  Intermediate files preserved at: {self.temp_dir}")
        lines.append("")
        lines.append("  FFmpeg output (last 10 lines):")
        for line in self.stderr.strip().split("\n")[-10:]:
            lines.append(f"    {line}")
        return "\n".join(lines)


class ConfigurationError(MediforgeError):
    """Error in configuration files or presets."""

    pass


class ProbeError(MediforgeError):
    """Error when probing media files with ffprobe."""

    def __init__(self, message: str, path: Path, stderr: str = ""):
        self.path = path
        self.stderr = stderr
        super().__init__(f"{message}: {path}")
