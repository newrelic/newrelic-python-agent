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

import json

import pytest
from testing_support.fixtures import (
    make_cross_agent_headers,
    override_application_settings,
    validate_analytics_catmap_data,
)
from testing_support.validators.validate_transaction_event_attributes import (
    validate_transaction_event_attributes,
)

from newrelic.common.encoding_utils import deobfuscate
from newrelic.common.object_wrapper import transient_function_wrapper

ENCODING_KEY = "1234567890123456789012345678901234567890"
test_uris = [
    ("/error?hello=world", "_target_application:error"),
    ("/coro?hello=world", "_target_application:index"),
    ("/class?hello=world", "_target_application:HelloWorldView._respond"),
]


def record_aiohttp1_raw_headers(raw_headers):
    try:
        import aiohttp.protocol  # noqa: F401, pylint: disable=W0611
    except ImportError:

        def pass_through(function):
            return function

        return pass_through

    @transient_function_wrapper("aiohttp.protocol", "HttpParser.parse_headers")
    def recorder(wrapped, instance, args, kwargs):
        def _bind_params(lines):
            return lines

        lines = _bind_params(*args, **kwargs)
        for line in lines:
            line = line.decode("utf-8")

            # This is the request, not the response
            if line.startswith("GET"):
                break

            if ":" in line:
                key, value = line.split(":", maxsplit=1)
                raw_headers[key.strip()] = value.strip()

        return wrapped(*args, **kwargs)

    return recorder


@pytest.mark.parametrize(
    "inbound_payload,expected_intrinsics,forgone_intrinsics,cat_id",
    [
        # Valid payload from trusted account
        (
            ["b854df4feb2b1f06", False, "7e249074f277923d", "5d2957be"],
            {
                "nr.referringTransactionGuid": "b854df4feb2b1f06",
                "nr.tripId": "7e249074f277923d",
                "nr.referringPathHash": "5d2957be",
            },
            [],
            "1#1",
        ),
        # Valid payload from an untrusted account
        (
            ["b854df4feb2b1f06", False, "7e249074f277923d", "5d2957be"],
            {},
            ["nr.referringTransactionGuid", "nr.tripId", "nr.referringPathHash"],
            "80#1",
        ),
    ],
)
@pytest.mark.parametrize("method", ["GET"])
@pytest.mark.parametrize("uri,metric_name", test_uris)
def test_cat_headers(
    method, uri, metric_name, inbound_payload, expected_intrinsics, forgone_intrinsics, cat_id, aiohttp_app
):

    _raw_headers = {}

    async def fetch():
        headers = make_cross_agent_headers(inbound_payload, ENCODING_KEY, cat_id)
        resp = await aiohttp_app.client.request(method, uri, headers=headers)

        if _raw_headers:
            raw_headers = _raw_headers
        else:
            raw_headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in resp.raw_headers}

        if expected_intrinsics:
            # test valid CAT response header
            assert "X-NewRelic-App-Data" in raw_headers

            app_data = json.loads(deobfuscate(raw_headers["X-NewRelic-App-Data"], ENCODING_KEY))
            assert app_data[0] == cat_id
            assert app_data[1] == ("WebTransaction/Function/%s" % metric_name)
        else:
            assert "X-NewRelic-App-Data" not in resp.headers

    _custom_settings = {
        "cross_process_id": "1#1",
        "encoding_key": ENCODING_KEY,
        "trusted_account_ids": [1],
        "cross_application_tracer.enabled": True,
        "distributed_tracing.enabled": False,
    }

    # NOTE: the logic-flow of this test can be a bit confusing.
    #       the override settings and attribute validation occur
    #       not when the request is made (above) since it does not
    #       occur inside a transaction. instead, the settings and
    #       validation are for the new transaction that is made
    #       asynchronously on the *server side* when the request
    #       is received and subsequently processed. that code is
    #       a fixture from conftest.py/_target_application.py

    @validate_analytics_catmap_data(
        "WebTransaction/Function/%s" % metric_name,
        expected_attributes=expected_intrinsics,
        non_expected_attributes=forgone_intrinsics,
    )
    @override_application_settings(_custom_settings)
    @record_aiohttp1_raw_headers(_raw_headers)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()


account_id = "33"
primary_application_id = "2827902"

inbound_payload = {
    "v": [0, 1],
    "d": {
        "ac": account_id,
        "ap": primary_application_id,
        "id": "7d3efb1b173fecfa",
        "tx": "e8b91a159289ff74",
        "pr": 1.234567,
        "sa": True,
        "ti": 1518469636035,
        "tr": "d6b4ba0c3a712ca",
        "ty": "App",
    },
}

expected_attributes = {
    "agent": [],
    "user": [],
    "intrinsic": {
        "traceId": "d6b4ba0c3a712ca",
        "priority": 1.234567,
        "sampled": True,
        "parent.type": "App",
        "parent.app": primary_application_id,
        "parent.account": account_id,
        "parent.transportType": "HTTP",
        "parentId": "e8b91a159289ff74",
        "parentSpanId": "7d3efb1b173fecfa",
    },
}

unexpected_attributes = {
    "agent": [],
    "user": [],
    "intrinsic": ["grandparentId", "cross_process_id", "nr.tripId", "nr.pathHash"],
}


@pytest.mark.parametrize("uri,metric_name", test_uris)
def test_distributed_tracing_headers(uri, metric_name, aiohttp_app):
    async def fetch():
        headers = {"newrelic": json.dumps(inbound_payload)}
        resp = await aiohttp_app.client.request("GET", uri, headers=headers)

        # better cat does not send a response in the headers
        assert "newrelic" not in resp.headers

        # old-cat headers should not be in the response
        assert "X-NewRelic-App-Data" not in resp.headers

    # NOTE: the logic-flow of this test can be a bit confusing.
    #       the override settings and attribute validation occur
    #       not when the request is made (above) since it does not
    #       occur inside a transaction. instead, the settings and
    #       validation are for the new transaction that is made
    #       asynchronously on the *server side* when the request
    #       is received and subsequently processed. that code is
    #       a fixture from conftest.py/_target_application.py

    @validate_transaction_event_attributes(expected_attributes, unexpected_attributes)
    @override_application_settings(
        {
            "account_id": "33",
            "trusted_account_key": "33",
            "primary_application_id": primary_application_id,
            "distributed_tracing.enabled": True,
        }
    )
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())

    _test()
