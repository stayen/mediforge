"""FFprobe wrapper for media file analysis."""

import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from .errors import ProbeError


def probe_file(path: Path, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    """
    Probe a media file using ffprobe.

    Args:
        path: Path to the media file
        ffprobe_path: Path to ffprobe executable

    Returns:
        Dictionary with probe data including format and streams

    Raises:
        ProbeError: If ffprobe fails or file cannot be read
    """
    if not path.exists():
        raise ProbeError(f"File not found", path)

    cmd = [
        ffprobe_path,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise ProbeError("ffprobe timed out", path)
    except FileNotFoundError:
        raise ProbeError(f"ffprobe not found at: {ffprobe_path}", path)
    except OSError as e:
        raise ProbeError(f"Failed to run ffprobe: {e}", path)

    if result.returncode != 0:
        raise ProbeError(
            f"ffprobe failed with exit code {result.returncode}",
            path,
            stderr=result.stderr,
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ProbeError(f"Failed to parse ffprobe output: {e}", path)

    return data


def get_media_info(path: Path, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    """
    Get simplified media information from a file.

    Args:
        path: Path to the media file
        ffprobe_path: Path to ffprobe executable

    Returns:
        Dictionary with:
            - path: Original file path
            - format: Format name
            - duration: Duration in seconds (Decimal) or None for images
            - size: File size in bytes
            - streams: List of stream info dicts
            - video: First video stream info or None
            - audio: First audio stream info or None
    """
    probe_data = probe_file(path, ffprobe_path)

    format_info = probe_data.get('format', {})
    streams = probe_data.get('streams', [])

    # Parse duration
    duration_str = format_info.get('duration')
    duration = Decimal(duration_str) if duration_str else None

    # Find first video and audio streams
    video_stream = None
    audio_stream = None

    for stream in streams:
        codec_type = stream.get('codec_type')

        if codec_type == 'video' and video_stream is None:
            video_stream = _parse_video_stream(stream)
        elif codec_type == 'audio' and audio_stream is None:
            audio_stream = _parse_audio_stream(stream)

    # Determine media type
    format_name = format_info.get('format_name', '')

    # Image formats are identified by format name
    image_formats = {'image2', 'png_pipe', 'jpeg_pipe', 'webp_pipe', 'bmp_pipe',
                     'tiff_pipe', 'gif'}

    if any(fmt in format_name for fmt in image_formats):
        media_type = 'image'
    elif video_stream:
        # Check if it's actually an image (single frame, no duration)
        nb_frames = video_stream.get('nb_frames')
        if nb_frames == 1 and duration is None:
            media_type = 'image'
        else:
            media_type = 'video'
    elif audio_stream:
        media_type = 'audio'
    else:
        media_type = 'unknown'

    return {
        'path': path,
        'format': format_info.get('format_name', 'unknown'),
        'format_long': format_info.get('format_long_name', 'unknown'),
        'duration': duration,
        'size': int(format_info.get('size', 0)),
        'bitrate': int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else None,
        'streams': [_parse_stream(s) for s in streams],
        'video': video_stream,
        'audio': audio_stream,
        'media_type': media_type,
    }


def _parse_stream(stream: dict[str, Any]) -> dict[str, Any]:
    """Parse basic stream information."""
    return {
        'index': stream.get('index'),
        'codec_type': stream.get('codec_type'),
        'codec_name': stream.get('codec_name'),
        'codec_long_name': stream.get('codec_long_name'),
    }


def _parse_video_stream(stream: dict[str, Any]) -> dict[str, Any]:
    """Parse video stream information."""
    # Parse framerate
    fps_str = stream.get('avg_frame_rate', '0/1')
    try:
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = Decimal(num) / Decimal(den) if int(den) != 0 else Decimal(0)
        else:
            fps = Decimal(fps_str)
    except Exception:
        fps = Decimal(0)

    return {
        'index': stream.get('index'),
        'codec_name': stream.get('codec_name'),
        'codec_long_name': stream.get('codec_long_name'),
        'width': stream.get('width'),
        'height': stream.get('height'),
        'pix_fmt': stream.get('pix_fmt'),
        'framerate': fps,
        'nb_frames': int(stream.get('nb_frames', 0)) if stream.get('nb_frames') else None,
        'duration': Decimal(stream['duration']) if stream.get('duration') else None,
    }


def _parse_audio_stream(stream: dict[str, Any]) -> dict[str, Any]:
    """Parse audio stream information."""
    return {
        'index': stream.get('index'),
        'codec_name': stream.get('codec_name'),
        'codec_long_name': stream.get('codec_long_name'),
        'sample_rate': int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else None,
        'channels': stream.get('channels'),
        'channel_layout': stream.get('channel_layout'),
        'bits_per_sample': stream.get('bits_per_sample'),
        'duration': Decimal(stream['duration']) if stream.get('duration') else None,
    }


def format_media_info(info: dict[str, Any]) -> str:
    """
    Format media info as a human-readable string.

    Args:
        info: Media info dictionary from get_media_info()

    Returns:
        Formatted string for display
    """
    lines = []

    # File info
    lines.append(f"File: {info['path']}")
    lines.append(f"Format: {info['format_long']} ({info['format']})")

    # Size
    size_bytes = info['size']
    if size_bytes >= 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        size_str = f"{size_bytes / 1024:.2f} KB"
    else:
        size_str = f"{size_bytes} bytes"
    lines.append(f"Size: {size_str}")

    # Duration
    if info['duration']:
        total_secs = float(info['duration'])
        hours = int(total_secs // 3600)
        mins = int((total_secs % 3600) // 60)
        secs = total_secs % 60
        if hours > 0:
            dur_str = f"{hours}:{mins:02d}:{secs:06.3f}"
        else:
            dur_str = f"{mins}:{secs:06.3f}"
        lines.append(f"Duration: {dur_str}")

    # Bitrate
    if info['bitrate']:
        kbps = info['bitrate'] / 1000
        lines.append(f"Bitrate: {kbps:.0f} kbps")

    # Video stream
    if info['video']:
        v = info['video']
        lines.append("")
        lines.append("Video Stream:")
        lines.append(f"  Codec: {v['codec_long_name']} ({v['codec_name']})")
        lines.append(f"  Resolution: {v['width']}x{v['height']}")
        if v['pix_fmt']:
            lines.append(f"  Pixel Format: {v['pix_fmt']}")
        if v['framerate']:
            lines.append(f"  Frame Rate: {float(v['framerate']):.2f} fps")

    # Audio stream
    if info['audio']:
        a = info['audio']
        lines.append("")
        lines.append("Audio Stream:")
        lines.append(f"  Codec: {a['codec_long_name']} ({a['codec_name']})")
        if a['sample_rate']:
            lines.append(f"  Sample Rate: {a['sample_rate']} Hz")
        if a['channels']:
            ch_str = f"{a['channels']} channels"
            if a['channel_layout']:
                ch_str += f" ({a['channel_layout']})"
            lines.append(f"  Channels: {ch_str}")

    return "\n".join(lines)
