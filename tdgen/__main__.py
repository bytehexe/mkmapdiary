import click
import pathlib
import yaml

from .taskList import TaskList
from doit.api import run_tasks
from doit.doit_cmd import DoitMain
from doit.cmd_base import ModuleTaskLoader
from tabulate import tabulate
import locale
import os

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
@click.option('-a', '--always-execute', is_flag=True, help='Always execute tasks, even if up-to-date')
@click.option('-n', '--num-processes', default=os.cpu_count(), type=int, help='Number of parallel processes to use')
def main(dist_dir, config, build_dir, params, source_dir, always_execute, num_processes):
    click.echo("Generating configuration ...")

    # Load config defaults
    with open(pathlib.Path(__file__).parent / "defaults.yaml", "r") as f:
        config_data = yaml.safe_load(f)

    lc = locale.getlocale()[0].split("_")[0]
    locale_file = pathlib.Path(__file__).parent / f"defaults_{lc}.yaml"
    if locale_file.exists():
        with open(locale_file, "r") as f:
            config_data.update(yaml.safe_load(f))

    # Load configuration file if provided
    if config:
        config_data.update(yaml.safe_load(config.read_text()))

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

    proccess_args = []
    if always_execute:
        proccess_args.append("--always-execute")
    if num_processes > 0:
        proccess_args.append(f"--process={num_processes}")
    proccess_args.append("--parallel-type=thread")

    sys.exit(DoitMain(ModuleTaskLoader(taskList.toDict())).run(proccess_args))

if __name__ == "__main__":
    main()