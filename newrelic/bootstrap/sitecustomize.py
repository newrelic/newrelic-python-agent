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

import os
import sys
import time
from importlib.machinery import PathFinder
from pathlib import Path

# Define some debug logging routines to help sort out things when this
# all doesn't work as expected.

startup_debug = os.environ.get("NEW_RELIC_STARTUP_DEBUG", "off").lower() in ("on", "true", "1")


def log_message(text, *args, **kwargs):
    critical = kwargs.get("critical", False)
    if startup_debug or critical:
        text = text % args
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        sys.stdout.write(f"NEWRELIC: {timestamp} ({os.getpid()}) - {text}\n")
        sys.stdout.flush()


def del_sys_path_entry(path):
    if path and path in sys.path:
        try:
            del sys.path[sys.path.index(path)]
        except Exception:
            pass


log_message("New Relic Bootstrap (%s)", __file__)

log_message("working_directory = %r", str(Path.cwd()))

sys_prefix = str(Path(sys.prefix).resolve())
log_message("sys.prefix = %r", sys_prefix)

try:
    log_message("sys.real_prefix = %r", sys.real_prefix)
except AttributeError:
    pass

log_message("sys.version_info = %r", sys.version_info)
log_message("sys.executable = %r", sys.executable)

if hasattr(sys, "flags"):
    log_message("sys.flags = %r", sys.flags)

log_message("sys.path = %r", sys.path)

for name in sorted(os.environ.keys()):
    if name.startswith("NEW_RELIC_") or name.startswith("PYTHON"):
        if name == "NEW_RELIC_LICENSE_KEY":
            continue
        log_message("%s = %r", name, os.environ.get(name))

# We need to import the original sitecustomize.py file if it exists. We
# can't just try and import the existing one as we will pick up
# ourselves again. Even if we remove ourselves from sys.modules and
# remove the bootstrap directory from sys.path, still not sure that the
# import system will not have cached something and return a reference to
# ourselves rather than searching again. What we therefore do is use the
# imp module to find the module, excluding the bootstrap directory from
# the search, and then load what was found.

boot_directory = str(Path(__file__).parent)
log_message("boot_directory = %r", boot_directory)

del_sys_path_entry(boot_directory)

try:
    module_spec = PathFinder.find_spec("sitecustomize", path=sys.path)
except ImportError:
    pass
else:
    if module_spec is not None:  # Import error not raised in importlib
        log_message("sitecustomize = %r", module_spec)

        module_spec.loader.load_module("sitecustomize")

# Because the PYTHONPATH environment variable has been amended and the
# bootstrap directory added, if a Python application creates a sub
# process which runs a different Python interpreter, then it will still
# load this sitecustomize.py. If that is for a different Python version
# it will cause problems if we then try and import and initialize the
# agent. We therefore need to try our best to verify that we are running
# in the same Python installation as the original newrelic-admin script
# which was run and only continue if we are.

expected_python_prefix = os.environ.get("NEW_RELIC_PYTHON_PREFIX")
actual_python_prefix = sys_prefix

expected_python_version = os.environ.get("NEW_RELIC_PYTHON_VERSION")
actual_python_version = ".".join(map(str, sys.version_info[:2]))

python_prefix_matches = expected_python_prefix == actual_python_prefix
python_version_matches = expected_python_version == actual_python_version
k8s_operator_enabled = os.environ.get("NEW_RELIC_K8S_OPERATOR_ENABLED", "off").lower() in ("on", "true", "1")
azure_operator_enabled = os.environ.get("NEW_RELIC_AZURE_OPERATOR_ENABLED", "off").lower() in ("on", "true", "1")

log_message("python_prefix_matches = %r", python_prefix_matches)
log_message("python_version_matches = %r", python_version_matches)
log_message("k8s_operator_enabled = %r", k8s_operator_enabled)
log_message("azure_operator_enabled = %r", azure_operator_enabled)

if k8s_operator_enabled or azure_operator_enabled or (python_prefix_matches and python_version_matches):
    # We also need to skip agent initialisation if neither the license
    # key or config file environment variables are set. We do this as
    # some people like to use a common startup script which always uses
    # the wrapper script, and which controls whether the agent is
    # actually run based on the presence of the environment variables.

    license_key = os.environ.get("NEW_RELIC_LICENSE_KEY", None)
    developer_mode = os.environ.get("NEW_RELIC_DEVELOPER_MODE", "off").lower() in ("on", "true", "1")
    config_file = os.environ.get("NEW_RELIC_CONFIG_FILE", None)
    environment = os.environ.get("NEW_RELIC_ENVIRONMENT", None)
    initialize_agent = bool(license_key or config_file or developer_mode)

    log_message("initialize_agent = %r", initialize_agent)

    if initialize_agent:
        if k8s_operator_enabled or azure_operator_enabled:
            # When installed with either the kubernetes operator or the
            # azure operator functionality enabled, we need to attempt to
            # find a distribution from our initcontainer that matches the
            # current environment. For wheels, this is platform dependent and we
            # rely on pip to identify the correct wheel to use. If no suitable
            # wheel can be found, we will fall back to the sdist and disable
            # extensions. Once the appropriate distribution is found, we import
            # it and leave the entry in sys.path. This allows users to import
            # the 'newrelic' module later and use our APIs in their code.
            try:
                sys.path.insert(0, boot_directory)
                # Will use the same file for k8s as well as Azure since the functionality
                # will remain the same.  File may be renamed in the near future.
                from newrelic_k8s_operator import find_supported_newrelic_distribution
            finally:
                del_sys_path_entry(boot_directory)

            new_relic_path = find_supported_newrelic_distribution()
            do_insert_path = True
        else:
            # When installed as an egg with buildout, the root directory for
            # packages is not listed in sys.path and scripts instead set it
            # after Python has started up. This will cause importing of
            # 'newrelic' module to fail. What we do is see if the root
            # directory where the package is held is in sys.path and if not
            # insert it. For good measure we remove it after having imported
            # 'newrelic' module to reduce chance that will cause any issues.
            # If it is a buildout created script, it will replace the whole
            # sys.path again later anyway.
            root_directory = str(Path(boot_directory).parent.parent)
            log_message("root_directory = %r", root_directory)

            new_relic_path = root_directory
            do_insert_path = root_directory not in sys.path

        # Now that the appropriate location of the module has been identified,
        # either by the kubernetes operator or this script, we are ready to import
        # the 'newrelic' module to make it available in sys.modules. If the location
        # containing it was not found on sys.path, do_insert_path will be set and
        # the location will be inserted into sys.path. The module is then imported,
        # and the sys.path entry is removed afterwards to reduce chance that will
        # cause any issues.

        log_message(f"new_relic_path = {new_relic_path!r}")
        log_message(f"do_insert_path = {do_insert_path!r}")

        try:
            if do_insert_path:
                sys.path.insert(0, new_relic_path)

            import newrelic

            log_message("agent_version = %r", newrelic.version)
        finally:
            if do_insert_path:
                del_sys_path_entry(new_relic_path)

        # Finally initialize the agent.
        import newrelic.config

        newrelic.config.initialize(config_file, environment)
    else:
        log_message(
            "New Relic could not start due to missing configuration. Either NEW_RELIC_LICENSE_KEY or NEW_RELIC_CONFIG_FILE are required."
        )
else:
    log_message(
        """New Relic could not start because the newrelic-admin script was called from a Python installation that is different from the Python installation that is currently running. To fix this problem, call the newrelic-admin script from the Python installation that is currently running (details below).

newrelic-admin Python directory: %r
current Python directory: %r
newrelic-admin Python version: %r
current Python version: %r""",
        expected_python_prefix,
        actual_python_prefix,
        expected_python_version,
        actual_python_version,
        critical=True,
    )
