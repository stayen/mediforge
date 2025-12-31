"""Main CLI entry point."""

import click

from .plugins import discover_plugins
from .utils.logging import configure_logging


@click.group()
@click.option(
    '--log-level',
    type=click.Choice(['error', 'warning', 'info', 'debug']),
    default='warning',
    help='Logging verbosity level',
)
@click.version_option(package_name='mediforge')
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """
    Mediforge - Command-line media processing toolkit.

    Compose videos and audio from scenario files, normalize loudness,
    apply mastering presets, and more.
    """
    ctx.ensure_object(dict)
    ctx.obj['log_level'] = log_level
    configure_logging(log_level)


# Discover and register all plugins
discover_plugins(cli)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
