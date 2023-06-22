#!/usr/bin/env python3.8
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

GROUP_NUMBER = int(os.environ["GROUP_NUMBER"]) - 1
TOTAL_GROUPS = int(os.environ["TOTAL_GROUPS"])


def main(f):
    environments = [e.rstrip() for e in f]
    filtered_envs = environments[GROUP_NUMBER::TOTAL_GROUPS]
    print(",".join(filtered_envs))


if __name__ == "__main__":
    with fileinput.input() as f:
        main(f)
