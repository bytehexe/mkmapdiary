import click
import pathlib
import yaml

from .generator import Generator
from doit.api import run_tasks
from doit.doit_cmd import DoitMain
from doit.cmd_base import TaskLoader2

import sys

def validate_param(ctx, param, value):
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value

class TaskLoader(TaskLoader2):
    def __init__(self, tasks):
        self.tasks = tasks
        super().__init__()

    def setup(self, opt_values):
        pass

    def load_doit_config(self):
        return {}

    def load_tasks(self, cmd, pos_args):
        return self.tasks

@click.command()
@click.option('-d', '--dist-dir', default="dist", type=click.Path(path_type=pathlib.Path), help='Path to distribution directory')
@click.option('-c', '--config', type=click.Path(path_type=pathlib.Path), help='Path to configuration file')
@click.option('-x', '--params', multiple=True, callback=validate_param, type=str, help='Additional parameters')
@click.option('-b', '--build-dir', default="build", type=click.Path(path_type=pathlib.Path), help='Path to build directory')
@click.option('-s', '--source-dir', default="src", type=click.Path(path_type=pathlib.Path), help='Path to source directory')
def main(dist_dir, config, build_dir, params, source_dir):
    click.echo("Generating configuration ...")

    # Load configuration file if provided
    if config:
        config_data = yaml.safe_load(config.read_text())
    else:
        config_data = {}

    # Override config with params
    for param in params:
        key, value = param.split("=", 1)
        key = key.split(".")
        d = config_data
        for k in key[:-1]:
            d = d.setdefault(k, {})
        d[key[-1]] = yaml.safe_load(value)

    click.echo("Generating tasks ...")

    generator = Generator(config_data, source_dir, build_dir, dist_dir)
    tasks = list(generator())
    for task in tasks:
        click.echo(f"Task: {task.name}")

    click.echo("Running tasks ...")

    sys.exit(DoitMain(TaskLoader(tasks)).run([]))

if __name__ == "__main__":
    main()