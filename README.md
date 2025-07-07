xemu-perf-tester_results
===

Archived performance tester results for [xemu](https://xemu.app)

[Results browsable on GitHub pages](https://abaire.github.io/xemu-perf-tester_results/)

# Submitting results

## Setup

Read the README.md in the `inputs` directory or use the `run.sh` script with
`--import-install` to copy files from your working xemu installation.

## Linux/macOS

```shell
./run.sh
```

### Running with a specific official xemu release

```shell
./run.sh --xemu-tag <release>

# E.g., ./run.sh --xemu-tag v0.8.90
```

### Running with a development / PR build

1. Build xemu (or download a PR artifact)
1. Use the `--xemu` option to specify the path to the xemu executable
    ```shell
    ./run.sh -X <path/to/xemu>
    ```

