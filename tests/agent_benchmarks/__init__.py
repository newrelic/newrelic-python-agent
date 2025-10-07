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

from ._agent_initialization import collector_agent_registration

BENCHMARK_PREFIXES = ("time", "mem")
REPLACE_PREFIX = "bench_"


def benchmark(cls):
    # Find all methods not prefixed with underscores and treat them as benchmark methods
    benchmark_methods = {
        name: method for name, method in vars(cls).items() if callable(method) and name.startswith(REPLACE_PREFIX)
    }

    # Remove setup function from benchmark methods and save it
    cls._setup = benchmark_methods.pop("setup", None)

    # Patch in benchmark methods for each prefix
    for name, method in benchmark_methods.items():
        name = name[len(REPLACE_PREFIX) :]  # Remove "bench_" prefix
        for prefix in BENCHMARK_PREFIXES:
            setattr(cls, f"{prefix}_{name}", method)

    # Define agent activation as setup function
    def setup(self):
        collector_agent_registration(self)

        # Call the original setup if it exists
        if getattr(self, "_setup", None) is not None:
            self._setup()

    # Patch in new setup method
    cls.setup = setup

    return cls
