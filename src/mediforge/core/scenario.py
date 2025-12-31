"""YAML scenario parsing with line number preservation."""

from decimal import Decimal
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .errors import ValidationError, SourceLocation, MediaFileError
from .models import (
    Scenario, Timeline, Clip, MediaAsset, MediaType,
    TimeRange, Effect, FadeIn, FadeOut, VolumeAdjust,
    VideoOutputSettings, AudioOutputSettings,
)
from .timecode import parse_timecode
from .probe import get_media_info


class ScenarioParser:
    """
    Parser for YAML scenario files with line number tracking.

    Usage:
        parser = ScenarioParser()
        scenario = parser.parse(Path("scenario.yaml"))
    """

    SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'}
    SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a', '.opus'}
    SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.bmp', '.gif'}

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
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")

        with open(path) as f:
            try:
                data = self.yaml.load(f)
            except Exception as e:
                raise ValidationError(
                    message=f"Failed to parse YAML: {e}",
                    location=SourceLocation(file=path, line=1),
                )

        if data is None:
            raise ValidationError(
                message="Empty scenario file",
                location=SourceLocation(file=path, line=1),
            )

        # Validate required fields
        self._validate_required_fields(data, path)

        # Parse scenario type
        scenario_type = data.get('type', 'video')
        if scenario_type not in ('video', 'audio'):
            line = self._get_line_number(data, 'type', path)
            raise ValidationError(
                message="Invalid scenario type",
                location=SourceLocation(file=path, line=line),
                expected="'video' or 'audio'",
                found=scenario_type,
            )

        # Parse output settings
        output_data = data.get('output', {})
        if scenario_type == 'video':
            output = VideoOutputSettings.from_dict(output_data)
        else:
            output = AudioOutputSettings.from_dict(output_data)

        # Parse timeline
        timeline_data = data.get('timeline', [])
        if not timeline_data:
            raise ValidationError(
                message="Timeline cannot be empty",
                location=SourceLocation(file=path, line=1),
            )

        clips = []
        for i, clip_data in enumerate(timeline_data):
            clip = self._parse_clip(clip_data, i, scenario_type, path)
            clips.append(clip)

        timeline = Timeline(clips=clips)

        return Scenario(
            version=data.get('version', 1),
            type=scenario_type,
            timeline=timeline,
            output=output,
            source_file=path,
        )

    def _validate_required_fields(self, data: dict, path: Path) -> None:
        """Validate that required fields are present."""
        if 'timeline' not in data:
            raise ValidationError(
                message="Missing required field: 'timeline'",
                location=SourceLocation(file=path, line=1),
            )

    def _get_line_number(self, data: Any, key: str, path: Path) -> int:
        """Get line number for a key in YAML data."""
        if isinstance(data, CommentedMap):
            if key in data:
                lc = data.lc
                if hasattr(lc, 'key'):
                    pos = lc.key(key)
                    if pos:
                        return pos[0] + 1  # 1-based line numbers
        return 1

    def _parse_clip(
        self,
        data: dict,
        index: int,
        scenario_type: str,
        scenario_path: Path,
    ) -> Clip:
        """Parse and validate a single clip definition."""
        line = 1
        if isinstance(data, CommentedMap) and hasattr(data, 'lc'):
            line = data.lc.line + 1

        # Required fields
        for field in ('start', 'end', 'source'):
            if field not in data:
                raise ValidationError(
                    message=f"Missing required field: '{field}' in clip {index + 1}",
                    location=SourceLocation(file=scenario_path, line=line),
                )

        # Parse timecodes
        try:
            start = parse_timecode(str(data['start']))
        except ValueError as e:
            raise ValidationError(
                message=f"Invalid start timecode in clip {index + 1}: {e}",
                location=SourceLocation(file=scenario_path, line=line),
            )

        try:
            end = parse_timecode(str(data['end']))
        except ValueError as e:
            raise ValidationError(
                message=f"Invalid end timecode in clip {index + 1}: {e}",
                location=SourceLocation(file=scenario_path, line=line),
            )

        # Create time range
        try:
            timeline_range = TimeRange(start=start, end=end)
        except ValueError as e:
            raise ValidationError(
                message=f"Invalid time range in clip {index + 1}: {e}",
                location=SourceLocation(file=scenario_path, line=line),
            )

        # Resolve source path
        source_path = self._resolve_source(str(data['source']), scenario_path)

        # Detect media type from file or explicit declaration
        if 'type' in data:
            try:
                media_type = MediaType(data['type'])
            except ValueError:
                raise ValidationError(
                    message=f"Invalid media type in clip {index + 1}",
                    location=SourceLocation(file=scenario_path, line=line),
                    expected="'video', 'audio', or 'image'",
                    found=data['type'],
                )
        else:
            media_type = self._detect_media_type(source_path)

        # Probe the file
        try:
            probe_data = get_media_info(source_path)
        except Exception as e:
            raise MediaFileError(
                message=f"Failed to probe media file in clip {index + 1}: {e}",
                path=source_path,
                scenario_location=SourceLocation(file=scenario_path, line=line),
            )

        asset = MediaAsset.from_probe(source_path, probe_data)
        # Override type if explicitly specified
        asset.type = media_type

        # Parse optional fields
        source_offset = Decimal(0)
        if 'offset' in data:
            try:
                source_offset = parse_timecode(str(data['offset']))
            except ValueError as e:
                raise ValidationError(
                    message=f"Invalid offset timecode in clip {index + 1}: {e}",
                    location=SourceLocation(file=scenario_path, line=line),
                )

        speed = Decimal(1)
        if 'speed' in data:
            speed = Decimal(str(data['speed']))
            if speed <= 0:
                raise ValidationError(
                    message=f"Speed must be positive in clip {index + 1}",
                    location=SourceLocation(file=scenario_path, line=line),
                    expected="positive number",
                    found=str(speed),
                )
            if speed > 10:
                raise ValidationError(
                    message=f"Speed factor too large in clip {index + 1}",
                    location=SourceLocation(file=scenario_path, line=line),
                    expected="<= 10",
                    found=str(speed),
                )

        # Parse effects
        effects: list[Effect] = []

        if 'fade_in' in data and data['fade_in']:
            fade_in_dur = Decimal(str(data['fade_in']))
            if fade_in_dur > 0:
                effects.append(FadeIn(duration=fade_in_dur))

        if 'fade_out' in data and data['fade_out']:
            fade_out_dur = Decimal(str(data['fade_out']))
            if fade_out_dur > 0:
                effects.append(FadeOut(duration=fade_out_dur))

        if 'volume' in data:
            volume = Decimal(str(data['volume']))
            if volume != 1:
                effects.append(VolumeAdjust(level=volume))

        return Clip(
            asset=asset,
            timeline_range=timeline_range,
            source_offset=source_offset,
            speed=speed,
            effects=effects,
        )

    def _resolve_source(self, source: str, scenario_path: Path) -> Path:
        """Resolve source path relative to scenario file or base_path."""
        source_path = Path(source)

        if source_path.is_absolute():
            resolved = source_path
        elif self.base_path:
            resolved = self.base_path / source_path
        else:
            resolved = scenario_path.parent / source_path

        resolved = resolved.resolve()

        if not resolved.exists():
            raise MediaFileError(
                message="Source file not found",
                path=resolved,
                scenario_location=SourceLocation(file=scenario_path, line=1),
            )

        return resolved

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
            all_supported = (
                self.SUPPORTED_VIDEO_EXTENSIONS
                | self.SUPPORTED_AUDIO_EXTENSIONS
                | self.SUPPORTED_IMAGE_EXTENSIONS
            )
            raise ValidationError(
                message="Unsupported file type",
                expected=f"one of {sorted(all_supported)}",
                found=suffix,
            )

    def _create_location(self, line: int, path: Path) -> SourceLocation:
        """Create SourceLocation with context lines from file."""
        context_lines: list[str] = []

        try:
            with open(path) as f:
                all_lines = f.readlines()
                # Get line before, the line, and line after
                start = max(0, line - 2)
                end = min(len(all_lines), line + 1)
                context_lines = [l.rstrip() for l in all_lines[start:end]]
        except Exception:
            pass

        return SourceLocation(
            file=path,
            line=line,
            context_lines=context_lines,
        )
