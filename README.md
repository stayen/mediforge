# Mediforge

Command-line media processing toolkit for video and audio composition. Mediforge replaces complex GUI applications (Shotcut, Ardour) for common linear media operations by orchestrating FFmpeg through human-readable YAML scenario files.

## Installation

```bash
# Install in development mode
pip install -e ".[dev]"

# Or install from source
pip install .
```

## Requirements

- Python 3.11+
- FFmpeg 5.0+ (including ffprobe)

---

## Quick Start

```bash
# Get help
mediforge --help

# Show media file info
mediforge info video.mp4

# Compose video from scenario
mediforge video compose scenario.yaml -o output.mp4

# Compose audio from scenario
mediforge audio compose scenario.yaml -o output.wav

# Normalize audio loudness
mediforge audio normalize input.wav -o output.wav --lufs=-14

# Apply mastering preset
mediforge audio master input.wav -o output.wav --preset=streaming

# Mux video and audio
mediforge mux video.mp4 audio.wav -o output.mp4
```

---

## Configuration

### Configuration File Locations

Mediforge looks for configuration files in the following locations, in order of priority (highest first):

| Priority | Location | Description |
|----------|----------|-------------|
| 1 (highest) | `.mediforge.yaml` | Project-specific config in current directory |
| 2 | `~/.config/mediforge/config.yaml` | User-wide configuration |
| 3 (lowest) | Built-in defaults | Hardcoded fallback values |

Configuration values are **deep-merged**: project config overrides user config, which overrides defaults. You can override only specific values while inheriting others.

### User Configuration File

Create `~/.config/mediforge/config.yaml` to set user-wide defaults:

```yaml
# ~/.config/mediforge/config.yaml

# Custom mastering presets (merged with built-in presets)
mastering_presets:
  my_podcast:
    target_lufs: -16.0
    true_peak: -1.5
    compressor:
      threshold: -18
      ratio: 3
      attack: 5
      release: 60
    eq:
      low_shelf:
        freq: 100
        gain: -3
      high_shelf:
        freq: 10000
        gain: 2
```

### Project Configuration File

Create `.mediforge.yaml` in your project directory for project-specific settings:

```yaml
# .mediforge.yaml

# Override or add presets for this project
mastering_presets:
  project_voice:
    target_lufs: -14.0
    true_peak: -1.0
    compressor:
      threshold: -16
      ratio: 4
      attack: 3
      release: 40
```

---

## Scenario Files

Scenario files define timelines for video or audio composition. They use YAML format with timecode notation.

### Video Scenario Example

```yaml
# video_project.yaml
version: 1
type: video

output:
  resolution: 1920x1080    # Output resolution (WxH)
  framerate: 30            # Frames per second
  codec: h264              # Video codec (h264, h265, libx264, libx265)
  crf: 18                  # Quality (0-51, lower = better, 18 = visually lossless)
  preset: medium           # Encoding speed (ultrafast, fast, medium, slow, veryslow)

timeline:
  # Image clip with fade effects
  - start: "0:00:00.000"
    end: "0:00:05.000"
    type: image
    source: assets/title.png
    fade_in: 1.0           # Fade in duration (seconds)
    fade_out: 1.0          # Fade out duration (seconds)

  # Video clip with offset
  - start: "0:00:05.000"
    end: "0:00:35.000"
    type: video
    source: clips/interview.mp4
    offset: "0:00:10.000"  # Start from 10 seconds into source
    fade_in: 0.5
    fade_out: 0.5

  # Another video clip
  - start: "0:00:35.000"
    end: "0:01:00.000"
    type: video
    source: clips/broll.mp4
    speed: 1.5             # Playback speed (0.5 = half speed, 2.0 = double)
```

### Audio Scenario Example

```yaml
# audio_project.yaml
version: 1
type: audio

output:
  sample_rate: 48000       # Sample rate in Hz
  channels: 2              # Number of channels (1 = mono, 2 = stereo)
  codec: pcm_s24le         # Audio codec (pcm_s16le, pcm_s24le, mp3, aac)
  # bitrate: 320k          # For lossy codecs only

timeline:
  # Background music (quieter)
  - start: "0:00:00.000"
    end: "0:02:00.000"
    source: audio/background.wav
    volume: 0.3            # Volume level (1.0 = original, 0.5 = half)
    fade_in: 2.0
    fade_out: 2.0

  # Voiceover (full volume)
  - start: "0:00:05.000"
    end: "0:01:30.000"
    source: audio/voiceover.wav
    volume: 1.0
    fade_in: 0.5
    fade_out: 0.5

  # Sound effect
  - start: "0:00:30.000"
    end: "0:00:32.000"
    source: audio/swoosh.wav
    volume: 0.8
```

### Timecode Format

Timecodes use the format `H:MM:SS.mmm`:
- `1:30:00.000` = 1 hour, 30 minutes
- `5:30.500` = 5 minutes, 30.5 seconds
- `45.123` = 45.123 seconds
- `0:00:00.000` = start of timeline

### Clip Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `start` | timecode | Yes | Timeline start position |
| `end` | timecode | Yes | Timeline end position |
| `source` | path | Yes | Path to source file (relative to scenario file) |
| `type` | string | No | `video`, `audio`, or `image` (auto-detected from extension) |
| `offset` | timecode | No | Start position within source file (default: 0) |
| `speed` | float | No | Playback speed multiplier (default: 1.0) |
| `volume` | float | No | Volume level for audio (default: 1.0) |
| `fade_in` | float | No | Fade-in duration in seconds |
| `fade_out` | float | No | Fade-out duration in seconds |

---

## Commands Reference

### Global Options

```
mediforge [OPTIONS] COMMAND [ARGS]...

Options:
  --log-level [error|warning|info|debug]  Logging verbosity level
  --version                               Show version and exit
  --help                                  Show help and exit
```

---

### `info` - Display Media File Information

Probe a media file and display its metadata.

```bash
mediforge info [OPTIONS] FILE
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `FILE` | Path to media file (video, audio, or image) |

**Options:**
| Option | Description |
|--------|-------------|
| `--json` | Output as JSON instead of formatted text |
| `--help` | Show help |

**Examples:**
```bash
# Display info in readable format
mediforge info video.mp4

# Output as JSON for scripting
mediforge info --json video.mp4 | jq '.duration'
```

**Output includes:**
- File format and size
- Duration and bitrate
- Video stream: codec, resolution, frame rate, pixel format
- Audio stream: codec, sample rate, channels

---

### `video` - Video Processing Commands

#### `video compose` - Compose Video from Scenario

Build a video from a YAML scenario file containing timeline definitions.

```bash
mediforge video compose [OPTIONS] SCENARIO
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `SCENARIO` | Path to YAML scenario file |

**Options:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output video file path (required) |
| `--dry-run` | Print FFmpeg commands without executing |
| `--preview` | Generate low-quality preview (640x360, 15fps) |
| `--progress` | Show progress bar during encoding |
| `--keep-temp` | Preserve intermediate files after completion |
| `--help` | Show help |

**Examples:**
```bash
# Compose video
mediforge video compose project.yaml -o output.mp4

# Preview mode (faster, lower quality)
mediforge video compose project.yaml -o preview.mp4 --preview

# See what commands would run
mediforge video compose project.yaml -o output.mp4 --dry-run

# With progress bar
mediforge video compose project.yaml -o output.mp4 --progress
```

**Supported input formats:** `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.m4v`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.bmp`, `.gif`

---

### `audio` - Audio Processing Commands

#### `audio compose` - Compose Audio from Scenario

Build an audio file from a YAML scenario file.

```bash
mediforge audio compose [OPTIONS] SCENARIO
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `SCENARIO` | Path to YAML scenario file |

**Options:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output audio file path (required) |
| `--dry-run` | Print FFmpeg commands without executing |
| `--progress` | Show progress bar during encoding |
| `--keep-temp` | Preserve intermediate files |
| `--help` | Show help |

**Example:**
```bash
mediforge audio compose audio_mix.yaml -o output.wav
```

---

#### `audio normalize` - Loudness Normalization

Normalize audio loudness using the EBU R128 standard. Performs two-pass processing for accurate results.

```bash
mediforge audio normalize [OPTIONS] INPUT_FILE
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `INPUT_FILE` | Input audio file |

**Options:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output audio file path (required) |
| `-l, --lufs FLOAT` | Target integrated loudness in LUFS (default: -14) |
| `-t, --true-peak FLOAT` | Maximum true peak in dB (default: -1) |
| `--dry-run` | Print FFmpeg commands without executing |
| `--help` | Show help |

**Examples:**
```bash
# Normalize to streaming standard (-14 LUFS)
mediforge audio normalize input.wav -o output.wav

# Normalize to broadcast standard (-23 LUFS)
mediforge audio normalize input.wav -o output.wav --lufs=-23

# Custom settings
mediforge audio normalize input.wav -o output.wav --lufs=-16 --true-peak=-2
```

**Common LUFS targets:**
| Platform | Target LUFS |
|----------|-------------|
| Spotify, YouTube, Apple Music | -14 |
| Podcasts | -16 |
| Broadcast TV (EBU R128) | -23 |

---

#### `audio master` - Apply Mastering Preset

Apply a mastering chain (EQ, compression, limiting, normalization) using built-in or custom presets.

```bash
mediforge audio master [OPTIONS] INPUT_FILE
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `INPUT_FILE` | Input audio file |

**Options:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output audio file path (required) |
| `-p, --preset NAME` | Mastering preset name (default: streaming) |
| `--list-presets` | List available presets and exit |
| `--dry-run` | Print FFmpeg commands without executing |
| `--help` | Show help |

**Examples:**
```bash
# Apply streaming preset
mediforge audio master input.wav -o output.wav --preset=streaming

# Apply podcast preset
mediforge audio master input.wav -o output.wav --preset=podcast

# List all available presets
mediforge audio master input.wav -o out.wav --list-presets
```

**Built-in Presets:**

| Preset | Target LUFS | Description |
|--------|-------------|-------------|
| `streaming` | -14 | Optimized for Spotify, YouTube, Apple Music |
| `podcast` | -16 | Voice-focused with de-esser |
| `broadcast` | -23 | EBU R128 broadcast standard |
| `music` | -14 | Gentle compression for music |
| `voice` | -16 | Enhanced clarity for speech |

---

### `mux` - Combine Video and Audio

Multiplex (combine) a video file with an audio file, replacing any existing audio.

```bash
mediforge mux [OPTIONS] VIDEO AUDIO
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `VIDEO` | Input video file |
| `AUDIO` | Input audio file |

**Options:**
| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output file path (required) |
| `--audio-offset FLOAT` | Audio offset in seconds (positive = delay audio) |
| `--dry-run` | Print FFmpeg commands without executing |
| `--help` | Show help |

**Examples:**
```bash
# Simple mux
mediforge mux video.mp4 audio.wav -o output.mp4

# Delay audio by 0.5 seconds
mediforge mux video.mp4 audio.wav -o output.mp4 --audio-offset=0.5

# Preview command
mediforge mux video.mp4 audio.wav -o output.mp4 --dry-run
```

---

## Developer Guide: Creating Plugins

Mediforge uses a plugin architecture that makes it easy to add new commands.

### Plugin Structure

Plugins live in `src/mediforge/plugins/`. Each plugin is either:
- A single Python file (e.g., `mux/__init__.py`)
- A package directory with multiple commands

### Plugin Interface

Every plugin must expose a `register(parent: click.Group)` function that adds commands to the CLI.

#### Simple Command Plugin

```python
# src/mediforge/plugins/mycommand/__init__.py
"""My custom command plugin."""

from pathlib import Path
import click
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path),
              help='Output file path')
@click.option('--dry-run', is_flag=True, help='Print commands without executing')
@click.pass_context
def mycommand(ctx: click.Context, input_file: Path, output: Path, dry_run: bool) -> None:
    """
    Brief description of my command.

    Longer description and examples go here.
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)

    logger.info(f"Processing: {input_file}")

    # Your implementation here
    if dry_run:
        print(f"Would process {input_file} -> {output}")
        return

    # ... actual processing ...


def register(parent: click.Group) -> None:
    """Register this command with the CLI."""
    parent.add_command(mycommand)
```

#### Command Group Plugin

For plugins with multiple subcommands:

```python
# src/mediforge/plugins/mygroup/__init__.py
"""My command group plugin."""

import click
from . import subcommand1, subcommand2


@click.group()
def mygroup() -> None:
    """My group of commands."""
    pass


mygroup.add_command(subcommand1.cmd1)
mygroup.add_command(subcommand2.cmd2)


def register(parent: click.Group) -> None:
    """Register the command group with the CLI."""
    parent.add_command(mygroup)
```

```python
# src/mediforge/plugins/mygroup/subcommand1.py
import click

@click.command('cmd1')
def cmd1():
    """First subcommand."""
    pass
```

### Using Core Utilities

Plugins can use these core utilities:

```python
# Logging
from mediforge.utils.logging import get_logger
logger = get_logger(__name__, log_level)
logger.debug("Debug message")
logger.info("Info message")

# Temporary directories
from mediforge.utils.tempfiles import TempDirectory
with TempDirectory(keep=keep_temp) as temp_dir:
    intermediate_file = temp_dir / "temp.mp4"
    # ... use temp_dir ...
# Auto-cleaned unless keep=True or error occurred

# FFmpeg execution
from mediforge.backends.executor import CommandExecutor
executor = CommandExecutor(dry_run=dry_run, log_level=log_level)
result = executor.execute(
    command=['ffmpeg', '-i', str(input_path), str(output_path)],
    stage="encoding",
    temp_dir=temp_dir,
)

# FFmpeg command building
from mediforge.backends.ffmpeg import FFmpegCommandBuilder
builder = FFmpegCommandBuilder()
cmd = builder.build_mux(video_path, audio_path, output_path)

# Error handling
from mediforge.core.errors import ValidationError, FFmpegError, MediaFileError
raise ValidationError("Invalid value", expected="number", found="text")

# Media probing
from mediforge.core.probe import get_media_info
info = get_media_info(Path("video.mp4"))
print(f"Duration: {info['duration']}")
```

### Plugin Discovery

Plugins are automatically discovered at startup. The discovery process:

1. Scans `src/mediforge/plugins/` for Python modules/packages
2. Skips modules starting with `_`
3. Imports each module
4. Calls `register(parent)` if the function exists

No manual registration required - just create your plugin in the plugins directory.

---

## License

MIT License
