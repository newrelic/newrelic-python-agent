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
                        count = data_point.as_int
                        attr = {}
                        if hasattr(data_point, "attributes"):
                            for attribute in data_point.attributes:
                                attr[attribute.key] = attribute.value.string_value
                        parsed_counter_data.append((count, attr))

    # Fill in with remaining metric types
    return (parsed_counter_data, None)


def validate_otel_dimensional_metrics(
        counter_expected=None,
    ):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        # This is a list because there may be actual batching of requests
        metric_events = []

        def wrap_otlp_metric_exporter__export_batch(wrapped, instance, args, kwargs):
            bound_args = bind_args(wrapped, args, kwargs)
            export_request = bound_args.get("export_request")
            metric_events.append(export_request)

            return wrapped(*args, **kwargs)

        wrap_function_wrapper("opentelemetry.exporter.otlp.proto.http.metric_exporter", "OTLPMetricExporter._export_batch", wrap_otlp_metric_exporter__export_batch)

        wrapped(*args, **kwargs)

        # Force the metric reader to collect metrics immediately
        provider = metrics.get_meter_provider()
        metric_reader = provider._metric_readers[-1]
        metric_reader.collect()

        parsed_counter_data, _ = metric_parser(metric_events)

        if counter_expected:
            assert all(item in parsed_counter_data for item in counter_expected) and all(item in counter_expected for item in parsed_counter_data), f"Expected: {counter_expected}, Got: {parsed_counter_data}"

    return _validate_wrapper
