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
from opentelemetry.sdk.metrics.export import AggregationTemporality

from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.signature import bind_args


def attribute_parser(attributes):
    return {attribute.key: attribute.value.string_value for attribute in attributes}


def metric_parser(export_request):
    parsed_counter_data = []
    parsed_histogram_data = []
    parsed_gauge_data = []
    for request in export_request:
        for scope_metric in request.resource_metrics[-1].scope_metrics:
            for metric in scope_metric.metrics:
                if metric.HasField("sum"):  # Counters and UpDownCounters
                    for data_point in metric.sum.data_points:
                        count = data_point.as_int or data_point.as_double
                        attr = attribute_parser(data_point.attributes)
                        parsed_counter_data.append((metric.name, count, attr))
                if metric.HasField("exponential_histogram"):  # The agent exports Histograms as exponential histograms
                    for data_point in metric.exponential_histogram.data_points:
                        attr = attribute_parser(data_point.attributes)
                        parsed_histogram_data.append(
                            (metric.name, data_point.count, data_point.sum, data_point.min, data_point.max, attr)
                        )
                if metric.HasField("gauge"):  # Gauges and ObservableGauges
                    for data_point in metric.gauge.data_points:
                        value = data_point.as_int or data_point.as_double
                        attr = attribute_parser(data_point.attributes)
                        parsed_gauge_data.append((metric.name, value, attr))

    # Fill in with remaining metric types
    return (parsed_counter_data, parsed_histogram_data, parsed_gauge_data)


def assert_matches_expected(parsed_data, expected):
    """Compares only the metric names in `expected`, so each test must use its own instrument names.

    This is because Cumulative totals are re-exported on every collect, so they bleed into later tests.
    """
    expected_metric_names = {item[0] for item in expected}
    parsed_data = [item for item in parsed_data if item[0] in expected_metric_names]
    assert all(item in parsed_data for item in expected), f"Expected: {expected}, Got: {parsed_data}"
    assert all(item in expected for item in parsed_data), f"Expected: {expected}, Got: {parsed_data}"


def assert_temporality(metric_events, expected):
    """Counters (monotonic sums) and Histograms must be Delta, and UpDownCounters Cumulative."""
    expected_metric_names = {item[0] for item in expected}
    for request in metric_events:
        for scope_metric in request.resource_metrics[-1].scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name not in expected_metric_names:
                    continue
                if metric.HasField("sum"):  # Counters and UpDownCounters
                    if metric.sum.is_monotonic:
                        temporality = AggregationTemporality.DELTA
                    else:
                        temporality = AggregationTemporality.CUMULATIVE
                    assert metric.sum.aggregation_temporality == temporality, f"{metric.name} is not {temporality.name}"
                if metric.HasField("exponential_histogram"):  # The agent exports Histograms as exponential histograms
                    assert metric.exponential_histogram.aggregation_temporality == AggregationTemporality.DELTA, (
                        f"{metric.name} is not DELTA"
                    )


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

        parsed_counter_data, _, _ = metric_parser(metric_events)

        if not counter_expected:
            continue

        try:
            assert_matches_expected(parsed_counter_data, counter_expected)
            return
        except AssertionError as err:
            # Go through next metric reader to see if that has the information we expect
            last_error = err

    if counter_expected:
        raise last_error or AssertionError(f"Expected: {counter_expected}, but the MeterProvider has no metric readers")


def validate_otel_dimensional_metrics(
    counter_expected=None,  # [(name, value, attributes), ...]
    histogram_expected=None,  # [(name, count, sum, min, max, attributes), ...]
    gauge_expected=None,  # [(name, value, attributes), ...]
):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        with capture_otlp_metric_exports() as metric_events:
            wrapped(*args, **kwargs)
            assert_counters_exported(metrics.get_meter_provider(), metric_events, counter_expected)

            # assert_counters_exported has already made the metric readers collect
            if counter_expected:
                assert_temporality(metric_events, counter_expected)

            if histogram_expected:
                assert_temporality(metric_events, histogram_expected)
                _, parsed_histogram_data, _ = metric_parser(metric_events)
                assert_matches_expected(parsed_histogram_data, histogram_expected)

            if gauge_expected:
                _, _, parsed_gauge_data = metric_parser(metric_events)
                assert_matches_expected(parsed_gauge_data, gauge_expected)

    return _validate_wrapper
