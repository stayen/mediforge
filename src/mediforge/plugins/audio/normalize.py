"""Audio loudness normalization."""

import json
import re
from pathlib import Path

import click
from rich.console import Console

from mediforge.core.errors import FFmpegError
from mediforge.backends.ffmpeg import FFmpegCommandBuilder
from mediforge.backends.executor import CommandExecutor
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path),
              help='Output audio file path')
@click.option('--lufs', '-l', type=float, default=-14.0,
              help='Target integrated loudness in LUFS (default: -14)')
@click.option('--true-peak', '-t', type=float, default=-1.0,
              help='Maximum true peak in dB (default: -1)')
@click.option('--dry-run', is_flag=True, help='Print FFmpeg commands without executing')
@click.pass_context
def normalize(
    ctx: click.Context,
    input_file: Path,
    output: Path,
    lufs: float,
    true_peak: float,
    dry_run: bool,
) -> None:
    """
    Normalize audio loudness using EBU R128 standard.

    Performs two-pass loudness normalization:
    1. First pass analyzes the audio loudness
    2. Second pass applies normalization with measured values

    Example:

        mediforge audio normalize input.wav -o output.wav --lufs=-14
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)
    console = Console()

    builder = FFmpegCommandBuilder()
    executor = CommandExecutor(dry_run=dry_run, log_level=log_level)

    if not dry_run:
        console.print(f"[bold]Normalizing audio[/bold]")
        console.print(f"  Input: {input_file}")
        console.print(f"  Target: {lufs} LUFS, {true_peak} dB true peak")

    # First pass: analyze loudness
    analyze_cmd = builder.build_normalize_analyze(
        input_path=input_file,
        target_lufs=lufs,
        true_peak=true_peak,
    )

    if dry_run:
        console.print("# Pass 1: Analyze loudness")
        executor.execute(analyze_cmd, stage="loudness analysis")
        console.print("\n# Pass 2: Apply normalization")
        console.print("# (requires measured values from pass 1)")
        return

    try:
        if not dry_run:
            console.print("  Analyzing loudness...")

        result = executor.execute(
            command=analyze_cmd,
            stage="loudness analysis",
        )

        # Parse loudnorm output from stderr
        measured = _parse_loudnorm_output(result.stderr)
        if not measured:
            raise click.ClickException(
                "Failed to parse loudness analysis. FFmpeg may be too old."
            )

        logger.info(f"Measured loudness: {measured['input_i']:.1f} LUFS")
        if not dry_run:
            console.print(f"  Current loudness: {measured['input_i']:.1f} LUFS")

    except FFmpegError as e:
        raise click.ClickException(f"Loudness analysis failed: {e}")

    # Second pass: apply normalization
    try:
        if not dry_run:
            console.print("  Applying normalization...")

        apply_cmd = builder.build_normalize_apply(
            input_path=input_file,
            output_path=output,
            measured_i=measured['input_i'],
            measured_tp=measured['input_tp'],
            measured_lra=measured['input_lra'],
            measured_thresh=measured['input_thresh'],
            target_offset=measured['target_offset'],
            target_lufs=lufs,
            true_peak=true_peak,
        )

        executor.execute(
            command=apply_cmd,
            stage="normalization",
        )

    except FFmpegError as e:
        raise click.ClickException(f"Normalization failed: {e}")

    if not dry_run:
        console.print(f"[green]Normalized audio saved to: {output}[/green]")


def _parse_loudnorm_output(stderr: str) -> dict | None:
    """Parse loudnorm JSON output from ffmpeg stderr."""
    # Find JSON block in output
    json_match = re.search(r'\{[^}]*"input_i"[^}]*\}', stderr, re.DOTALL)
    if not json_match:
        return None

    try:
        # Clean up the JSON (ffmpeg outputs it with some quirks)
        json_str = json_match.group(0)
        # Fix common issues
        json_str = re.sub(r':\s*-inf', ': -99', json_str)
        json_str = re.sub(r':\s*inf', ': 99', json_str)

        data = json.loads(json_str)

        return {
            'input_i': float(data.get('input_i', -24)),
            'input_tp': float(data.get('input_tp', -2)),
            'input_lra': float(data.get('input_lra', 7)),
            'input_thresh': float(data.get('input_thresh', -34)),
            'target_offset': float(data.get('target_offset', 0)),
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        return None
