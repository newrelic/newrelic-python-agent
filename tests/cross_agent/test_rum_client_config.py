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
import os

import pytest
import webtest
from testing_support.fixtures import override_application_settings

from newrelic.api.transaction import (
    add_custom_attribute,
    get_browser_timing_footer,
    set_transaction_name,
)
from newrelic.api.wsgi_application import wsgi_application


def _load_tests():
    fixture = os.path.join(os.curdir, "fixtures", "rum_client_config.json")
    with open(fixture, "r") as fh:
        js = fh.read()
    return json.loads(js)


fields = [
    "testname",
    "apptime_milliseconds",
    "queuetime_milliseconds",
    "browser_monitoring.attributes.enabled",
    "transaction_name",
    "license_key",
    "connect_reply",
    "user_attributes",
    "expected",
]

# Replace . as not a valid character in python argument names

field_names = ",".join([f.replace(".", "_") for f in fields])


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in fields])


_rum_tests = [_parametrize_test(t) for t in _load_tests()]


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = "200 OK"

    txn_name = environ.get("txn_name")
    set_transaction_name(txn_name, group="")

    user_attrs = json.loads(environ.get("user_attrs"))
    for key, value in user_attrs.items():
        add_custom_attribute(key, value)

    text = "<html><head>%s</head><body><p>RESPONSE</p></body></html>"

    output = (text % get_browser_timing_footer()).encode("UTF-8")

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    return [output]


target_application = webtest.TestApp(target_wsgi_application)


@pytest.mark.parametrize(field_names, _rum_tests)
def test_browser_montioring(
    testname,
    apptime_milliseconds,
    queuetime_milliseconds,
    browser_monitoring_attributes_enabled,
    transaction_name,
    license_key,
    connect_reply,
    user_attributes,
    expected,
):

    settings = {
        "browser_monitoring.attributes.enabled": browser_monitoring_attributes_enabled,
        "license_key": license_key,
        "js_agent_loader": "<!-- NREUM HEADER -->",
    }
    settings.update(connect_reply)

    @override_application_settings(settings)
    def run_browser_data_test():

        response = target_application.get(
            "/", extra_environ={"txn_name": str(transaction_name), "user_attrs": json.dumps(user_attributes)}
        )

        # We actually put the "footer" in the header, the first script is the
        # agent "header", the second one is where the data lives, hence the [1].

        footer = response.html.html.head.find_all("script")[1]
        footer_data = json.loads(footer.string.split("NREUM.info=")[1])

        # Not feasible to test the time metric values in testing

        expected.pop("queueTime")
        expected.pop("applicationTime")
        assert footer_data["applicationTime"] >= 0
        assert footer_data["queueTime"] >= 0

        # Python always prepends stuff to the transaction name, so this
        # doesn't match the obscured value.

        expected.pop("transactionName")

        # Check that all other values are correct

        for key, value in expected.items():

            # If there are no attributes, the spec allows us to omit the
            # 'atts' field altogether, so we do. But, the cross agent tests
            # don't omit it, so we need to special case 'atts' when we compare
            # to 'expected'.

            if key == "atts" and value == "":
                assert key not in footer_data
            else:
                assert footer_data[key] == value

    run_browser_data_test()
