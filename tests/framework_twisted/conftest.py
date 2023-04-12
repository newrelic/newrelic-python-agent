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

import pytest
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_twisted)", default_settings=_default_settings
)


@pytest.fixture(scope="module")
def app(request):
    from twisted.internet import endpoints, reactor
    from twisted.web import resource, server

    class Counter(resource.Resource):
        isLeaf = True
        numberRequests = 0

        def render_GET(self, request):
            self.numberRequests += 1
            request.setHeader(b"content-type", b"text/plain")
            content = "I am request #{}\n".format(self.numberRequests)
            return content.encode("ascii")

    endpoints.serverFromString(reactor, "tcp:8080").listen(server.Site(Counter()))
    reactor.run()
