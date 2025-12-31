# Mediforge Implementation Specification

## Overview

Mediforge is a Python command-line toolkit for media file processing, designed to replace complex GUI applications (Shotcut, Ardour, etc.) for common linear media operations. It provides composable tools for video/audio composition, normalization, mastering, and multiplexing.

### Design Principles

1. **Orchestration over processing** — Delegate heavy computation to ffmpeg/ImageMagick; Python handles coordination
2. **Human-readable scenarios** — YAML-based timeline definitions with timecode notation
3. **Plugin architecture** — New operations added as independent modules
4. **Fail-safe defaults** — Preserve intermediate files on error, clean up on success
5. **Platform agnostic** — Runs on Linux, macOS, Windows with Python 3.11+ and ffmpeg

---

## Technical Stack

### Core Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `click` | CLI framework | >=8.0 |
| `pydantic` | Data validation, settings | >=2.0 |
| `ruamel.yaml` | YAML parsing with line numbers | >=0.18 |
| `rich` | Terminal output, progress bars | >=13.0 |

### External Tools (Required)

| Tool | Purpose | Minimum Version |
|------|---------|-----------------|
| `ffmpeg` | Video/audio processing | 5.0 |
| `ffprobe` | Media file analysis | 5.0 |
| `imagemagick` | Image processing (optional) | 7.0 |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `pytest-cov` | Coverage reporting |
| `mypy` | Static type checking |
| `ruff` | Linting and formatting |

---

## Project Structure

```
mediforge/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── mediforge/
│       ├── __init__.py              # Package version, metadata
│       ├── cli.py                   # Entry point, plugin loader
│       ├── core/
│       │   ├── __init__.py
│       │   ├── timecode.py          # Timecode parsing and conversion
│       │   ├── models.py            # Core data models
│       │   ├── scenario.py          # YAML scenario parsing
│       │   ├── effects.py           # Effect definitions
│       │   ├── errors.py            # Custom exceptions
│       │   ├── validation.py        # File and schema validation
│       │   └── probe.py             # ffprobe wrapper
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── ffmpeg.py            # FFmpeg command construction
│       │   ├── progress.py          # Progress parsing
│       │   └── executor.py          # Command execution, dry-run
│       ├── plugins/
│       │   ├── __init__.py          # Plugin discovery
│       │   ├── video/
│       │   │   ├── __init__.py      # Registers 'video' command group
│       │   │   ├── compose.py       # video compose
│       │   │   └── edit.py          # video edit
│       │   ├── audio/
│       │   │   ├── __init__.py      # Registers 'audio' command group
│       │   │   ├── compose.py       # audio compose
│       │   │   ├── normalize.py     # audio normalize
│       │   │   └── master.py        # audio master
│       │   ├── mux/
│       │   │   └── __init__.py      # mux command
│       │   └── info/
│       │       └── __init__.py      # info command
│       ├── config/
│       │   ├── __init__.py
│       │   ├── defaults.py          # Built-in presets
│       │   ├── loader.py            # Config file loading
│       │   └── schema.py            # Config validation schemas
│       └── utils/
│           ├── __init__.py
│           ├── tempfiles.py         # Temp directory management
│           └── logging.py           # Logging configuration
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── test_timecode.py
│   ├── test_models.py
│   ├── test_scenario.py
│   ├── test_ffmpeg.py
│   ├── test_video_compose.py
│   ├── test_audio_normalize.py
│   └── fixtures/
│       ├── sample_video.mp4         # Small test video
│       ├── sample_audio.wav         # Small test audio
│       ├── sample_image.png         # Test image
│       └── scenarios/
│           ├── valid_video.yaml
│           ├── valid_audio.yaml
│           └── invalid_*.yaml       # Error case scenarios
└── docs/
    ├── usage.md
    ├── scenario-format.md
    └── presets.md
```

---

## Core Data Models

### File: `src/mediforge/core/timecode.py`

```python
"""Timecode parsing and conversion utilities."""

from decimal import Decimal
import re
from typing import Union

# Pattern: H:MM:SS.mmm or M:SS.mmm or SS.mmm
TIMECODE_PATTERN = re.compile(
    r'^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?$'
)


def parse_timecode(value: str) -> Decimal:
    """
    Parse timecode string to Decimal seconds.
    
    Formats:
        - "H:MM:SS.mmm" -> hours, minutes, seconds, milliseconds
        - "M:SS.mmm" -> minutes, seconds, milliseconds
        - "SS.mmm" -> seconds, milliseconds
    
    Args:
        value: Timecode string
        
    Returns:
        Decimal seconds with millisecond precision
        
    Raises:
        ValueError: If format is invalid
    """
    ...


def format_timecode(seconds: Decimal, precision: int = 3) -> str:
    """
    Format Decimal seconds as timecode string.
    
    Args:
        seconds: Time in seconds
        precision: Decimal places for milliseconds (default 3)
        
    Returns:
        Formatted timecode string "H:MM:SS.mmm"
    """
    ...


def parse_duration(value: Union[str, float, int, Decimal]) -> Decimal:
    """
    Parse duration value (accepts timecode string or numeric seconds).
    
    Args:
        value: Duration as timecode string or numeric value
        
    Returns:
        Decimal seconds
    """
    ...
```

### File: `src/mediforge/core/models.py`

```python
"""Core data models for media processing."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Literal, Optional


class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


@dataclass(frozen=True)
class TimeRange:
    """Immutable time range with start and end points."""
    start: Decimal
    end: Decimal
    
    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError(f"End time must be greater than start: {self.start} >= {self.end}")
    
    @property
    def duration(self) -> Decimal:
        return self.end - self.start
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """Check if this range overlaps with another."""
        return self.start < other.end and other.start < self.end
    
    def overlap_duration(self, other: 'TimeRange') -> Decimal:
        """Calculate overlap duration with another range."""
        if not self.overlaps(other):
            return Decimal(0)
        return min(self.end, other.end) - max(self.start, other.start)


@dataclass
class MediaAsset:
    """Represents a source media file with metadata."""
    path: Path
    type: MediaType
    duration: Optional[Decimal] = None  # None for images
    width: Optional[int] = None
    height: Optional[int] = None
    framerate: Optional[Decimal] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    
    @classmethod
    def from_probe(cls, path: Path, probe_data: dict) -> 'MediaAsset':
        """Construct MediaAsset from ffprobe output."""
        ...


@dataclass
class Effect:
    """Base class for effects applied to clips."""
    pass


@dataclass
class FadeIn(Effect):
    duration: Decimal


@dataclass
class FadeOut(Effect):
    duration: Decimal


@dataclass
class VolumeAdjust(Effect):
    level: Decimal  # 1.0 = original, 0.5 = half, 2.0 = double


@dataclass
class SpeedAdjust(Effect):
    factor: Decimal  # 1.0 = original, 0.5 = half speed, 2.0 = double speed


@dataclass
class Clip:
    """A segment of media placed on a timeline."""
    asset: MediaAsset
    timeline_range: TimeRange
    source_offset: Decimal = Decimal(0)
    speed: Decimal = Decimal(1)
    effects: list[Effect] = field(default_factory=list)
    
    @property
    def source_duration(self) -> Decimal:
        """Duration in source media time (accounting for speed)."""
        return self.timeline_range.duration * self.speed


@dataclass
class Timeline:
    """Ordered collection of clips forming a composition."""
    clips: list[Clip] = field(default_factory=list)
    
    @property
    def duration(self) -> Decimal:
        """Total timeline duration."""
        if not self.clips:
            return Decimal(0)
        return max(clip.timeline_range.end for clip in self.clips)
    
    def get_overlapping_clips(self, time: Decimal) -> list[Clip]:
        """Get all clips active at a given time point."""
        return [
            clip for clip in self.clips
            if clip.timeline_range.start <= time < clip.timeline_range.end
        ]
    
    def detect_crossfades(self) -> list[tuple[Clip, Clip, Decimal]]:
        """Detect overlapping clips that require crossfade."""
        ...


@dataclass
class VideoOutputSettings:
    """Settings for video output encoding."""
    resolution: tuple[int, int] = (1920, 1080)
    framerate: Decimal = Decimal(30)
    codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    pixel_format: str = "yuv420p"


@dataclass
class AudioOutputSettings:
    """Settings for audio output encoding."""
    sample_rate: int = 48000
    channels: int = 2
    codec: str = "pcm_s24le"
    bitrate: Optional[str] = None  # For lossy codecs


@dataclass
class Scenario:
    """Complete scenario for media composition."""
    version: int
    type: Literal["video", "audio"]
    timeline: Timeline
    output: VideoOutputSettings | AudioOutputSettings
    source_file: Optional[Path] = None  # For error reporting
```

---

## Error Handling

### File: `src/mediforge/core/errors.py`

```python
"""Custom exceptions with source location tracking."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SourceLocation:
    """Location in a source file for error reporting."""
    file: Path
    line: int
    column: Optional[int] = None
    context_lines: list[str] = None  # Surrounding lines for display
    
    def format(self) -> str:
        """Format location for error message."""
        ...


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
        self.command = command
        self.stderr = stderr
        self.stage = stage
        self.temp_dir = temp_dir
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format error with command and output."""
        lines = [f"FFmpeg error: {self.args[0]}"]
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
```

---

## Scenario Parsing

### File: `src/mediforge/core/scenario.py`

```python
"""YAML scenario parsing with line number preservation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from ruamel.yaml import YAML

from .errors import ValidationError, SourceLocation
from .models import (
    Scenario, Timeline, Clip, MediaAsset, MediaType,
    TimeRange, Effect, FadeIn, FadeOut, VolumeAdjust, SpeedAdjust,
    VideoOutputSettings, AudioOutputSettings,
)
from .timecode import parse_timecode, parse_duration


class ClipSchema(BaseModel):
    """Pydantic schema for clip validation."""
    start: str
    end: str
    type: MediaType
    source: str
    offset: str = "0:00:00.000"
    speed: float = 1.0
    fade_in: float | None = None
    fade_out: float | None = None
    volume: float = 1.0
    
    # Store line number from YAML for error reporting
    _source_line: int | None = None
    
    @field_validator('start', 'end', 'offset')
    @classmethod
    def validate_timecode(cls, v: str) -> str:
        try:
            parse_timecode(v)
        except ValueError as e:
            raise ValueError(f"Invalid timecode format: {v}") from e
        return v
    
    @field_validator('speed')
    @classmethod
    def validate_speed(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"Speed must be positive: {v}")
        if v > 10:
            raise ValueError(f"Speed factor too large: {v}")
        return v


class VideoOutputSchema(BaseModel):
    """Schema for video output settings."""
    resolution: str = "1920x1080"
    framerate: float = 30
    codec: str = "h264"
    crf: int = 18
    preset: str = "medium"
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        try:
            w, h = v.lower().split('x')
            int(w), int(h)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid resolution format: {v}, expected WxH")
        return v


class AudioOutputSchema(BaseModel):
    """Schema for audio output settings."""
    sample_rate: int = 48000
    channels: int = 2
    codec: str = "pcm_s24le"
    bitrate: str | None = None


class ScenarioSchema(BaseModel):
    """Top-level scenario schema."""
    version: int = 1
    type: str  # "video" or "audio"
    output: dict = Field(default_factory=dict)
    timeline: list[dict]
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ('video', 'audio'):
            raise ValueError(f"Invalid scenario type: {v}, must be 'video' or 'audio'")
        return v


class ScenarioParser:
    """
    Parser for YAML scenario files with line number tracking.
    
    Usage:
        parser = ScenarioParser()
        scenario = parser.parse(Path("scenario.yaml"))
    """
    
    SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm'}
    SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a'}
    SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.bmp'}
    
    def __init__(self, base_path: Path | None = None):
        """
        Initialize parser.
        
        Args:
            base_path: Base directory for resolving relative source paths.
                      Defaults to scenario file's parent directory.
        """
        self.base_path = base_path
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self._line_map: dict[int, int] = {}  # Object id -> line number
    
    def parse(self, path: Path) -> Scenario:
        """
        Parse scenario file.
        
        Args:
            path: Path to YAML scenario file
            
        Returns:
            Validated Scenario object
            
        Raises:
            ValidationError: If scenario is invalid
            FileNotFoundError: If scenario file doesn't exist
        """
        ...
    
    def _build_line_map(self, node: Any, depth: int = 0) -> None:
        """Recursively build mapping of objects to source line numbers."""
        ...
    
    def _parse_clip(
        self,
        data: dict,
        index: int,
        scenario_type: str,
        scenario_path: Path,
    ) -> Clip:
        """Parse and validate a single clip definition."""
        ...
    
    def _resolve_source(self, source: str, scenario_path: Path) -> Path:
        """Resolve source path relative to scenario file or base_path."""
        ...
    
    def _detect_media_type(self, path: Path) -> MediaType:
        """Detect media type from file extension."""
        suffix = path.suffix.lower()
        if suffix in self.SUPPORTED_VIDEO_EXTENSIONS:
            return MediaType.VIDEO
        elif suffix in self.SUPPORTED_AUDIO_EXTENSIONS:
            return MediaType.AUDIO
        elif suffix in self.SUPPORTED_IMAGE_EXTENSIONS:
            return MediaType.IMAGE
        else:
            raise ValidationError(
                f"Unsupported file type",
                expected=f"one of {self.SUPPORTED_VIDEO_EXTENSIONS | self.SUPPORTED_AUDIO_EXTENSIONS | self.SUPPORTED_IMAGE_EXTENSIONS}",
                found=suffix,
            )
    
    def _create_location(self, line: int, path: Path) -> SourceLocation:
        """Create SourceLocation with context lines from file."""
        ...
```

---

## FFmpeg Backend

### File: `src/mediforge/backends/ffmpeg.py`

```python
"""FFmpeg command construction and filter graph building."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from ..core.models import (
    Clip, Timeline, Effect, FadeIn, FadeOut, SpeedAdjust, VolumeAdjust,
    VideoOutputSettings, AudioOutputSettings,
)


@dataclass
class FFmpegInput:
    """Represents an input file with options."""
    path: Path
    options: list[str] = None
    
    def to_args(self) -> list[str]:
        args = []
        if self.options:
            args.extend(self.options)
        args.extend(['-i', str(self.path)])
        return args


@dataclass
class FilterNode:
    """Node in an FFmpeg filter graph."""
    filter_name: str
    params: dict[str, str]
    inputs: list[str]
    outputs: list[str]
    
    def to_string(self) -> str:
        """Convert to FFmpeg filter string."""
        ...


class FilterGraph:
    """Builder for complex FFmpeg filter graphs."""
    
    def __init__(self):
        self._nodes: list[FilterNode] = []
        self._counter: int = 0
    
    def add_node(
        self,
        filter_name: str,
        params: dict[str, str] | None = None,
        inputs: list[str] | None = None,
    ) -> str:
        """
        Add a filter node and return its output label.
        
        Args:
            filter_name: FFmpeg filter name
            params: Filter parameters
            inputs: Input labels (default: previous output)
            
        Returns:
            Output label for this node
        """
        ...
    
    def build(self) -> str:
        """Build complete filter graph string."""
        ...


class FFmpegCommandBuilder:
    """
    Builds FFmpeg commands for various operations.
    
    This class constructs FFmpeg command-line arguments for:
    - Video/audio composition from timelines
    - Audio normalization
    - Audio mastering
    - Muxing video and audio
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    def build_video_compose(
        self,
        timeline: Timeline,
        output_settings: VideoOutputSettings,
        output_path: Path,
        preview: bool = False,
    ) -> list[str]:
        """
        Build command for video composition.
        
        Handles:
        - Image inputs (with loop and duration)
        - Video inputs (with seeking and duration)
        - Speed adjustment
        - Fade effects
        - Crossfades between overlapping clips
        - Resolution scaling/padding
        
        Args:
            timeline: Timeline with clips
            output_settings: Encoding settings
            output_path: Output file path
            preview: If True, use preview quality settings
            
        Returns:
            Complete FFmpeg command as list of arguments
        """
        ...
    
    def build_audio_compose(
        self,
        timeline: Timeline,
        output_settings: AudioOutputSettings,
        output_path: Path,
    ) -> list[str]:
        """Build command for audio composition."""
        ...
    
    def build_normalize(
        self,
        input_path: Path,
        output_path: Path,
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
    ) -> list[str]:
        """
        Build two-pass loudness normalization command.
        
        Returns commands for:
        1. Analysis pass (loudnorm filter with print_format=json)
        2. Normalization pass (loudnorm with measured values)
        """
        ...
    
    def build_master(
        self,
        input_path: Path,
        output_path: Path,
        preset: dict,
    ) -> list[str]:
        """
        Build audio mastering command from preset.
        
        Applies in order:
        1. EQ (if specified)
        2. Compressor (if specified)
        3. De-esser (if specified)
        4. Limiter (if specified)
        5. Loudness normalization
        """
        ...
    
    def build_mux(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        audio_offset: Decimal = Decimal(0),
    ) -> list[str]:
        """Build command to mux video and audio."""
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_path),
            '-i', str(audio_path),
        ]
        if audio_offset != 0:
            cmd.extend(['-itsoffset', str(audio_offset)])
        cmd.extend([
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            str(output_path),
        ])
        return cmd
    
    def _build_clip_input(self, clip: Clip, index: int) -> tuple[list[str], str]:
        """
        Build input arguments for a single clip.
        
        Returns:
            Tuple of (input arguments, stream label)
        """
        ...
    
    def _build_fade_filter(self, effect: FadeIn | FadeOut, clip: Clip) -> str:
        """Build fade filter string."""
        ...
    
    def _build_crossfade_filter(
        self,
        clip_a: Clip,
        clip_b: Clip,
        label_a: str,
        label_b: str,
        overlap: Decimal,
    ) -> tuple[str, str]:
        """
        Build xfade filter for video crossfade.
        
        Returns:
            Tuple of (filter string, output label)
        """
        ...
```

### File: `src/mediforge/backends/executor.py`

```python
"""Command execution with dry-run and progress support."""

import subprocess
from pathlib import Path
from typing import Callable

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
        self.logger.debug(f"Executing: {' '.join(command)}")
        
        if self.dry_run:
            print(" ".join(command))
            return subprocess.CompletedProcess(command, 0, "", "")
        
        ...
    
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
        ...


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
        if line.startswith("out_time_ms="):
            try:
                ms = int(line.split("=")[1])
                self.current_time = ms / 1_000_000
                return (self.current_time / self.expected_duration) * 100
            except (ValueError, IndexError):
                pass
        return None
```

---

## Plugin System

### File: `src/mediforge/plugins/__init__.py`

```python
"""Plugin discovery and registration."""

import importlib
import pkgutil
from pathlib import Path
from typing import Callable

import click


def discover_plugins(parent: click.Group) -> None:
    """
    Discover and register all plugins.
    
    Scans the plugins directory for modules with a `register` function
    and calls them with the parent CLI group.
    
    Args:
        parent: Root CLI group to register commands under
    """
    plugins_path = Path(__file__).parent
    
    for loader, name, is_pkg in pkgutil.iter_modules([str(plugins_path)]):
        if name.startswith('_'):
            continue
        
        module = importlib.import_module(f'mediforge.plugins.{name}')
        
        if hasattr(module, 'register'):
            module.register(parent)


def create_command_group(name: str, help_text: str) -> tuple[click.Group, Callable]:
    """
    Create a command group for a plugin domain.
    
    Returns:
        Tuple of (group, register function)
    
    Usage in plugin __init__.py:
        group, register = create_command_group('video', 'Video processing commands')
        
        @group.command()
        def compose(...):
            ...
    """
    group = click.Group(name=name, help=help_text)
    
    def register(parent: click.Group):
        parent.add_command(group)
    
    return group, register
```

### File: `src/mediforge/plugins/video/__init__.py`

```python
"""Video processing plugin."""

import click

from . import compose, edit


@click.group()
def video():
    """Video processing commands."""
    pass


video.add_command(compose.compose)
video.add_command(edit.edit)


def register(parent: click.Group):
    parent.add_command(video)
```

### File: `src/mediforge/plugins/video/compose.py`

```python
"""Video composition from scenario file."""

from pathlib import Path

import click

from mediforge.core.scenario import ScenarioParser
from mediforge.core.errors import ValidationError, FFmpegError
from mediforge.backends.ffmpeg import FFmpegCommandBuilder
from mediforge.backends.executor import CommandExecutor
from mediforge.utils.tempfiles import TempDirectory
from mediforge.utils.logging import get_logger, LogLevel


@click.command()
@click.argument('scenario', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path))
@click.option('--dry-run', is_flag=True, help='Print commands without executing')
@click.option('--preview', is_flag=True, help='Generate low-quality preview')
@click.option('--progress', is_flag=True, help='Show progress bar')
@click.option('--keep-temp', is_flag=True, help='Preserve intermediate files')
@click.pass_context
def compose(
    ctx,
    scenario: Path,
    output: Path,
    dry_run: bool,
    preview: bool,
    progress: bool,
    keep_temp: bool,
):
    """
    Compose video from scenario file.
    
    SCENARIO is a YAML file defining the timeline with clips, effects,
    and output settings.
    
    Example:
    
        mediforge video compose project.yaml -o output.mp4
    """
    log_level = ctx.obj.get('log_level', 'warning')
    logger = get_logger(__name__, log_level)
    
    # Parse scenario
    logger.info(f"Parsing scenario: {scenario}")
    parser = ScenarioParser()
    try:
        scene = parser.parse(scenario)
    except ValidationError as e:
        raise click.ClickException(str(e))
    
    if scene.type != 'video':
        raise click.ClickException(
            f"Expected video scenario, got: {scene.type}"
        )
    
    # Build commands
    builder = FFmpegCommandBuilder()
    
    with TempDirectory(keep=keep_temp or dry_run) as temp_dir:
        logger.debug(f"Temp directory: {temp_dir}")
        
        # ... implementation continues
        # 1. Process each clip to intermediate files
        # 2. Build concat file or complex filter
        # 3. Execute final composition
        
        pass
```

---

## CLI Entry Point

### File: `src/mediforge/cli.py`

```python
"""Main CLI entry point."""

import click

from .plugins import discover_plugins
from .utils.logging import configure_logging, LogLevel


@click.group()
@click.option(
    '--log-level',
    type=click.Choice(['error', 'warning', 'info', 'debug']),
    default='warning',
    help='Logging verbosity level',
)
@click.version_option()
@click.pass_context
def cli(ctx, log_level: str):
    """
    Mediforge - Command-line media processing toolkit.
    
    Compose videos and audio from scenario files, normalize loudness,
    apply mastering presets, and more.
    """
    ctx.ensure_object(dict)
    ctx.obj['log_level'] = log_level
    configure_logging(log_level)


# Discover and register all plugins
discover_plugins(cli)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
```

---

## Configuration and Presets

### File: `src/mediforge/config/defaults.py`

```python
"""Built-in default configurations and presets."""

PREVIEW_SETTINGS = {
    'video': {
        'resolution': (640, 360),
        'framerate': 15,
        'crf': 35,
        'preset': 'ultrafast',
    },
    'audio': {
        'sample_rate': 22050,
        'bitrate': '64k',
    },
}

MASTERING_PRESETS = {
    'streaming': {
        'target_lufs': -14.0,
        'true_peak': -1.0,
        'compressor': {
            'threshold': -18,
            'ratio': 3,
            'attack': 10,
            'release': 100,
        },
        'limiter': {
            'ceiling': -1.0,
        },
        'eq': {
            'low_shelf': {'freq': 80, 'gain': 1.5},
            'high_shelf': {'freq': 12000, 'gain': 0.5},
        },
    },
    'podcast': {
        'target_lufs': -16.0,
        'true_peak': -1.5,
        'compressor': {
            'threshold': -20,
            'ratio': 4,
            'attack': 5,
            'release': 50,
        },
        'de_esser': {
            'frequency': 6000,
            'threshold': -30,
        },
    },
    'broadcast': {
        'target_lufs': -23.0,
        'true_peak': -2.0,
        'compressor': {
            'threshold': -24,
            'ratio': 2,
            'attack': 20,
            'release': 200,
        },
    },
    'music': {
        'target_lufs': -14.0,
        'true_peak': -1.0,
        'compressor': {
            'threshold': -12,
            'ratio': 2,
            'attack': 30,
            'release': 150,
        },
        'limiter': {
            'ceiling': -0.3,
        },
    },
}

SUPPORTED_FORMATS = {
    'video': {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'},
    'audio': {'.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a', '.opus'},
    'image': {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.bmp', '.gif'},
}

DEFAULT_VIDEO_OUTPUT = {
    'resolution': '1920x1080',
    'framerate': 30,
    'codec': 'libx264',
    'crf': 18,
    'preset': 'medium',
    'pixel_format': 'yuv420p',
}

DEFAULT_AUDIO_OUTPUT = {
    'sample_rate': 48000,
    'channels': 2,
    'codec': 'pcm_s24le',
}
```

### File: `src/mediforge/config/loader.py`

```python
"""Configuration loading and merging."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .defaults import MASTERING_PRESETS


def get_config_paths() -> list[Path]:
    """
    Get configuration file search paths in priority order.
    
    Returns:
        List of paths to check for config files
    """
    paths = []
    
    # User config
    user_config = Path.home() / '.config' / 'mediforge' / 'config.yaml'
    if user_config.exists():
        paths.append(user_config)
    
    # Project config
    project_config = Path.cwd() / '.mediforge.yaml'
    if project_config.exists():
        paths.append(project_config)
    
    return paths


def load_config() -> dict[str, Any]:
    """
    Load and merge configuration from all sources.
    
    Priority (highest to lowest):
    1. Project config (.mediforge.yaml in cwd)
    2. User config (~/.config/mediforge/config.yaml)
    3. Built-in defaults
    """
    ...


def get_mastering_preset(name: str) -> dict[str, Any]:
    """
    Get mastering preset by name.
    
    Args:
        name: Preset name
        
    Returns:
        Preset configuration dict
        
    Raises:
        ConfigurationError: If preset not found
    """
    config = load_config()
    presets = {**MASTERING_PRESETS, **config.get('mastering_presets', {})}
    
    if name not in presets:
        available = ', '.join(sorted(presets.keys()))
        raise ConfigurationError(
            f"Unknown preset: {name}. Available: {available}"
        )
    
    return presets[name]
```

---

## Utility Modules

### File: `src/mediforge/utils/tempfiles.py`

```python
"""Temporary file and directory management."""

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Iterator

from contextlib import contextmanager


class TempDirectory:
    """
    Managed temporary directory with conditional cleanup.
    
    Usage:
        with TempDirectory(keep=False) as path:
            # Use path for intermediate files
            ...
        # Directory is deleted unless keep=True or error occurred
    """
    
    def __init__(
        self,
        keep: bool = False,
        prefix: str = "mediforge-",
        base_dir: Path | None = None,
    ):
        self.keep = keep
        self.prefix = prefix
        self.base_dir = base_dir
        self.path: Path | None = None
        self._error_occurred = False
    
    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(
            prefix=self.prefix,
            dir=self.base_dir,
        ))
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._error_occurred = True
        
        if self.path and self.path.exists():
            if self.keep or self._error_occurred:
                print(f"Intermediate files preserved at: {self.path}")
            else:
                shutil.rmtree(self.path)
        
        return False  # Don't suppress exceptions
    
    def create_subdir(self, name: str) -> Path:
        """Create a subdirectory within the temp directory."""
        subdir = self.path / name
        subdir.mkdir(exist_ok=True)
        return subdir


def generate_temp_filename(prefix: str, suffix: str) -> str:
    """Generate a unique temporary filename."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
```

### File: `src/mediforge/utils/logging.py`

```python
"""Logging configuration."""

import logging
import os
import sys
from enum import Enum


class LogLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


LEVEL_MAP = {
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
}


def configure_logging(level: str) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level name (error, warning, info, debug)
    """
    # Check environment variable override
    env_level = os.environ.get('MEDIFORGE_LOG_LEVEL', '').lower()
    if env_level in LEVEL_MAP:
        level = env_level
    
    log_level = LEVEL_MAP.get(level, logging.WARNING)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s' if log_level >= logging.WARNING
               else '%(levelname)s [%(name)s]: %(message)s',
        stream=sys.stderr,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        level: Optional level override
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(LEVEL_MAP.get(level, logging.WARNING))
    return logger
```

---

## pyproject.toml

```toml
[project]
name = "mediforge"
version = "0.1.0"
description = "Command-line media processing toolkit"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Konstantin" }
]
keywords = ["video", "audio", "ffmpeg", "media", "cli"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Video",
    "Topic :: Multimedia :: Sound/Audio",
]

dependencies = [
    "click>=8.0",
    "pydantic>=2.0",
    "ruamel.yaml>=0.18",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
]

[project.scripts]
mediforge = "mediforge.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mediforge"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
```

---

## Implementation Phases

### Phase 1: Foundation (Core + Minimal CLI)

**Goal:** Working skeleton with `mediforge info <file>` command.

**Files to implement:**
1. `pyproject.toml`
2. `src/mediforge/__init__.py`
3. `src/mediforge/cli.py`
4. `src/mediforge/core/timecode.py`
5. `src/mediforge/core/errors.py`
6. `src/mediforge/core/probe.py`
7. `src/mediforge/plugins/__init__.py`
8. `src/mediforge/plugins/info/__init__.py`
9. `src/mediforge/utils/logging.py`

**Tests:**
- `tests/test_timecode.py`
- `tests/test_probe.py`

**Verification:**
```bash
pip install -e .
mediforge --help
mediforge info sample.mp4
```

---

### Phase 2: Video Composition

**Goal:** Working `mediforge video compose` with basic timeline support.

**Files to implement:**
1. `src/mediforge/core/models.py`
2. `src/mediforge/core/scenario.py`
3. `src/mediforge/core/validation.py`
4. `src/mediforge/backends/ffmpeg.py`
5. `src/mediforge/backends/executor.py`
6. `src/mediforge/plugins/video/__init__.py`
7. `src/mediforge/plugins/video/compose.py`
8. `src/mediforge/utils/tempfiles.py`

**Scope limitations for Phase 2:**
- Support image and video inputs
- Support fade in/out effects
- No crossfades yet (defer to Phase 2b)
- No speed adjustment yet

**Tests:**
- `tests/test_models.py`
- `tests/test_scenario.py`
- `tests/test_video_compose.py` (integration)

**Verification:**
```bash
mediforge video compose tests/fixtures/scenarios/simple_video.yaml -o out.mp4
mediforge video compose scenario.yaml -o out.mp4 --dry-run
mediforge video compose scenario.yaml -o out.mp4 --preview
```

---

### Phase 2b: Advanced Video Features

**Goal:** Crossfades, speed adjustment, full effects support.

**Updates:**
1. Extend `ffmpeg.py` with crossfade filter construction
2. Add speed adjustment to clip processing
3. Implement `--progress` flag

**Tests:**
- `tests/test_ffmpeg_filters.py`
- `tests/test_crossfade.py`

---

### Phase 3: Audio Composition

**Goal:** Working `mediforge audio compose` with volume and fades.

**Files to implement:**
1. `src/mediforge/plugins/audio/__init__.py`
2. `src/mediforge/plugins/audio/compose.py`

**Tests:**
- `tests/test_audio_compose.py`

---

### Phase 4: Audio Processing Tools

**Goal:** Working `audio normalize` and `audio master` commands.

**Files to implement:**
1. `src/mediforge/plugins/audio/normalize.py`
2. `src/mediforge/plugins/audio/master.py`
3. `src/mediforge/config/defaults.py`
4. `src/mediforge/config/loader.py`

**Tests:**
- `tests/test_normalize.py`
- `tests/test_master.py`

---

### Phase 5: Muxing and Polish

**Goal:** Working `mediforge mux`, documentation, full test coverage.

**Files to implement:**
1. `src/mediforge/plugins/mux/__init__.py`
2. `docs/usage.md`
3. `docs/scenario-format.md`
4. `README.md`

**Final verification:**
- Full workflow: compose video → compose audio → mux
- All commands with --dry-run
- All commands with --progress
- Error handling for invalid inputs

---

## Test Fixtures

Create minimal test media files:

```bash
# Generate 1-second test video (no audio)
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=30 \
       -c:v libx264 -pix_fmt yuv420p tests/fixtures/sample_video.mp4

# Generate 1-second test audio
ffmpeg -f lavfi -i sine=frequency=440:duration=1 \
       -c:a pcm_s16le tests/fixtures/sample_audio.wav

# Generate test image
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 \
       -frames:v 1 tests/fixtures/sample_image.png
```

---

## Appendix: Example Scenario Files

### Video Composition Scenario

```yaml
# tests/fixtures/scenarios/valid_video.yaml
version: 1
type: video

output:
  resolution: 1920x1080
  framerate: 30
  codec: h264
  crf: 18

timeline:
  - start: "0:00:00.000"
    end: "0:00:05.000"
    type: image
    source: ../sample_image.png
    fade_in: 1.0
    fade_out: 1.0

  - start: "0:00:04.000"
    end: "0:00:10.000"
    type: video
    source: ../sample_video.mp4
    fade_in: 1.0
    fade_out: 1.0
```

### Audio Composition Scenario

```yaml
# tests/fixtures/scenarios/valid_audio.yaml
version: 1
type: audio

output:
  sample_rate: 48000
  channels: 2
  codec: pcm_s24le

timeline:
  - start: "0:00:00.000"
    end: "0:00:10.000"
    source: ../background.wav
    volume: 0.5
    fade_in: 2.0
    fade_out: 2.0

  - start: "0:00:02.000"
    end: "0:00:08.000"
    source: ../voiceover.wav
    volume: 1.0
```

---

## Notes for Implementation

1. **FFmpeg filter graph complexity**: Video crossfades with multiple overlapping clips require careful filter graph construction. Consider using the `concat` demuxer for simpler cases (no overlaps) and complex filtergraphs only when needed.

2. **Two-pass normalization**: The `loudnorm` filter requires a first pass to measure loudness, then a second pass to apply correction. Store analysis JSON in temp directory.

3. **Image duration**: When using images in video, ffmpeg needs `-loop 1 -t <duration>` or `-framerate 1 -loop 1` depending on filter approach.

4. **Progress parsing**: FFmpeg's `-progress pipe:1` outputs key=value pairs. Parse `out_time_ms` for progress percentage.

5. **Error recovery**: When FFmpeg fails, parse stderr for common error patterns and provide actionable messages.
