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

"""
Tests the scenario where a MeterProvider is created outside
the scope of without New Relic's instrumentation.
`get_meter_provider` and `set_meter_provider` are expected
to add the New Relic resource attributes and New Relic reader
and exporter to the existing MeterProvider.
"""

from contextlib import contextmanager

from opentelemetry.sdk.metrics import MeterProvider
from testing_support.validators.validate_otel_dimensional_metrics import validate_otel_dimensional_metrics

from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.hooks.hybridagent_opentelemetry import wrap_get_meter_provider, wrap_set_meter_provider


@contextmanager
def _uninstrumented(obj, attr):
    """Temporarily swap a New-Relic-wrapped callable for the original
    (un-instrumented) function it wraps, so code under it runs exactly as
    if New Relic's hook were never installed.
    """
    instrumented = getattr(obj, attr)
    setattr(obj, attr, instrumented.__wrapped__)
    try:
        yield
    finally:
        setattr(obj, attr, instrumented)


def _unmanaged_meter_provider(**kwargs):
    """Construct a MeterProvider the way code that bypassed New Relic's
    instrumentation would: __init__ runs with none of wrap_MeterProvider's
    resource/reader injection.
    """
    with _uninstrumented(MeterProvider, "__init__"):
        return MeterProvider(**kwargs)


def _assert_unmanaged(provider):
    assert list(provider._metric_readers) == []
    assert "entity.guid" not in provider._sdk_config.resource.attributes


def _assert_subscribed(provider):
    readers = list(provider._metric_readers)
    assert len(readers) == 1
    assert "entity.guid" in provider._sdk_config.resource.attributes
    return readers[0]


@validate_otel_dimensional_metrics(counter_expected=[(7, {})])
def test_set_meter_provider_retrofits_unmanaged_provider():
    provider = _unmanaged_meter_provider()
    _assert_unmanaged(provider)

    def real_set_meter_provider(meter_provider):
        pass  # stand-in for opentelemetry.metrics.set_meter_provider

    wrap_set_meter_provider(real_set_meter_provider, None, (provider,), {})

    nr_reader = _assert_subscribed(provider)

    meter = provider.get_meter("unmanaged_provider_meter")
    counter = meter.create_counter("unmanaged_provider_counter")
    counter.add(7)


@validate_otel_dimensional_metrics(counter_expected=[(9, {})])
def test_get_meter_provider_retrofits_unmanaged_provider():
    provider = _unmanaged_meter_provider()
    _assert_unmanaged(provider)

    def real_get_meter_provider():
        return provider  # stand-in for opentelemetry.metrics.get_meter_provider

    application = application_instance()
    previous_meter_provider = application._agent._meter_provider
    application._agent._meter_provider = None
    try:
        result = wrap_get_meter_provider(real_get_meter_provider, None, (), {})

        assert result is provider
        nr_reader = _assert_subscribed(provider)

        meter = provider.get_meter("unmanaged_provider_meter")
        counter = meter.create_counter("unmanaged_provider_counter")
        counter.add(9)
    finally:
        application._agent._meter_provider = previous_meter_provider
