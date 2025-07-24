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
    "generate-config", "license_key [output_file]", """Generates a sample agent configuration file for <license_key>."""
)
def generate_config(args):
    import sys
    from pathlib import Path

    if len(args) == 0:
        usage("generate-config")
        sys.exit(1)

    import newrelic

    config_file = Path(newrelic.__file__).parent / "newrelic.ini"

    with config_file.open() as f:
        content = f.read()

    if len(args) >= 1:
        content = content.replace("*** REPLACE ME ***", args[0])

    if len(args) >= 2 and args[1] != "-":
        with Path(args[1]).open("w") as output_file:
            output_file.write(content)
    else:
        print(content)
