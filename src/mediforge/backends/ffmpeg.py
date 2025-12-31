"""FFmpeg command construction and filter graph building."""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..core.models import (
    Clip, Timeline, Effect, FadeIn, FadeOut, SpeedAdjust, VolumeAdjust,
    VideoOutputSettings, AudioOutputSettings, MediaType,
)


@dataclass
class FFmpegInput:
    """Represents an input file with options."""

    path: Path
    options: list[str] = field(default_factory=list)

    def to_args(self) -> list[str]:
        args = []
        if self.options:
            args.extend(self.options)
        args.extend(['-i', str(self.path)])
        return args


@dataclass
class FilterNode:
    """Node in an FFmpeg filter graph."""

    filter_name: str
    params: dict[str, str] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    def to_string(self) -> str:
        """Convert to FFmpeg filter string."""
        parts = []

        # Input labels
        for inp in self.inputs:
            parts.append(f"[{inp}]")

        # Filter name and parameters
        if self.params:
            param_str = ':'.join(f"{k}={v}" for k, v in self.params.items())
            parts.append(f"{self.filter_name}={param_str}")
        else:
            parts.append(self.filter_name)

        # Output labels
        for out in self.outputs:
            parts.append(f"[{out}]")

        return ''.join(parts)


class FilterGraph:
    """Builder for complex FFmpeg filter graphs."""

    def __init__(self):
        self._nodes: list[FilterNode] = []
        self._counter: int = 0
        self._last_output: str = ""

    def add_node(
        self,
        filter_name: str,
        params: dict[str, str] | None = None,
        inputs: list[str] | None = None,
    ) -> str:
        """
        Add a filter node and return its output label.

        Args:
            filter_name: FFmpeg filter name
            params: Filter parameters
            inputs: Input labels (default: previous output)

        Returns:
            Output label for this node
        """
        output_label = f"v{self._counter}"
        self._counter += 1

        if inputs is None:
            inputs = [self._last_output] if self._last_output else []

        node = FilterNode(
            filter_name=filter_name,
            params=params or {},
            inputs=inputs,
            outputs=[output_label],
        )

        self._nodes.append(node)
        self._last_output = output_label
        return output_label

    def build(self) -> str:
        """Build complete filter graph string."""
        return ';'.join(node.to_string() for node in self._nodes)

    def get_last_output(self) -> str:
        """Get the label of the last output."""
        return self._last_output


class FFmpegCommandBuilder:
    """
    Builds FFmpeg commands for various operations.

    This class constructs FFmpeg command-line arguments for:
    - Video/audio composition from timelines
    - Audio normalization
    - Audio mastering
    - Muxing video and audio
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def build_video_compose(
        self,
        timeline: Timeline,
        output_settings: VideoOutputSettings,
        output_path: Path,
        preview: bool = False,
    ) -> list[str]:
        """
        Build command for video composition.

        Handles:
        - Image inputs (with loop and duration)
        - Video inputs (with seeking and duration)
        - Fade effects
        - Resolution scaling/padding
        - Concatenation

        Args:
            timeline: Timeline with clips
            output_settings: Encoding settings
            output_path: Output file path
            preview: If True, use preview quality settings

        Returns:
            Complete FFmpeg command as list of arguments
        """
        if not timeline.clips:
            raise ValueError("Timeline has no clips")

        # Sort clips by start time
        sorted_clips = sorted(timeline.clips, key=lambda c: c.timeline_range.start)

        # Check for overlaps (crossfades) - not supported in Phase 2
        crossfades = timeline.detect_crossfades()
        if crossfades:
            # For Phase 2, we'll just ignore overlaps and process sequentially
            pass

        cmd = [self.ffmpeg_path, '-y']

        # Build inputs and filters for each clip
        filter_parts = []
        concat_inputs = []

        target_w, target_h = output_settings.resolution
        if preview:
            target_w, target_h = 640, 360

        for i, clip in enumerate(sorted_clips):
            input_idx = i

            # Add input with appropriate options
            if clip.asset.type == MediaType.IMAGE:
                # Image input: loop and set duration
                cmd.extend([
                    '-loop', '1',
                    '-t', str(float(clip.timeline_range.duration)),
                    '-i', str(clip.asset.path),
                ])
            else:
                # Video/audio input
                if clip.source_offset > 0:
                    cmd.extend(['-ss', str(float(clip.source_offset))])
                cmd.extend([
                    '-t', str(float(clip.source_duration)),
                    '-i', str(clip.asset.path),
                ])

            # Build filter chain for this clip
            filters = self._build_clip_filters(
                clip, input_idx, target_w, target_h, output_settings.framerate
            )
            if filters:
                filter_parts.append(filters)
                concat_inputs.append(f"[v{input_idx}]")
            else:
                concat_inputs.append(f"[{input_idx}:v]")

        # Build concat filter if multiple clips
        if len(sorted_clips) > 1:
            concat_filter = f"{''.join(concat_inputs)}concat=n={len(sorted_clips)}:v=1:a=0[outv]"
            filter_parts.append(concat_filter)
            map_label = "[outv]"
        elif filter_parts:
            # Single clip with filters
            map_label = f"[v0]"
        else:
            # Single clip without filters
            map_label = "0:v"

        # Add filter complex if needed
        if filter_parts:
            cmd.extend(['-filter_complex', ';'.join(filter_parts)])
            cmd.extend(['-map', map_label])
        else:
            cmd.extend(['-map', '0:v'])

        # Output encoding settings
        if preview:
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '35',
                '-pix_fmt', 'yuv420p',
            ])
        else:
            cmd.extend([
                '-c:v', output_settings.codec,
                '-preset', output_settings.preset,
                '-crf', str(output_settings.crf),
                '-pix_fmt', output_settings.pixel_format,
            ])

        # Frame rate
        fps = float(output_settings.framerate) if not preview else 15
        cmd.extend(['-r', str(fps)])

        # No audio
        cmd.append('-an')

        cmd.append(str(output_path))

        return cmd

    def _build_clip_filters(
        self,
        clip: Clip,
        input_idx: int,
        target_w: int,
        target_h: int,
        target_fps: Decimal,
    ) -> str:
        """Build filter chain for a single clip."""
        filters = []
        input_label = f"{input_idx}:v"
        output_label = f"v{input_idx}"

        # Scale and pad to target resolution
        scale_filter = (
            f"[{input_label}]scale={target_w}:{target_h}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1"
        )
        filters.append(scale_filter)

        # Set frame rate for images
        if clip.asset.type == MediaType.IMAGE:
            filters.append(f"fps={float(target_fps)}")

        # Fade in
        fade_in = clip.get_fade_in()
        if fade_in:
            filters.append(f"fade=t=in:st=0:d={float(fade_in.duration)}")

        # Fade out
        fade_out = clip.get_fade_out()
        if fade_out:
            start_time = float(clip.timeline_range.duration - fade_out.duration)
            if start_time >= 0:
                filters.append(f"fade=t=out:st={start_time}:d={float(fade_out.duration)}")

        if filters:
            # Join filters with commas and add output label
            return ','.join(filters) + f"[{output_label}]"
        return ""

    def build_audio_compose(
        self,
        timeline: Timeline,
        output_settings: AudioOutputSettings,
        output_path: Path,
    ) -> list[str]:
        """Build command for audio composition."""
        if not timeline.clips:
            raise ValueError("Timeline has no clips")

        sorted_clips = sorted(timeline.clips, key=lambda c: c.timeline_range.start)

        cmd = [self.ffmpeg_path, '-y']

        filter_parts = []
        amix_inputs = []

        for i, clip in enumerate(sorted_clips):
            # Add input
            if clip.source_offset > 0:
                cmd.extend(['-ss', str(float(clip.source_offset))])
            cmd.extend([
                '-t', str(float(clip.source_duration)),
                '-i', str(clip.asset.path),
            ])

            # Build audio filter chain
            filters = self._build_audio_clip_filters(clip, i)
            if filters:
                filter_parts.append(filters)
                amix_inputs.append(f"[a{i}]")
            else:
                amix_inputs.append(f"[{i}:a]")

        # Build amerge/amix filter for timeline positioning
        # For now, simple concatenation
        if len(sorted_clips) > 1:
            concat_filter = f"{''.join(amix_inputs)}concat=n={len(sorted_clips)}:v=0:a=1[outa]"
            filter_parts.append(concat_filter)
            map_label = "[outa]"
        elif filter_parts:
            map_label = "[a0]"
        else:
            map_label = "0:a"

        if filter_parts:
            cmd.extend(['-filter_complex', ';'.join(filter_parts)])
            cmd.extend(['-map', map_label])
        else:
            cmd.extend(['-map', '0:a'])

        # Output settings
        cmd.extend([
            '-c:a', output_settings.codec,
            '-ar', str(output_settings.sample_rate),
            '-ac', str(output_settings.channels),
        ])

        if output_settings.bitrate:
            cmd.extend(['-b:a', output_settings.bitrate])

        cmd.append(str(output_path))

        return cmd

    def _build_audio_clip_filters(self, clip: Clip, input_idx: int) -> str:
        """Build audio filter chain for a single clip."""
        filters = []
        input_label = f"{input_idx}:a"
        output_label = f"a{input_idx}"

        # Volume adjustment
        volume = clip.get_volume()
        if volume != 1:
            filters.append(f"volume={float(volume)}")

        # Fade in
        fade_in = clip.get_fade_in()
        if fade_in:
            filters.append(f"afade=t=in:st=0:d={float(fade_in.duration)}")

        # Fade out
        fade_out = clip.get_fade_out()
        if fade_out:
            start_time = float(clip.timeline_range.duration - fade_out.duration)
            if start_time >= 0:
                filters.append(f"afade=t=out:st={start_time}:d={float(fade_out.duration)}")

        if filters:
            return f"[{input_label}]{','.join(filters)}[{output_label}]"
        return ""

    def build_normalize_analyze(
        self,
        input_path: Path,
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
    ) -> list[str]:
        """
        Build loudness analysis command (first pass).

        Returns command that outputs loudness measurements.
        """
        return [
            self.ffmpeg_path,
            '-i', str(input_path),
            '-af', f'loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:print_format=json',
            '-f', 'null',
            '-',
        ]

    def build_normalize_apply(
        self,
        input_path: Path,
        output_path: Path,
        measured_i: float,
        measured_tp: float,
        measured_lra: float,
        measured_thresh: float,
        target_offset: float,
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
    ) -> list[str]:
        """
        Build loudness normalization command (second pass).

        Args:
            measured_*: Values from analysis pass
        """
        loudnorm_filter = (
            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:"
            f"measured_I={measured_i}:measured_TP={measured_tp}:"
            f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
            f"offset={target_offset}:linear=true"
        )

        return [
            self.ffmpeg_path,
            '-y',
            '-i', str(input_path),
            '-af', loudnorm_filter,
            str(output_path),
        ]

    def build_mux(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        audio_offset: Decimal = Decimal(0),
    ) -> list[str]:
        """Build command to mux video and audio."""
        cmd = [self.ffmpeg_path, '-y']

        if audio_offset != 0:
            cmd.extend(['-itsoffset', str(float(audio_offset))])

        cmd.extend([
            '-i', str(video_path),
            '-i', str(audio_path),
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            str(output_path),
        ])

        return cmd
