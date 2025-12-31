"""Integration tests for video compose command."""

import subprocess
from pathlib import Path

import pytest


class TestVideoComposeCommand:
    """Integration tests for mediforge video compose."""

    def test_help(self):
        """Test that help works."""
        result = subprocess.run(
            ['mediforge', 'video', 'compose', '--help'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'Compose video from scenario file' in result.stdout

    def test_dry_run(self, fixtures_dir: Path, sample_image: Path, sample_video: Path, tmp_path: Path):
        """Test dry-run mode prints command without executing."""
        scenario_path = fixtures_dir / "scenarios" / "valid_video.yaml"
        output_path = tmp_path / "output.mp4"

        result = subprocess.run(
            [
                'mediforge', 'video', 'compose',
                str(scenario_path),
                '-o', str(output_path),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'ffmpeg' in result.stdout
        assert not output_path.exists()  # Should not create file in dry-run

    def test_compose_video(self, fixtures_dir: Path, sample_image: Path, sample_video: Path, tmp_path: Path):
        """Test actual video composition."""
        scenario_path = fixtures_dir / "scenarios" / "valid_video.yaml"
        output_path = tmp_path / "output.mp4"

        result = subprocess.run(
            [
                'mediforge', 'video', 'compose',
                str(scenario_path),
                '-o', str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed with stderr: {result.stderr}"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_compose_preview(self, fixtures_dir: Path, sample_image: Path, sample_video: Path, tmp_path: Path):
        """Test preview mode generates smaller output."""
        scenario_path = fixtures_dir / "scenarios" / "valid_video.yaml"
        output_path = tmp_path / "preview.mp4"

        result = subprocess.run(
            [
                'mediforge', 'video', 'compose',
                str(scenario_path),
                '-o', str(output_path),
                '--preview',
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed with stderr: {result.stderr}"
        assert output_path.exists()

    def test_invalid_scenario_type(self, tmp_path: Path, sample_audio: Path):
        """Test that audio scenario fails for video compose."""
        scenario_path = tmp_path / "audio.yaml"
        scenario_path.write_text(f"""
version: 1
type: audio
timeline:
  - start: "0:00:00"
    end: "0:00:01"
    source: {sample_audio}
""")

        output_path = tmp_path / "output.mp4"

        result = subprocess.run(
            [
                'mediforge', 'video', 'compose',
                str(scenario_path),
                '-o', str(output_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert 'Expected video scenario' in result.stderr

    def test_missing_scenario_file(self, tmp_path: Path):
        """Test that missing scenario file fails gracefully."""
        result = subprocess.run(
            [
                'mediforge', 'video', 'compose',
                str(tmp_path / "nonexistent.yaml"),
                '-o', str(tmp_path / "output.mp4"),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
