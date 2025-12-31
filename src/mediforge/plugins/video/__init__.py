"""Video processing plugin."""

import click

from . import compose


@click.group()
def video() -> None:
    """Video processing commands."""
    pass


video.add_command(compose.compose)


def register(parent: click.Group) -> None:
    """Register the video command group with the CLI."""
    parent.add_command(video)
