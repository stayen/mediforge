"""Tests for scenario parsing."""

from decimal import Decimal
from pathlib import Path

import pytest

from mediforge.core.scenario import ScenarioParser
from mediforge.core.errors import ValidationError, MediaFileError
from mediforge.core.models import MediaType


class TestScenarioParser:
    """Tests for ScenarioParser class."""

    def test_parse_valid_video_scenario(self, fixtures_dir: Path, sample_image: Path, sample_video: Path):
        """Test parsing a valid video scenario."""
        scenario_path = fixtures_dir / "scenarios" / "valid_video.yaml"

        parser = ScenarioParser()
        scenario = parser.parse(scenario_path)

        assert scenario.version == 1
        assert scenario.type == "video"
        assert len(scenario.timeline.clips) == 2
        assert scenario.output.resolution == (320, 240)

    def test_parse_missing_file(self, tmp_path: Path):
        """Test that parsing nonexistent file raises FileNotFoundError."""
        parser = ScenarioParser()

        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "nonexistent.yaml")

    def test_parse_empty_file(self, tmp_path: Path):
        """Test that parsing empty file raises ValidationError."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        parser = ScenarioParser()

        with pytest.raises(ValidationError, match="Empty scenario file"):
            parser.parse(empty_file)

    def test_parse_missing_timeline(self, tmp_path: Path):
        """Test that missing timeline raises ValidationError."""
        bad_file = tmp_path / "no_timeline.yaml"
        bad_file.write_text("version: 1\ntype: video\n")

        parser = ScenarioParser()

        with pytest.raises(ValidationError, match="Missing required field.*timeline"):
            parser.parse(bad_file)

    def test_parse_invalid_type(self, tmp_path: Path):
        """Test that invalid scenario type raises ValidationError."""
        bad_file = tmp_path / "bad_type.yaml"
        bad_file.write_text("""
version: 1
type: invalid
timeline:
  - start: "0:00:00"
    end: "0:00:01"
    source: test.mp4
""")

        parser = ScenarioParser()

        with pytest.raises(ValidationError, match="Invalid scenario type"):
            parser.parse(bad_file)

    def test_parse_invalid_timecode(self, tmp_path: Path, sample_video: Path):
        """Test that invalid timecode raises ValidationError."""
        bad_file = tmp_path / "bad_timecode.yaml"
        bad_file.write_text(f"""
version: 1
type: video
timeline:
  - start: "invalid"
    end: "0:00:01"
    source: {sample_video}
""")

        parser = ScenarioParser()

        with pytest.raises(ValidationError, match="Invalid start timecode"):
            parser.parse(bad_file)

    def test_parse_missing_source(self, tmp_path: Path):
        """Test that missing source file raises MediaFileError."""
        bad_file = tmp_path / "missing_source.yaml"
        bad_file.write_text("""
version: 1
type: video
timeline:
  - start: "0:00:00"
    end: "0:00:01"
    source: nonexistent.mp4
""")

        parser = ScenarioParser()

        with pytest.raises(MediaFileError, match="Source file not found"):
            parser.parse(bad_file)

    def test_parse_clip_with_effects(self, fixtures_dir: Path, sample_image: Path):
        """Test parsing clips with effects."""
        scenario_path = fixtures_dir / "scenarios" / "valid_video.yaml"

        parser = ScenarioParser()
        scenario = parser.parse(scenario_path)

        # First clip should have fade effects
        clip = scenario.timeline.clips[0]
        fade_in = clip.get_fade_in()
        fade_out = clip.get_fade_out()

        assert fade_in is not None
        assert fade_in.duration == Decimal("0.5")
        assert fade_out is not None
        assert fade_out.duration == Decimal("0.5")

    def test_relative_paths(self, tmp_path: Path, sample_video: Path):
        """Test that relative paths are resolved correctly."""
        # Create scenario in a subdirectory referencing file in parent
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Copy sample video to tmp_path
        import shutil
        video_copy = tmp_path / "video.mp4"
        shutil.copy(sample_video, video_copy)

        scenario_file = subdir / "scenario.yaml"
        scenario_file.write_text(f"""
version: 1
type: video
timeline:
  - start: "0:00:00"
    end: "0:00:01"
    source: ../video.mp4
""")

        parser = ScenarioParser()
        scenario = parser.parse(scenario_file)

        assert len(scenario.timeline.clips) == 1
        assert scenario.timeline.clips[0].asset.path == video_copy.resolve()
