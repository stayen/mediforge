"""Shared pytest fixtures for mediforge tests."""

import subprocess
from pathlib import Path
from typing import Generator

import pytest

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


@pytest.fixture(scope='session')
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture(scope='session')
def sample_video(fixtures_dir: Path) -> Path:
    """Generate a sample video file for testing."""
    video_path = fixtures_dir / 'sample_video.mp4'

    if not video_path.exists():
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        # Generate 1-second test video (no audio)
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=30',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            str(video_path)
        ], capture_output=True, check=True)

    return video_path


@pytest.fixture(scope='session')
def sample_audio(fixtures_dir: Path) -> Path:
    """Generate a sample audio file for testing."""
    audio_path = fixtures_dir / 'sample_audio.wav'

    if not audio_path.exists():
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        # Generate 1-second test audio
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
            '-c:a', 'pcm_s16le',
            str(audio_path)
        ], capture_output=True, check=True)

    return audio_path


@pytest.fixture(scope='session')
def sample_image(fixtures_dir: Path) -> Path:
    """Generate a sample image file for testing."""
    image_path = fixtures_dir / 'sample_image.png'

    if not image_path.exists():
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        # Generate test image
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=1',
            '-frames:v', '1',
            str(image_path)
        ], capture_output=True, check=True)

    return image_path


@pytest.fixture(scope='session')
def scenarios_dir(fixtures_dir: Path) -> Path:
    """Return the path to the scenarios fixtures directory."""
    scenarios = fixtures_dir / 'scenarios'
    scenarios.mkdir(parents=True, exist_ok=True)
    return scenarios


def pytest_configure(config: pytest.Config) -> None:
    """Ensure fixtures directory exists before tests run."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / 'scenarios').mkdir(parents=True, exist_ok=True)
