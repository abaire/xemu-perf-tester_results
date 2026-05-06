xemu-perf-tester_results
===

Archived performance tester results for [xemu](https://xemu.app)

[Results browsable on GitHub pages](https://abaire.github.io/xemu-perf-tester_results/)

# Submitting results

Results are submitted automatically by the
[xemu-perf-tester](https://github.com/abaire/xemu-perf-tester) tool via the
GitHub API. No fork, clone, or pull request is required.

## Setup

Note: In the examples below, things surrounded by angle brackets (e.g.,
`<someplace>`) will need to be replaced before running.

### One time setup

1. Download the latest scripts for your platform from the
   [Releases page](https://github.com/abaire/xemu-perf-tester_results/releases/latest):
   - **Windows**: `xemu-perf-tester-scripts-windows.zip`
   - **macOS**: `xemu-perf-tester-scripts-macos.zip`
   - **Linux**: `xemu-perf-tester-scripts-linux.zip`
1. Extract the archive to a directory of your choice (e.g., `<someplace>/xemu-perf-tester`).

#### Install Python (if needed)

##### Windows

Python 3.10 or higher is required. If you do not have a developer environment (including CMake) you will need to match the version of Python used by pyfatx. Check around https://github.com/mborgerson/fatx/blob/master/.github/workflows/build.yml#L165

If you do not have Python installed:

1. Install the latest Python 3.13 release
   from https://www.python.org/downloads/windows/
2. Open up a `cmd.exe` shell and `cd` into the directory containing this file,
   then run the setup:

   ```shell
   cd <someplace>/xemu-perf-tester
   python.exe --version
   REM If this does not print something like `Python 3.10` or higher, you will
   REM need to provide a full path to Python.
   REM For example, the default install of Python 3.10.x is at
   REM   %LOCALAPPDATA%\Programs\Python\Python310\python.exe
   ```

#### Set up your local environment

Use the `run.sh`/`run.bat` script with `--import-install` to copy files from
your working xemu installation. Note: The path to the xemu.toml file is printed
to the console and `xemu.log` by xemu when it starts.

```shell
cd <someplace>/xemu-perf-tester

# Windows
run.bat --import-install <path_to_xemu_toml_file>
# Linux/macOS
./run.sh --import-install <path_to_xemu_toml_file>
```

## Run the tests

### Windows

Open up a `cmd.exe` shell and `cd` into the directory containing the scripts.

```shell
cd <someplace>/xemu-perf-tester

rem Default - run using the OpenGL backend
run.bat

rem Vulkan
run.bat --use-vulkan
```

#### Running with a specific official xemu release

```shell
cd <someplace>/xemu-perf-tester
run.bat --xemu-tag <release>

# E.g., run.bat --xemu-tag v0.8.90
```

`--xemu-tag` accepts:

- a xemu release version (e.g., `v0.8.92`)
- the URL of a build action (e.g.,
  `https://github.com/xemu-project/xemu/actions/runs/16152580613`)
- the URL of a pull request (PR) (e.g.,
  `https://github.com/xemu-project/xemu/pull/2329`).

The action and PR options additionally require you to pass a
[GitHub personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
using the `--github-token` argument. See `--help` for details.

#### Running with a development / PR build

1. Build xemu (or download a PR artifact)
1. Use the `--xemu` option to specify the path to the xemu executable
    ```shell
    cd <someplace>/xemu-perf-tester
    run.bat -X <path/to/xemu>
    ```

### Linux/macOS

```shell
cd <someplace>/xemu-perf-tester
# Default - run using the OpenGL backend
./run.sh

# Or run with Vulkan
./run.sh --use-vulkan
```

#### Running with a specific official xemu release

```shell
cd <someplace>/xemu-perf-tester
./run.sh --xemu-tag <release>

# E.g., ./run.sh --xemu-tag v0.8.90
```

`--xemu-tag` accepts:

- a xemu release version (e.g., `v0.8.92`)
- the URL of a build action (e.g.,
  `https://github.com/xemu-project/xemu/actions/runs/16152580613`)
- the URL of a pull request (PR) (e.g.,
  `https://github.com/xemu-project/xemu/pull/2329`).

The action and PR options additionally require you to pass a GitHub token using
the `--github-token` argument. See `--help` for details.

#### Running with a development / PR build

1. Build xemu (or download a PR artifact)
1. Use the `--xemu` option to specify the path to the xemu executable
    ```shell
    cd <someplace>/xemu-perf-tester
    ./run.sh -X <path/to/xemu>
    ```

##### Using a development build of xemu on macOS

Some extra flags are needed to utilize a development build of xemu. You will
need to set the `XEMU_DYLD_FALLBACK_LIBRARY_PATH` environment variable to point
at a valid xemu.app binary and will need to pass the `--no-bundle` argument to
`xemu-perf-run` to prevent it from attempting to find a `xemu.app` bundle
itself.

```shell
XEMU_DYLD_FALLBACK_LIBRARY_PATH=<path_to_xemu_repo>/dist/xemu.app/Contents/Libraries/arm64 \
  ./run.sh -X <path_to_xemu_repo>/build/qemu-system-i386 --no-bundle
```

### Running for multiple xemu versions

The "bulk_run.sh"/"bulk_run.bat" is a trivial helper that will run the tests for a number of xemu versions. You edit the file and change/add to the versions it executes.

## Submit your results

Results are submitted automatically at the end of a test run via the GitHub API.
The tool will open a GitHub issue in this repository on your behalf containing
the benchmark data, which is then ingested automatically by a CI workflow.

The tool may ask you to open a browser and authenticate a token the first time you run it (and occasionally thereafter). This allows the script to post a GitHub issue to this repository on your behalf along with your benchmark results.

# Development

## Python

This project uses [hatch](https://pypi.org/project/hatch/) to perform formatting
and type checking. You will probably need to install it locally to pass the CI
checks.

## Javascript

This project uses [Biome](https://biomejs.dev/) to lint and format javascript
files. You will probably need to install it locally to pass the CI checks.
