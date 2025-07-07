xemu-perf-tester_results
===

Archived performance tester results for [xemu](https://xemu.app)

[Results browsable on GitHub pages](https://abaire.github.io/xemu-perf-tester_results/)

# Submitting results

## Setup

Note: In the examples below, things surrounded by angle brackets (e.g.,
`<someplace>`) will need to be replaced before running.

### Prepare to submit a PR

1. Install `git` if needed (E.g., from https://git-scm.com/downloads)
1. Fork this repository using the "Fork" button near the top of this GitHub
   page.
   See [the GitHub instructions](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo)
   if needed.
1. [Clone your fork locally](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#cloning-your-forked-repository)
    ```shell
   cd <someplace>
   git clone git@github.com:<your_github_username>/xemu-perf-tester_results.git --depth 1
    ```

### Set up your local environment

Read the README.md in the `inputs` directory or use the `run.sh`/`run.bat`
script with `--import-install` to copy files from your working xemu
installation. Note: The path to the xemu.toml file is printed to the console and
xemu.log by xemu when it starts.

```shell
cd <someplace>/xemu-perf-tester_results

# Windows
run.bat --import-install <path_to_xemu_toml_file>
# Linux/macOS
run.sh --import-install <path_to_xemu_toml_file>
```

### Install Python (if needed)

#### Windows

At the moment only Python 3.10 is supported without a full development
environment.

If you do not use Visual Studio:

1. Install the latest Python 3.10 release
   from https://www.python.org/downloads/windows/
2. Open up a `cmd.exe` shell and `cd` into the directory containing this file,
   then set up a virtualenv using Python 3.10.

   ```shell
   cd <someplace>/xemu-perf-tester_results
   
   python.exe --version
   REM If this does not print something like `Python 3.10`, you will need to
   REM provide a full path to Python. 
   REM For example, the default install of Python 3.10.x is at 
   REM   %LOCALAPPDATA%\Programs\Python\Python310\python.exe
   REM so `%LOCALAPPDATA%\Programs\Python\Python310\python.exe --version`
   REM should print 3.10.something
   
   python.exe -m venv venv
   "venv\Scripts\pip.exe" install -r requirements.txt
   ````

## Run the tests

### Windows

Open up a `cmd.exe` shell and `cd` into the directory containing this file.

```shell
cd <someplace>/xemu-perf-tester_results

rem Default - run using the OpenGL backend
run.bat

rem Vulkan
run.bat --use-vulkan
```

#### Running with a specific official xemu release

```shell
cd <someplace>/xemu-perf-tester_results
run.bat --xemu-tag <release>

# E.g., run.bat --xemu-tag v0.8.90
```

#### Running with a development / PR build

1. Build xemu (or download a PR artifact)
1. Use the `--xemu` option to specify the path to the xemu executable
    ```shell
    cd <someplace>/xemu-perf-tester_results
    run.bat -X <path/to/xemu>
    ```

### Linux/macOS

```shell
cd <someplace>/xemu-perf-tester_results
# Default - run using the OpenGL backend
./run.sh

# Or run with Vulkan
./run.sh --use-vulkan
```

#### Running with a specific official xemu release

```shell
cd <someplace>/xemu-perf-tester_results
./run.sh --xemu-tag <release>

# E.g., ./run.sh --xemu-tag v0.8.90
```

#### Running with a development / PR build

1. Build xemu (or download a PR artifact)
1. Use the `--xemu` option to specify the path to the xemu executable
    ```shell
    cd <someplace>/xemu-perf-tester_results
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

## Submit your results

1. Commit the results to your fork
   ```shell
   cd <someplace>/xemu-perf-tester_results
   
   # Checkout a new branch
   git checkout -b my_results
   
   # Add the new results
   git add results
   
   # Commit the change
   git commit -m "Adds new benchmark results"
   
   # Push the change
   git push -u origin my_results
   ```

   The final command should print out a URL that you may open in a browser to
   create a pull request to submit your results.
1. [Create a pull request (PR)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork)
   to add them to the primary repository.
