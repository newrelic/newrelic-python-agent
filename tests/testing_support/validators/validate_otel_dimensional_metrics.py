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

from contextlib import contextmanager

from opentelemetry import metrics

from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.signature import bind_args


def metric_parser(export_request):
    parsed_counter_data = []
    for request in export_request:
        for scope_metric in request.resource_metrics[-1].scope_metrics:
            for metric in scope_metric.metrics:
                if hasattr(metric, "sum"):
                    for data_point in metric.sum.data_points:
                        count = getattr(data_point, "as_int") or getattr(data_point, "as_double")
                        attr = {}
                        if hasattr(data_point, "attributes"):
                            for attribute in data_point.attributes:
                                attr[attribute.key] = attribute.value.string_value
                        parsed_counter_data.append((count, attr))

    # Fill in with remaining metric types
    return (parsed_counter_data, None)


@contextmanager
def capture_otlp_metric_exports():
    """Record every export request sent through the OTLP metric exporter.

    Yields a list that is appended to as exports occur. It is a list because
    there may be actual batching of requests.
    """
    metric_events = []

    def wrap_otlp_metric_exporter__export_batch(wrapped, instance, args, kwargs):
        bound_args = bind_args(wrapped, args, kwargs)
        export_request = bound_args.get("export_request")
        metric_events.append(export_request)

        return wrapped(*args, **kwargs)

    wrap_function_wrapper(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter",
        "OTLPMetricExporter._export_batch",
        wrap_otlp_metric_exporter__export_batch,
    )

    yield metric_events


def assert_counters_exported(meter_provider, metric_events, counter_expected):
    """Force each of the provider's metric readers to collect, and assert that
    the exported counters match `counter_expected` for at least one of them.
    """
    last_error = None
    for metric_reader in meter_provider._all_metric_readers:
        metric_reader.collect()

        parsed_counter_data, _ = metric_parser(metric_events)

        if not counter_expected:
            continue

        try:
            assert all(item in parsed_counter_data for item in counter_expected), (
                f"Expected: {counter_expected}, Got: {parsed_counter_data}"
            )
            assert all(item in counter_expected for item in parsed_counter_data), (
                f"Expected: {counter_expected}, Got: {parsed_counter_data}"
            )
            return
        except AssertionError as err:
            # Go through next metric reader to see if that has the information we expect
            last_error = err

    if counter_expected:
        raise last_error or AssertionError(f"Expected: {counter_expected}, but the MeterProvider has no metric readers")


def validate_otel_dimensional_metrics(counter_expected=None):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        with capture_otlp_metric_exports() as metric_events:
            wrapped(*args, **kwargs)
            assert_counters_exported(metrics.get_meter_provider(), metric_events, counter_expected)

    return _validate_wrapper
