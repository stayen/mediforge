"""Audio mastering with presets."""

from pathlib import Path

import click
from rich.console import Console

from mediforge.core.errors import FFmpegError, ConfigurationError
from mediforge.backends.executor import CommandExecutor
from mediforge.config.defaults import MASTERING_PRESETS
from mediforge.config.loader import get_mastering_preset
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path),
              help='Output audio file path')
@click.option('--preset', '-p', type=str, default='streaming',
              help='Mastering preset name (default: streaming)')
@click.option('--list-presets', is_flag=True, help='List available presets and exit')
@click.option('--dry-run', is_flag=True, help='Print FFmpeg commands without executing')
@click.pass_context
def master(
    ctx: click.Context,
    input_file: Path,
    output: Path,
    preset: str,
    list_presets: bool,
    dry_run: bool,
) -> None:
    """
    Apply mastering preset to audio.

    Mastering presets apply a chain of effects:
    - EQ (equalization)
    - Compression
    - De-essing (for voice)
    - Limiting
    - Loudness normalization

    Example:

        mediforge audio master input.wav -o output.wav --preset=podcast
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)
    console = Console()

    if list_presets:
        console.print("[bold]Available mastering presets:[/bold]")
        for name, settings in MASTERING_PRESETS.items():
            lufs = settings.get('target_lufs', -14)
            console.print(f"  {name}: {lufs} LUFS target")
            if 'compressor' in settings:
                comp = settings['compressor']
                console.print(f"    Compressor: {comp.get('ratio', 2)}:1 @ {comp.get('threshold', -18)}dB")
            if 'de_esser' in settings:
                console.print(f"    De-esser enabled")
        return

    # Get preset configuration
    try:
        preset_config = get_mastering_preset(preset)
    except ConfigurationError as e:
        raise click.ClickException(str(e))

    if not dry_run:
        console.print(f"[bold]Mastering audio with '{preset}' preset[/bold]")
        console.print(f"  Input: {input_file}")
        console.print(f"  Target: {preset_config.get('target_lufs', -14)} LUFS")

    # Build filter chain
    filters = _build_mastering_filters(preset_config)
    logger.debug(f"Filter chain: {filters}")

    # Build and execute command
    cmd = [
        'ffmpeg', '-y',
        '-i', str(input_file),
        '-af', filters,
        str(output),
    ]

    executor = CommandExecutor(dry_run=dry_run, log_level=log_level)

    try:
        if not dry_run:
            console.print("  Processing...")

        executor.execute(
            command=cmd,
            stage="mastering",
        )

    except FFmpegError as e:
        raise click.ClickException(f"Mastering failed: {e}")

    if not dry_run:
        console.print(f"[green]Mastered audio saved to: {output}[/green]")


def _build_mastering_filters(preset: dict) -> str:
    """Build FFmpeg audio filter chain from preset."""
    filters = []

    # EQ (if specified)
    if 'eq' in preset:
        eq = preset['eq']
        eq_filters = []

        if 'low_shelf' in eq:
            ls = eq['low_shelf']
            eq_filters.append(
                f"lowshelf=f={ls.get('freq', 80)}:g={ls.get('gain', 0)}"
            )

        if 'high_shelf' in eq:
            hs = eq['high_shelf']
            eq_filters.append(
                f"highshelf=f={hs.get('freq', 12000)}:g={hs.get('gain', 0)}"
            )

        if 'peak' in eq:
            for peak in eq['peak']:
                eq_filters.append(
                    f"equalizer=f={peak.get('freq', 1000)}:width_type=q:"
                    f"w={peak.get('q', 1)}:g={peak.get('gain', 0)}"
                )

        filters.extend(eq_filters)

    # Compressor (if specified)
    if 'compressor' in preset:
        comp = preset['compressor']
        filters.append(
            f"acompressor="
            f"threshold={comp.get('threshold', -18)}dB:"
            f"ratio={comp.get('ratio', 3)}:"
            f"attack={comp.get('attack', 10)}:"
            f"release={comp.get('release', 100)}:"
            f"makeup={comp.get('makeup', 0)}dB"
        )

    # De-esser (if specified)
    if 'de_esser' in preset:
        de = preset['de_esser']
        # Use bandreject filter as simple de-esser
        filters.append(
            f"highpass=f={de.get('frequency', 6000) - 2000},"
            f"acompressor=threshold={de.get('threshold', -30)}dB:ratio=10:attack=0.3:release=25,"
            f"lowpass=f={de.get('frequency', 6000) + 2000}"
        )

    # Limiter (if specified)
    if 'limiter' in preset:
        lim = preset['limiter']
        ceiling = lim.get('ceiling', -1.0)
        filters.append(f"alimiter=limit={ceiling}dB:level=false")

    # Loudness normalization (always applied)
    target_lufs = preset.get('target_lufs', -14.0)
    true_peak = preset.get('true_peak', -1.0)
    filters.append(f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11")

    return ','.join(filters)
