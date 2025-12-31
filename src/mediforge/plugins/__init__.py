"""Plugin discovery and registration."""

import importlib
import pkgutil
from pathlib import Path
from typing import Callable

import click


def discover_plugins(parent: click.Group) -> None:
    """
    Discover and register all plugins.

    Scans the plugins directory for modules with a `register` function
    and calls them with the parent CLI group.

    Args:
        parent: Root CLI group to register commands under
    """
    plugins_path = Path(__file__).parent

    for loader, name, is_pkg in pkgutil.iter_modules([str(plugins_path)]):
        if name.startswith('_'):
            continue

        module = importlib.import_module(f'mediforge.plugins.{name}')

        if hasattr(module, 'register'):
            module.register(parent)


def create_command_group(name: str, help_text: str) -> tuple[click.Group, Callable]:
    """
    Create a command group for a plugin domain.

    Returns:
        Tuple of (group, register function)

    Usage in plugin __init__.py:
        group, register = create_command_group('video', 'Video processing commands')

        @group.command()
        def compose(...):
            ...
    """
    group = click.Group(name=name, help=help_text)

    def register(parent: click.Group) -> None:
        parent.add_command(group)

    return group, register
