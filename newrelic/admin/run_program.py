# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from newrelic.admin import command, usage


@command(
    "run-program",
    "...",
    """Executes the command line but forces the initialisation of the agent
automatically at startup.

If using an agent configuration file the path to the file should be
supplied by the environment variable NEW_RELIC_CONFIG_FILE. Alternatively,
just the licence key, application and log file details can be supplied via
environment variables NEW_RELIC_LICENSE_KEY, NEW_RELIC_APP_NAME and
NEW_RELIC_LOG.""",
)
def run_program(args):
    import os
    import sys
    import time
    from pathlib import Path

    if len(args) == 0:
        usage("run-program")
        sys.exit(1)

    startup_debug = os.environ.get("NEW_RELIC_STARTUP_DEBUG", "off").lower() in ("on", "true", "1")

    def log_message(text, *args):
        if startup_debug:
            text = text % args
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"NEWRELIC: {timestamp} ({os.getpid()}) - {text}")

    log_message("New Relic Admin Script (%s)", __file__)

    log_message("working_directory = %r", str(Path.cwd()))
    log_message("current_command = %r", sys.argv)

    sys_prefix = str(Path(sys.prefix).resolve())
    log_message("sys.prefix = %r", sys_prefix)

    try:
        log_message("sys.real_prefix = %r", sys.real_prefix)
    except AttributeError:
        pass

    log_message("sys.version_info = %r", sys.version_info)
    log_message("sys.executable = %r", sys.executable)
    log_message("sys.flags = %r", sys.flags)
    log_message("sys.path = %r", sys.path)

    for name in sorted(os.environ.keys()):
        if name.startswith("NEW_RELIC_") or name.startswith("PYTHON"):
            if name == "NEW_RELIC_LICENSE_KEY":
                continue
            log_message("%s = %r", name, os.environ.get(name))

    import newrelic

    root_directory = Path(newrelic.__file__).parent
    boot_directory = root_directory / "bootstrap"

    root_directory = str(root_directory)
    boot_directory = str(boot_directory)

    log_message("root_directory = %r", root_directory)
    log_message("boot_directory = %r", boot_directory)

    python_path = boot_directory

    if "PYTHONPATH" in os.environ:
        path = os.environ["PYTHONPATH"].split(os.pathsep)
        if boot_directory not in path:
            python_path = f"{boot_directory}{os.pathsep}{os.environ['PYTHONPATH']}"

    os.environ["PYTHONPATH"] = python_path

    os.environ["NEW_RELIC_ADMIN_COMMAND"] = repr(sys.argv)

    os.environ["NEW_RELIC_PYTHON_PREFIX"] = sys_prefix
    os.environ["NEW_RELIC_PYTHON_VERSION"] = ".".join(map(str, sys.version_info[:2]))

    # If not an absolute or relative path, then we need to
    # see if program can be found in PATH. Note that can
    # be found in current working directory even though '.'
    # not in PATH.

    program_exe_path = args[0]

    # Don't use path.parent, as it can't distinguish between ./ and no parent.
    if not os.path.dirname(program_exe_path):  # noqa: PTH120
        program_search_path = os.environ.get("PATH", "").split(os.pathsep)
        for path in program_search_path:
            path = Path(path) / program_exe_path
            if path.exists() and os.access(path, os.X_OK):
                program_exe_path = str(path)  # Convert to str to match other code path
                break

    log_message("program_exe_path = %r", program_exe_path)
    log_message("execl_arguments = %r", [program_exe_path, *args])

    os.execl(program_exe_path, *args)  # noqa: S606
