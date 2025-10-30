import os
import pathlib
import tempfile

import click

from ..main import main


def validate_param(ctx, param, value):
    for val in value:
        if "=" not in val:
            raise click.BadParameter("Parameters must be in the format key=value")
    return value


@click.command()
@click.option(
    "-x",
    "--params",
    multiple=True,
    callback=validate_param,
    type=str,
    help="Add additional configuration parameter. Format: key=value. Nested keys can be specified using dot notation, e.g., 'features.transcription=False'",
)
@click.option(
    "-b",
    "--build-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Path to the build directory (implies -B; defaults to a temporary directory)",
)
@click.option(
    "-B",
    "--persistent-build",
    is_flag=True,
    help="Uses a persistent build directory",
)
@click.option(
    "-a",
    "--always-execute",
    is_flag=True,
    help="Always execute tasks, even if up-to-date. Only relevant with persistent build directory.",
)
@click.option(
    "-n",
    "--num-processes",
    default=os.cpu_count(),
    type=int,
    help="Number of parallel processes to use",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity level. Can be used multiple times.",
)
@click.option(
    "-q",
    "--quiet",
    count=True,
    help="Decrease verbosity level. Can be used multiple times.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache in the home directory (not recommended)",
)
@click.option(
    "-T",
    "--generate-demo-data",
    is_flag=True,
    help="Do not compile. Generate demo data in the source directory; for testing purposes only; directory must be empty",
)
@click.argument(
    "source_dir",
    type=click.Path(path_type=pathlib.Path),
    required=True,
)
@click.argument(
    "dist_dir",
    type=click.Path(path_type=pathlib.Path),
    required=False,
)
def build(
    source_dir,
    dist_dir,
    build_dir,
    persistent_build,
    params,
    always_execute,
    num_processes,
    verbose,
    quiet,
    no_cache,
    generate_demo_data,
):
    """Build the map diary from source directory to distribution directory."""
    # Do not add tasks here, only adjust directories and call main()
    # Main reason: Logging setup needs to happen before any tasks are run

    if dist_dir is None:
        dist_dir = source_dir.with_name(source_dir.name + "_dist")

    if persistent_build and build_dir is None:
        build_dir = source_dir.with_name(source_dir.name + "_build")

    main_exec = lambda: main(
        dist_dir=dist_dir,
        build_dir=build_dir,
        source_dir=source_dir,
        params=params,
        always_execute=always_execute,
        num_processes=num_processes,
        verbose=verbose,
        quiet=quiet,
        no_cache=no_cache,
        generate_demo_data=generate_demo_data,
    )

    if build_dir is None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            build_dir = pathlib.Path(tmpdirname)
            main_exec()
    else:
        main_exec()
