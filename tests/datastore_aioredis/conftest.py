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

import aioredis
import pytest

from testing_support.db_settings import redis_settings

from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (  # noqa: F401
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)

AIOREDIS_VERSION = tuple(int(x) for x in aioredis.__version__.split(".")[:2])
SKIPIF_AIOREDIS_V1 = pytest.mark.skipif(AIOREDIS_VERSION < (2,), reason="Unsupported aioredis version.")
SKIPIF_AIOREDIS_V2 = pytest.mark.skipif(AIOREDIS_VERSION >= (2,), reason="Unsupported aioredis version.")
DB_SETTINGS = redis_settings()[0]


_coverage_source = [
    "newrelic.hooks.datastore_aioredis",
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (datastore_aioredis)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (datastore)"],
)


@pytest.fixture(params=("Redis", "StrictRedis"))
def client(request, loop):
    if AIOREDIS_VERSION >= (2, 0):
        if request.param == "Redis":
            return aioredis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
        elif request.param == "StrictRedis":
            return aioredis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
        else:
            raise NotImplementedError()
    else:
        if request.param == "Redis":
            return loop.run_until_complete(aioredis.create_redis("redis://%s:%d" % (DB_SETTINGS["host"], DB_SETTINGS["port"]), db=0))
        elif request.param == "StrictRedis":
            pytest.skip("StrictRedis not implemented.")
        else:
            raise NotImplementedError()
