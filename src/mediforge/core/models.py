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

    def __post_init__(self) -> None:
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
        """Construct MediaAsset from probe data (get_media_info output)."""
        media_type_str = probe_data.get('media_type', 'unknown')
        try:
            media_type = MediaType(media_type_str)
        except ValueError:
            media_type = MediaType.VIDEO  # Default to video for unknown types

        asset = cls(
            path=path,
            type=media_type,
            duration=probe_data.get('duration'),
        )

        if probe_data.get('video'):
            video = probe_data['video']
            asset.width = video.get('width')
            asset.height = video.get('height')
            asset.framerate = video.get('framerate')
            asset.codec = video.get('codec_name')

        if probe_data.get('audio'):
            audio = probe_data['audio']
            asset.sample_rate = audio.get('sample_rate')
            asset.channels = audio.get('channels')
            if not asset.codec:
                asset.codec = audio.get('codec_name')

        return asset


@dataclass
class Effect:
    """Base class for effects applied to clips."""

    pass


@dataclass
class FadeIn(Effect):
    """Fade in effect at the start of a clip."""

    duration: Decimal


@dataclass
class FadeOut(Effect):
    """Fade out effect at the end of a clip."""

    duration: Decimal


@dataclass
class VolumeAdjust(Effect):
    """Adjust volume level."""

    level: Decimal  # 1.0 = original, 0.5 = half, 2.0 = double


@dataclass
class SpeedAdjust(Effect):
    """Adjust playback speed."""

    factor: Decimal  # 1.0 = original, 0.5 = half speed, 2.0 = double speed


@dataclass
class Clip:
    """A segment of media placed on a timeline."""

    asset: MediaAsset
    timeline_range: TimeRange
    source_offset: Decimal = field(default_factory=lambda: Decimal(0))
    speed: Decimal = field(default_factory=lambda: Decimal(1))
    effects: list[Effect] = field(default_factory=list)

    @property
    def source_duration(self) -> Decimal:
        """Duration in source media time (accounting for speed)."""
        return self.timeline_range.duration * self.speed

    def get_fade_in(self) -> Optional[FadeIn]:
        """Get fade in effect if present."""
        for effect in self.effects:
            if isinstance(effect, FadeIn):
                return effect
        return None

    def get_fade_out(self) -> Optional[FadeOut]:
        """Get fade out effect if present."""
        for effect in self.effects:
            if isinstance(effect, FadeOut):
                return effect
        return None

    def get_volume(self) -> Decimal:
        """Get volume level (default 1.0)."""
        for effect in self.effects:
            if isinstance(effect, VolumeAdjust):
                return effect.level
        return Decimal(1)


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
        """
        Detect overlapping clips that require crossfade.

        Returns:
            List of tuples (clip_a, clip_b, overlap_duration) where clip_a
            ends after clip_b starts.
        """
        crossfades: list[tuple[Clip, Clip, Decimal]] = []

        # Sort clips by start time
        sorted_clips = sorted(self.clips, key=lambda c: c.timeline_range.start)

        for i, clip_a in enumerate(sorted_clips):
            for clip_b in sorted_clips[i + 1:]:
                # Check if clip_b starts before clip_a ends
                if clip_b.timeline_range.start < clip_a.timeline_range.end:
                    overlap = clip_a.timeline_range.overlap_duration(clip_b.timeline_range)
                    if overlap > 0:
                        crossfades.append((clip_a, clip_b, overlap))
                else:
                    # No more overlaps possible with clip_a since list is sorted
                    break

        return crossfades


@dataclass
class VideoOutputSettings:
    """Settings for video output encoding."""

    resolution: tuple[int, int] = (1920, 1080)
    framerate: Decimal = field(default_factory=lambda: Decimal(30))
    codec: str = "libx264"
    crf: int = 18
    preset: str = "medium"
    pixel_format: str = "yuv420p"

    @classmethod
    def from_dict(cls, data: dict) -> 'VideoOutputSettings':
        """Create from dictionary (e.g., from YAML)."""
        settings = cls()

        if 'resolution' in data:
            res = data['resolution']
            if isinstance(res, str):
                w, h = res.lower().split('x')
                settings.resolution = (int(w), int(h))
            else:
                settings.resolution = tuple(res)

        if 'framerate' in data:
            settings.framerate = Decimal(str(data['framerate']))

        if 'codec' in data:
            codec = data['codec']
            # Normalize codec names
            codec_map = {
                'h264': 'libx264',
                'h.264': 'libx264',
                'x264': 'libx264',
                'h265': 'libx265',
                'h.265': 'libx265',
                'hevc': 'libx265',
                'x265': 'libx265',
            }
            settings.codec = codec_map.get(codec.lower(), codec)

        if 'crf' in data:
            settings.crf = int(data['crf'])

        if 'preset' in data:
            settings.preset = data['preset']

        if 'pixel_format' in data:
            settings.pixel_format = data['pixel_format']

        return settings


@dataclass
class AudioOutputSettings:
    """Settings for audio output encoding."""

    sample_rate: int = 48000
    channels: int = 2
    codec: str = "pcm_s24le"
    bitrate: Optional[str] = None  # For lossy codecs

    @classmethod
    def from_dict(cls, data: dict) -> 'AudioOutputSettings':
        """Create from dictionary (e.g., from YAML)."""
        settings = cls()

        if 'sample_rate' in data:
            settings.sample_rate = int(data['sample_rate'])

        if 'channels' in data:
            settings.channels = int(data['channels'])

        if 'codec' in data:
            settings.codec = data['codec']

        if 'bitrate' in data:
            settings.bitrate = str(data['bitrate'])

        return settings


@dataclass
class Scenario:
    """Complete scenario for media composition."""

    version: int
    type: Literal["video", "audio"]
    timeline: Timeline
    output: VideoOutputSettings | AudioOutputSettings
    source_file: Optional[Path] = None  # For error reporting
