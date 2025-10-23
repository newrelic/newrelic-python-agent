#!/usr/bin/env python
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

import fileinput
import os
from pathlib import Path
from textwrap import dedent

GROUP_NUMBER = int(os.environ["GROUP_NUMBER"]) - 1
TOTAL_GROUPS = int(os.environ["TOTAL_GROUPS"])
GITHUB_JOB = os.environ["GITHUB_JOB"]
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT", None)


def main(stdin):
    environments = [env.rstrip() for env in stdin]
    filtered_envs = [env for env in environments if env.startswith(GITHUB_JOB + "-")]
    grouped_envs = filtered_envs[GROUP_NUMBER::TOTAL_GROUPS]

    # If not environments are found, raise an error with helpful information.
    if not grouped_envs:
        error_msg = dedent(f"""
            No matching environments found.
            GITHUB_JOB = {GITHUB_JOB}
            GROUP_NUMBER = {GROUP_NUMBER + 1}
            TOTAL_GROUPS = {TOTAL_GROUPS}

            environments = {environments}
            filtered_envs = {filtered_envs}
            grouped_envs = {grouped_envs}
        """)
        raise RuntimeError(error_msg(environments))

    # Output results to GITHUB_OUTPUT for use in later steps.
    if GITHUB_OUTPUT:
        with Path(GITHUB_OUTPUT).open("a") as output_fh:
            print(f"envs={','.join(grouped_envs)}", file=output_fh)

    # Output human readable results to stdout for visibility in logs.
    print("\n".join(grouped_envs))


if __name__ == "__main__":
    with fileinput.input() as stdin:
        main(stdin)
