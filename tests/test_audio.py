"""Tests for audio commands."""

import subprocess
from pathlib import Path

import pytest


class TestAudioComposeCommand:
    """Tests for mediforge audio compose."""

    def test_help(self):
        """Test that help works."""
        result = subprocess.run(
            ['mediforge', 'audio', 'compose', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Compose audio from scenario file' in result.stdout

    def test_dry_run(self, fixtures_dir: Path, sample_audio: Path, tmp_path: Path):
        """Test dry-run mode."""
        scenario_path = fixtures_dir / "scenarios" / "valid_audio.yaml"
        output_path = tmp_path / "output.wav"

        result = subprocess.run(
            [
                'mediforge', 'audio', 'compose',
                str(scenario_path),
                '-o', str(output_path),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'ffmpeg' in result.stdout
        assert not output_path.exists()

    def test_compose_audio(self, fixtures_dir: Path, sample_audio: Path, tmp_path: Path):
        """Test actual audio composition."""
        scenario_path = fixtures_dir / "scenarios" / "valid_audio.yaml"
        output_path = tmp_path / "output.wav"

        result = subprocess.run(
            [
                'mediforge', 'audio', 'compose',
                str(scenario_path),
                '-o', str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestAudioNormalizeCommand:
    """Tests for mediforge audio normalize."""

    def test_help(self):
        """Test that help works."""
        result = subprocess.run(
            ['mediforge', 'audio', 'normalize', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Normalize audio loudness' in result.stdout

    def test_dry_run(self, sample_audio: Path, tmp_path: Path):
        """Test dry-run mode."""
        output_path = tmp_path / "normalized.wav"

        result = subprocess.run(
            [
                'mediforge', 'audio', 'normalize',
                str(sample_audio),
                '-o', str(output_path),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'loudnorm' in result.stdout

    def test_normalize(self, sample_audio: Path, tmp_path: Path):
        """Test actual normalization."""
        output_path = tmp_path / "normalized.wav"

        result = subprocess.run(
            [
                'mediforge', 'audio', 'normalize',
                str(sample_audio),
                '-o', str(output_path),
                '--lufs=-16',
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert output_path.exists()


class TestAudioMasterCommand:
    """Tests for mediforge audio master."""

    def test_help(self):
        """Test that help works."""
        result = subprocess.run(
            ['mediforge', 'audio', 'master', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Apply mastering preset' in result.stdout

    def test_list_presets(self, sample_audio: Path, tmp_path: Path):
        """Test listing presets."""
        result = subprocess.run(
            ['mediforge', 'audio', 'master', str(sample_audio), '-o', str(tmp_path / 'out.wav'), '--list-presets'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'streaming' in result.stdout
        assert 'podcast' in result.stdout

    def test_master(self, sample_audio: Path, tmp_path: Path):
        """Test actual mastering."""
        output_path = tmp_path / "mastered.wav"

        result = subprocess.run(
            [
                'mediforge', 'audio', 'master',
                str(sample_audio),
                '-o', str(output_path),
                '--preset=streaming',
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert output_path.exists()


class TestMuxCommand:
    """Tests for mediforge mux."""

    def test_help(self):
        """Test that help works."""
        result = subprocess.run(
            ['mediforge', 'mux', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Combine video and audio files' in result.stdout

    def test_dry_run(self, sample_video: Path, sample_audio: Path, tmp_path: Path):
        """Test dry-run mode."""
        output_path = tmp_path / "muxed.mp4"

        result = subprocess.run(
            [
                'mediforge', 'mux',
                str(sample_video),
                str(sample_audio),
                '-o', str(output_path),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'ffmpeg' in result.stdout

    def test_mux(self, sample_video: Path, sample_audio: Path, tmp_path: Path):
        """Test actual muxing."""
        output_path = tmp_path / "muxed.mp4"

        result = subprocess.run(
            [
                'mediforge', 'mux',
                str(sample_video),
                str(sample_audio),
                '-o', str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert output_path.exists()
        assert output_path.stat().st_size > 0
