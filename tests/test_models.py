"""Tests for core data models."""

from decimal import Decimal
from pathlib import Path

import pytest

from mediforge.core.models import (
    TimeRange, MediaAsset, MediaType, Clip, Timeline,
    VideoOutputSettings, AudioOutputSettings, FadeIn, FadeOut, VolumeAdjust,
)


class TestTimeRange:
    """Tests for TimeRange class."""

    def test_create_valid_range(self):
        """Test creating a valid time range."""
        tr = TimeRange(start=Decimal(0), end=Decimal(10))
        assert tr.start == Decimal(0)
        assert tr.end == Decimal(10)
        assert tr.duration == Decimal(10)

    def test_invalid_range_raises(self):
        """Test that end <= start raises ValueError."""
        with pytest.raises(ValueError, match="End time must be greater"):
            TimeRange(start=Decimal(10), end=Decimal(5))

        with pytest.raises(ValueError):
            TimeRange(start=Decimal(5), end=Decimal(5))

    def test_overlaps(self):
        """Test overlap detection."""
        r1 = TimeRange(start=Decimal(0), end=Decimal(10))
        r2 = TimeRange(start=Decimal(5), end=Decimal(15))
        r3 = TimeRange(start=Decimal(10), end=Decimal(20))
        r4 = TimeRange(start=Decimal(20), end=Decimal(30))

        assert r1.overlaps(r2)
        assert r2.overlaps(r1)
        assert not r1.overlaps(r3)  # Adjacent but not overlapping
        assert not r1.overlaps(r4)

    def test_overlap_duration(self):
        """Test overlap duration calculation."""
        r1 = TimeRange(start=Decimal(0), end=Decimal(10))
        r2 = TimeRange(start=Decimal(5), end=Decimal(15))
        r3 = TimeRange(start=Decimal(15), end=Decimal(25))

        assert r1.overlap_duration(r2) == Decimal(5)
        assert r1.overlap_duration(r3) == Decimal(0)


class TestMediaAsset:
    """Tests for MediaAsset class."""

    def test_create_asset(self):
        """Test creating a media asset."""
        asset = MediaAsset(
            path=Path("/test/video.mp4"),
            type=MediaType.VIDEO,
            duration=Decimal("60.5"),
            width=1920,
            height=1080,
        )

        assert asset.path == Path("/test/video.mp4")
        assert asset.type == MediaType.VIDEO
        assert asset.duration == Decimal("60.5")

    def test_from_probe(self):
        """Test creating asset from probe data."""
        probe_data = {
            'media_type': 'video',
            'duration': Decimal("10.0"),
            'video': {
                'width': 320,
                'height': 240,
                'framerate': Decimal("30"),
                'codec_name': 'h264',
            },
            'audio': None,
        }

        asset = MediaAsset.from_probe(Path("/test.mp4"), probe_data)

        assert asset.type == MediaType.VIDEO
        assert asset.duration == Decimal("10.0")
        assert asset.width == 320
        assert asset.height == 240


class TestClip:
    """Tests for Clip class."""

    def test_create_clip(self):
        """Test creating a clip."""
        asset = MediaAsset(path=Path("/test.mp4"), type=MediaType.VIDEO)
        clip = Clip(
            asset=asset,
            timeline_range=TimeRange(Decimal(0), Decimal(10)),
            source_offset=Decimal(5),
            speed=Decimal(1),
        )

        assert clip.source_duration == Decimal(10)

    def test_clip_with_speed(self):
        """Test clip source duration with speed."""
        asset = MediaAsset(path=Path("/test.mp4"), type=MediaType.VIDEO)
        clip = Clip(
            asset=asset,
            timeline_range=TimeRange(Decimal(0), Decimal(10)),
            speed=Decimal(2),
        )

        assert clip.source_duration == Decimal(20)

    def test_clip_effects(self):
        """Test getting clip effects."""
        asset = MediaAsset(path=Path("/test.mp4"), type=MediaType.VIDEO)
        clip = Clip(
            asset=asset,
            timeline_range=TimeRange(Decimal(0), Decimal(10)),
            effects=[
                FadeIn(duration=Decimal(1)),
                FadeOut(duration=Decimal(2)),
                VolumeAdjust(level=Decimal("0.5")),
            ],
        )

        assert clip.get_fade_in().duration == Decimal(1)
        assert clip.get_fade_out().duration == Decimal(2)
        assert clip.get_volume() == Decimal("0.5")


class TestTimeline:
    """Tests for Timeline class."""

    def test_empty_timeline(self):
        """Test empty timeline duration."""
        timeline = Timeline()
        assert timeline.duration == Decimal(0)

    def test_timeline_duration(self):
        """Test timeline duration calculation."""
        asset = MediaAsset(path=Path("/test.mp4"), type=MediaType.VIDEO)
        timeline = Timeline(clips=[
            Clip(asset=asset, timeline_range=TimeRange(Decimal(0), Decimal(5))),
            Clip(asset=asset, timeline_range=TimeRange(Decimal(5), Decimal(15))),
        ])

        assert timeline.duration == Decimal(15)

    def test_detect_crossfades(self):
        """Test crossfade detection."""
        asset = MediaAsset(path=Path("/test.mp4"), type=MediaType.VIDEO)
        timeline = Timeline(clips=[
            Clip(asset=asset, timeline_range=TimeRange(Decimal(0), Decimal(10))),
            Clip(asset=asset, timeline_range=TimeRange(Decimal(8), Decimal(18))),
        ])

        crossfades = timeline.detect_crossfades()
        assert len(crossfades) == 1
        assert crossfades[0][2] == Decimal(2)  # 2 second overlap


class TestOutputSettings:
    """Tests for output settings classes."""

    def test_video_output_from_dict(self):
        """Test VideoOutputSettings from dictionary."""
        data = {
            'resolution': '1280x720',
            'framerate': 24,
            'codec': 'h264',
            'crf': 20,
        }

        settings = VideoOutputSettings.from_dict(data)

        assert settings.resolution == (1280, 720)
        assert settings.framerate == Decimal(24)
        assert settings.codec == 'libx264'
        assert settings.crf == 20

    def test_audio_output_from_dict(self):
        """Test AudioOutputSettings from dictionary."""
        data = {
            'sample_rate': 44100,
            'channels': 1,
            'codec': 'mp3',
            'bitrate': '192k',
        }

        settings = AudioOutputSettings.from_dict(data)

        assert settings.sample_rate == 44100
        assert settings.channels == 1
        assert settings.codec == 'mp3'
        assert settings.bitrate == '192k'
