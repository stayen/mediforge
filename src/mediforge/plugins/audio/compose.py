"""Audio composition from scenario file."""

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from mediforge.core.scenario import ScenarioParser
from mediforge.core.errors import ValidationError, FFmpegError, MediaFileError
from mediforge.backends.ffmpeg import FFmpegCommandBuilder
from mediforge.backends.executor import CommandExecutor
from mediforge.utils.tempfiles import TempDirectory
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('scenario', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', required=True, type=click.Path(path_type=Path),
              help='Output audio file path')
@click.option('--dry-run', is_flag=True, help='Print FFmpeg commands without executing')
@click.option('--progress', 'show_progress', is_flag=True, help='Show progress bar')
@click.option('--keep-temp', is_flag=True, help='Preserve intermediate files on success')
@click.pass_context
def compose(
    ctx: click.Context,
    scenario: Path,
    output: Path,
    dry_run: bool,
    show_progress: bool,
    keep_temp: bool,
) -> None:
    """
    Compose audio from scenario file.

    SCENARIO is a YAML file defining the timeline with audio clips, effects,
    and output settings.

    Example:

        mediforge audio compose project.yaml -o output.wav
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)
    console = Console()

    # Parse scenario
    logger.info(f"Parsing scenario: {scenario}")
    parser = ScenarioParser()

    try:
        scene = parser.parse(scenario)
    except ValidationError as e:
        raise click.ClickException(str(e))
    except MediaFileError as e:
        raise click.ClickException(str(e))
    except FileNotFoundError as e:
        raise click.ClickException(str(e))

    if scene.type != 'audio':
        raise click.ClickException(
            f"Expected audio scenario, got: {scene.type}"
        )

    # Summary
    logger.info(f"Timeline duration: {float(scene.timeline.duration):.2f}s")
    logger.info(f"Clips: {len(scene.timeline.clips)}")

    if not dry_run:
        console.print(f"[bold]Composing audio from {len(scene.timeline.clips)} clips[/bold]")
        console.print(f"  Duration: {float(scene.timeline.duration):.2f}s")
        console.print(f"  Output: {output}")

    # Build FFmpeg command
    builder = FFmpegCommandBuilder()

    with TempDirectory(keep=keep_temp or dry_run) as temp_dir:
        logger.debug(f"Temp directory: {temp_dir}")

        # Build composition command
        try:
            cmd = builder.build_audio_compose(
                timeline=scene.timeline,
                output_settings=scene.output,
                output_path=output,
            )
        except Exception as e:
            raise click.ClickException(f"Failed to build FFmpeg command: {e}")

        # Execute
        executor = CommandExecutor(
            dry_run=dry_run,
            log_level=log_level,
        )

        try:
            if show_progress and not dry_run:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Encoding audio...", total=100)

                    def update_progress(pct: float) -> None:
                        progress.update(task, completed=pct)

                    executor.progress_callback = update_progress
                    executor.execute_with_progress(
                        command=cmd,
                        expected_duration=float(scene.timeline.duration),
                        stage="audio composition",
                        temp_dir=temp_dir,
                    )
            else:
                executor.execute(
                    command=cmd,
                    stage="audio composition",
                    temp_dir=temp_dir,
                )
        except FFmpegError as e:
            if not dry_run:
                console.print(f"[red]Error during audio composition[/red]")
                if temp_dir.exists():
                    console.print(f"[yellow]Intermediate files preserved at: {temp_dir}[/yellow]")
            raise click.ClickException(str(e))

    if not dry_run:
        console.print(f"[green]Audio saved to: {output}[/green]")
