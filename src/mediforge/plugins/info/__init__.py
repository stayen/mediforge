"""Info command plugin for displaying media file information."""

from pathlib import Path

import click

from mediforge.core.probe import get_media_info, format_media_info
from mediforge.core.errors import ProbeError
from mediforge.utils.logging import get_logger


@click.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.pass_context
def info(ctx: click.Context, file: Path, output_json: bool) -> None:
    """
    Display information about a media file.

    FILE is the path to a video, audio, or image file.

    Example:

        mediforge info video.mp4
    """
    log_level = ctx.obj.get('log_level', 'warning') if ctx.obj else 'warning'
    logger = get_logger(__name__, log_level)

    logger.debug(f"Probing file: {file}")

    try:
        media_info = get_media_info(file)
    except ProbeError as e:
        raise click.ClickException(str(e))

    if output_json:
        import json
        # Convert Decimals and Path to JSON-serializable types
        output = _make_json_serializable(media_info)
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(format_media_info(media_info))


def _make_json_serializable(obj):
    """Convert Decimal and Path objects to JSON-serializable types."""
    from decimal import Decimal

    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(v) for v in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, Path):
        return str(obj)
    else:
        return obj


def register(parent: click.Group) -> None:
    """Register the info command with the CLI."""
    parent.add_command(info)
