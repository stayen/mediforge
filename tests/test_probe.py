"""Tests for ffprobe wrapper."""

from decimal import Decimal
from pathlib import Path

import pytest

from mediforge.core.probe import (
    probe_file,
    get_media_info,
    format_media_info,
    ProbeError,
)
from mediforge.core.errors import ProbeError


class TestProbeFile:
    """Tests for probe_file function."""

    def test_probe_nonexistent_file(self):
        """Test that probing a nonexistent file raises ProbeError."""
        with pytest.raises(ProbeError, match="File not found"):
            probe_file(Path("/nonexistent/file.mp4"))

    def test_probe_video(self, sample_video: Path):
        """Test probing a video file."""
        result = probe_file(sample_video)

        assert 'format' in result
        assert 'streams' in result
        assert result['format']['format_name'] == 'mov,mp4,m4a,3gp,3g2,mj2'

    def test_probe_audio(self, sample_audio: Path):
        """Test probing an audio file."""
        result = probe_file(sample_audio)

        assert 'format' in result
        assert 'streams' in result
        assert 'wav' in result['format']['format_name']

    def test_probe_image(self, sample_image: Path):
        """Test probing an image file."""
        result = probe_file(sample_image)

        assert 'format' in result
        assert 'streams' in result


class TestGetMediaInfo:
    """Tests for get_media_info function."""

    def test_video_info(self, sample_video: Path):
        """Test getting info for a video file."""
        info = get_media_info(sample_video)

        assert info['path'] == sample_video
        assert info['media_type'] == 'video'
        assert info['duration'] is not None
        assert info['duration'] > 0
        assert info['video'] is not None
        assert info['video']['width'] == 320
        assert info['video']['height'] == 240

    def test_audio_info(self, sample_audio: Path):
        """Test getting info for an audio file."""
        info = get_media_info(sample_audio)

        assert info['path'] == sample_audio
        assert info['media_type'] == 'audio'
        assert info['duration'] is not None
        assert info['audio'] is not None
        assert info['audio']['sample_rate'] is not None

    def test_image_info(self, sample_image: Path):
        """Test getting info for an image file."""
        info = get_media_info(sample_image)

        assert info['path'] == sample_image
        assert info['media_type'] == 'image'
        assert info['video'] is not None  # Images have video stream
        assert info['video']['width'] == 320
        assert info['video']['height'] == 240


class TestFormatMediaInfo:
    """Tests for format_media_info function."""

    def test_format_video(self, sample_video: Path):
        """Test formatting video info."""
        info = get_media_info(sample_video)
        output = format_media_info(info)

        assert 'File:' in output
        assert 'Format:' in output
        assert 'Video Stream:' in output
        assert '320x240' in output

    def test_format_audio(self, sample_audio: Path):
        """Test formatting audio info."""
        info = get_media_info(sample_audio)
        output = format_media_info(info)

        assert 'File:' in output
        assert 'Audio Stream:' in output
        assert 'Sample Rate:' in output
