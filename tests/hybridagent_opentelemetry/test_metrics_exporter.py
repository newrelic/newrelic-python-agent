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
import requests
from testing_support.fixtures import override_generic_settings

from newrelic.api.opentelemetry import meter_provider_resource_and_reader_generator
from newrelic.core.config import global_settings
from newrelic.network.addresses import proxy_details


@pytest.fixture
def meter_provider_with_proxy(meter_provider):
    @override_generic_settings(
        global_settings(),
        {
            "proxy_scheme": "http",
            "proxy_host": "proxy.example.com",
            "proxy_port": 8080,
            "proxy_user": "user",
            "proxy_pass": "pass",
        },
    )
    def reader_generator_with_proxy():
        _, nr_reader = meter_provider_resource_and_reader_generator(global_settings())
        return nr_reader

    nr_reader = reader_generator_with_proxy()

    meter_provider.add_metric_reader(nr_reader)

    yield meter_provider

    meter_provider.remove_metric_reader(nr_reader)


def test_meter_provider_creator_without_proxy(meter_provider):
    metric_reader = list(meter_provider._all_metric_readers)[0]
    session = metric_reader._exporter._client._transport._session

    assert session.proxies == {}


@override_generic_settings(
    global_settings(),
    {
        "proxy_scheme": "http",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "proxy_user": "user",
        "proxy_pass": "pass",
    },
)
def test_meter_provider_creator_with_proxy(meter_provider_with_proxy):
    settings = global_settings()

    # We cannot rely on the order of the metric readers, so we
    # check both of them for the correct proxy configuration.
    for metric_reader in meter_provider_with_proxy._all_metric_readers:
        session = metric_reader._exporter._client._transport._session
        assert isinstance(session, requests.Session)
        if session.proxies == proxy_details(
            settings.proxy_scheme, settings.proxy_host, settings.proxy_port, settings.proxy_user, settings.proxy_pass
        ):
            assert True
            return

    assert False


@pytest.mark.parametrize(
    "opentelemetry_metrics_export_interval,opentelemetry_metrics_export_timeout,expected_interval,expected_timeout",
    [
        (40000, 1000, 40000, 1000),  # interval > timeout, keep as is
        (1000, 1000, 60000, 10000),  # interval == timeout, revert to default
        (1000, 2000, 60000, 10000),  # interval < timeout, revert to default
        (0, 0, 60000, 10000),  # interval and timeout are both zero
        (-1000, 5000, 60000, 10000),  # interval is negative, revert to default
        (5000, -1000, 60000, 10000),  # timeout is negative, revert to default
    ],
)
def test_meter_exporter_interval_and_timeout(
    meter_provider,
    opentelemetry_metrics_export_interval,
    opentelemetry_metrics_export_timeout,
    expected_interval,
    expected_timeout,
):
    @override_generic_settings(
        global_settings(),
        {
            "opentelemetry.enabled": True,
            "opentelemetry.metrics.export_interval": opentelemetry_metrics_export_interval,
            "opentelemetry.metrics.export_timeout": opentelemetry_metrics_export_timeout,
        },
    )
    def _test():
        metric_reader = list(meter_provider._all_metric_readers)[0]

        metric_reader._export_interval_millis = expected_interval
        metric_reader._export_timeout_millis = expected_timeout

    _test()
