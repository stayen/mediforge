"""Command execution with dry-run and progress support."""

import subprocess
from pathlib import Path
from typing import Callable, Optional

from ..core.errors import FFmpegError
from ..utils.logging import get_logger


class CommandExecutor:
    """
    Executes shell commands with dry-run and progress support.
    """

    def __init__(
        self,
        dry_run: bool = False,
        progress_callback: Callable[[float], None] | None = None,
        log_level: str = "warning",
    ):
        self.dry_run = dry_run
        self.progress_callback = progress_callback
        self.logger = get_logger(__name__, log_level)

    def execute(
        self,
        command: list[str],
        stage: str | None = None,
        expected_duration: float | None = None,
        temp_dir: Path | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Execute a command.

        In dry-run mode, prints command and returns without executing.

        Args:
            command: Command and arguments
            stage: Description for error messages
            expected_duration: Expected output duration for progress calculation
            temp_dir: Temp directory to report on error

        Returns:
            CompletedProcess result

        Raises:
            FFmpegError: If command fails
        """
        cmd_str = ' '.join(command)
        self.logger.debug(f"Executing: {cmd_str}")

        if self.dry_run:
            print(cmd_str)
            return subprocess.CompletedProcess(command, 0, "", "")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
        except subprocess.TimeoutExpired:
            raise FFmpegError(
                message="Command timed out after 1 hour",
                command=command,
                stderr="",
                stage=stage,
                temp_dir=temp_dir,
            )
        except FileNotFoundError:
            raise FFmpegError(
                message=f"Command not found: {command[0]}",
                command=command,
                stderr="",
                stage=stage,
                temp_dir=temp_dir,
            )
        except OSError as e:
            raise FFmpegError(
                message=f"Failed to execute command: {e}",
                command=command,
                stderr="",
                stage=stage,
                temp_dir=temp_dir,
            )

        if result.returncode != 0:
            raise FFmpegError(
                message=f"Command failed with exit code {result.returncode}",
                command=command,
                stderr=result.stderr,
                stage=stage,
                temp_dir=temp_dir,
            )

        return result

    def execute_with_progress(
        self,
        command: list[str],
        expected_duration: float,
        stage: str | None = None,
        temp_dir: Path | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Execute FFmpeg command with progress parsing.

        Adds -progress pipe:1 to command and parses output.
        """
        if self.dry_run:
            return self.execute(command, stage, expected_duration, temp_dir)

        # Insert progress option before output file
        cmd_with_progress = command[:-1] + ['-progress', 'pipe:1', command[-1]]

        self.logger.debug(f"Executing with progress: {' '.join(cmd_with_progress)}")

        parser = ProgressParser(expected_duration)

        try:
            process = subprocess.Popen(
                cmd_with_progress,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout_lines = []
            if process.stdout:
                for line in process.stdout:
                    stdout_lines.append(line)
                    progress = parser.parse_line(line)
                    if progress is not None and self.progress_callback:
                        self.progress_callback(progress)

            _, stderr = process.communicate(timeout=3600)

        except subprocess.TimeoutExpired:
            process.kill()
            raise FFmpegError(
                message="Command timed out after 1 hour",
                command=command,
                stderr="",
                stage=stage,
                temp_dir=temp_dir,
            )

        if process.returncode != 0:
            raise FFmpegError(
                message=f"Command failed with exit code {process.returncode}",
                command=command,
                stderr=stderr,
                stage=stage,
                temp_dir=temp_dir,
            )

        return subprocess.CompletedProcess(
            command,
            process.returncode,
            ''.join(stdout_lines),
            stderr,
        )


class ProgressParser:
    """Parses FFmpeg progress output."""

    def __init__(self, expected_duration: float):
        self.expected_duration = expected_duration
        self.current_time: float = 0

    def parse_line(self, line: str) -> float | None:
        """
        Parse a line of FFmpeg progress output.

        Returns progress percentage (0-100) or None if not a progress line.
        """
        line = line.strip()

        if line.startswith("out_time_ms="):
            try:
                ms = int(line.split("=")[1])
                self.current_time = ms / 1_000_000
                if self.expected_duration > 0:
                    return min(100.0, (self.current_time / self.expected_duration) * 100)
            except (ValueError, IndexError):
                pass

        elif line.startswith("out_time="):
            try:
                time_str = line.split("=")[1]
                # Parse HH:MM:SS.microseconds
                parts = time_str.split(":")
                if len(parts) == 3:
                    hours = int(parts[0])
                    mins = int(parts[1])
                    secs = float(parts[2])
                    self.current_time = hours * 3600 + mins * 60 + secs
                    if self.expected_duration > 0:
                        return min(100.0, (self.current_time / self.expected_duration) * 100)
            except (ValueError, IndexError):
                pass

        return None
