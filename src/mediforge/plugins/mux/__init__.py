"""Muxing plugin for combining video and audio."""

from decimal import Decimal
from pathlib import Path

import click
from rich.console import Console

from mediforge.core.errors import FFmpegError
from mediforge.backends.ffmpeg import FFmpegCommandBuilder
from mediforge.backends.executor import CommandExecutor
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('video', type=click.Path(exists=True, path_type=Path))
@click.argument('audio', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path),
              help='Output file path')
@click.option('--audio-offset', type=float, default=0.0,
              help='Audio offset in seconds (positive = delay audio)')
@click.option('--dry-run', is_flag=True, help='Print FFmpeg commands without executing')
@click.pass_context
def mux(
    ctx: click.Context,
    video: Path,
    audio: Path,
    output: Path,
    audio_offset: float,
    dry_run: bool,
) -> None:
    """
    Combine video and audio files.

    VIDEO is the input video file (audio will be replaced).
    AUDIO is the input audio file.

    Example:

        mediforge mux video.mp4 audio.wav -o output.mp4
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)
    console = Console()

    if not dry_run:
        console.print(f"[bold]Muxing video and audio[/bold]")
        console.print(f"  Video: {video}")
        console.print(f"  Audio: {audio}")
        if audio_offset != 0:
            console.print(f"  Audio offset: {audio_offset}s")
        console.print(f"  Output: {output}")

    builder = FFmpegCommandBuilder()
    cmd = builder.build_mux(
        video_path=video,
        audio_path=audio,
        output_path=output,
        audio_offset=Decimal(str(audio_offset)),
    )

    executor = CommandExecutor(dry_run=dry_run, log_level=log_level)

    try:
        if not dry_run:
            console.print("  Muxing...")

        executor.execute(
            command=cmd,
            stage="muxing",
        )

    except FFmpegError as e:
        raise click.ClickException(f"Muxing failed: {e}")

    if not dry_run:
        console.print(f"[green]Muxed file saved to: {output}[/green]")


def register(parent: click.Group) -> None:
    """Register the mux command with the CLI."""
    parent.add_command(mux)
