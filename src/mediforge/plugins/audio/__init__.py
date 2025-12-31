"""Audio processing plugin."""

import click

from . import compose, normalize, master


@click.group()
def audio() -> None:
    """Audio processing commands."""
    pass


audio.add_command(compose.compose)
audio.add_command(normalize.normalize)
audio.add_command(master.master)


def register(parent: click.Group) -> None:
    """Register the audio command group with the CLI."""
    parent.add_command(audio)
