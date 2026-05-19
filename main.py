"""Entry point — dispatch to sub-commands via `py main.py <cmd>`."""

import importlib
import pkgutil

import click

import commands as _commands


class PrivateAgent(click.Group):
    """自动检测commands/<name>/main.py中的命令"""

    def list_commands(self, ctx):
        return sorted(m.name for m in pkgutil.iter_modules(_commands.__path__))

    def get_command(self, ctx, name):
        mod = importlib.import_module(f"commands.{name}.main")
        return mod.run


cli = PrivateAgent(help="Private Agent 智能体")

if __name__ == "__main__":
    cli()
