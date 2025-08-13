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
    "network-config",
    "config_file [log_file]",
    """Prints out the network configuration after having loaded the settings
from <config_file>.""",
)
def network_config(args):
    import logging
    import os
    import sys
    from pathlib import Path

    if len(args) == 0:
        usage("network-config")
        sys.exit(1)

    from newrelic.config import initialize
    from newrelic.core.config import global_settings

    if len(args) >= 2:
        log_file = args[1]
    else:
        log_file = Path("/tmp/python-agent-test.log")

    log_level = logging.DEBUG

    try:
        log_file.unlink()
    except Exception:
        pass

    config_file = args[0]
    environment = os.environ.get("NEW_RELIC_ENVIRONMENT")

    if config_file == "-":
        config_file = os.environ.get("NEW_RELIC_CONFIG_FILE")

    initialize(config_file, environment, ignore_errors=False, log_file=log_file, log_level=log_level)

    _settings = global_settings()

    print(f"host = {_settings.host!r}")
    print(f"port = {_settings.port!r}")
    print(f"proxy_scheme = {_settings.proxy_scheme!r}")
    print(f"proxy_host = {_settings.proxy_host!r}")
    print(f"proxy_port = {_settings.proxy_port!r}")
    print(f"proxy_user = {_settings.proxy_user!r}")
    print(f"proxy_pass = {_settings.proxy_pass!r}")
