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

from newrelic.agent import background_task, current_transaction

from . import benchmark

# This benchmark suite is a placeholder until actual benchmark suites can be added.
# For now, this ensures the infrastructure works as intended.


@benchmark
class Suite:
    def bench_application_active(self):
        from newrelic.agent import application

        assert application().active

    @background_task()
    def bench_transaction_active(self):
        from newrelic.agent import application

        assert current_transaction()
