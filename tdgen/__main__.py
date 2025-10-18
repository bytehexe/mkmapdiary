import click
import pathlib
import yaml

from .taskList import TaskList
from doit.api import run_tasks
from doit.doit_cmd import DoitMain
from doit.cmd_base import ModuleTaskLoader
from tabulate import tabulate

import sys

def validate_param(ctx, param, value):
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value

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

    taskList = TaskList(config_data, source_dir, build_dir, dist_dir)

    n_assets = taskList.db.count_assets()
    click.echo(f"Found {n_assets} assets" + (":" if n_assets > 0 else "."))
    if n_assets > 0:
        print(tabulate(taskList.db.dump(), headers=["ID", "Path", "Type", "DateTime", "Latitude", "Longitude"]))

    click.echo("Running tasks ...")

    sys.exit(DoitMain(ModuleTaskLoader(taskList.toDict())).run([]))

if __name__ == "__main__":
    main()