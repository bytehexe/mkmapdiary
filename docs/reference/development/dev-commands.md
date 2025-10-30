# Dev commands

## Common commands

Most commonly used development commands are also available as [taskipy](https://taskipy.github.io/) tasks. You can run them via:

```
task <taskname>
```

Run `task --list` to see all available tasks.

## Running the dev version

```bash
# Show help
hatch run mkmapdiary --help

# Build a project  
hatch run mkmapdiary build source_dir

# Configure a project
hatch run mkmapdiary config -x key=value source_dir
```

## Pruning the enviroments

```
hatch env prune
```