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

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.core.otlp_utils import otlp_content_setting

if otlp_content_setting == "protobuf":
    from google.protobuf.json_format import MessageToDict
else:
    MessageToDict = None


def data_points_to_dict(data_points):
    return {
        frozenset(
            {attr["key"]: attribute_to_value(attr["value"]) for attr in (data_point.get("attributes") or [])}.items()
        )
        or None: data_point
        for data_point in data_points
    }


def attribute_to_value(attribute):
    attribute_type, attribute_value = next(iter(attribute.items()))
    if attribute_type == "int_value":
        return int(attribute_value)
    elif attribute_type == "double_value":
        return float(attribute_value)
    elif attribute_type == "bool_value":
        return bool(attribute_value)
    elif attribute_type == "string_value":
        return str(attribute_value)
    else:
        raise TypeError(f"Invalid attribute type: {attribute_type}")


def payload_to_metrics(payload):
    if type(payload) is not dict:
        message = MessageToDict(payload, use_integers_for_enums=True, preserving_proto_field_name=True)
    else:
        message = payload

    resource_metrics = message.get("resource_metrics")
    assert len(resource_metrics) == 1
    resource_metrics = resource_metrics[0]

    resource = resource_metrics.get("resource")
    assert resource and resource.get("attributes")[0] == {
        "key": "instrumentation.provider",
        "value": {"string_value": "newrelic-opentelemetry-python-ml"},
    }
    scope_metrics = resource_metrics.get("scope_metrics")
    assert len(scope_metrics) == 1
    scope_metrics = scope_metrics[0]

    scope = scope_metrics.get("scope")
    assert scope is None
    metrics = scope_metrics.get("metrics")

    sent_summary_metrics = {}
    sent_count_metrics = {}
    for metric in metrics:
        metric_name = metric["name"]
        if metric.get("sum"):
            sent_count_metrics[metric_name] = metric
        elif metric.get("summary"):
            sent_summary_metrics[metric_name] = metric
        else:
            raise TypeError(f"Unknown metrics type for metric: {metric}")

    return sent_summary_metrics, sent_count_metrics


def validate_dimensional_metric_payload(summary_metrics=None, count_metrics=None):
    # Validates OTLP metrics as they are sent to the collector.

    summary_metrics = summary_metrics or []
    count_metrics = count_metrics or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        recorded_metrics = []

        @transient_function_wrapper("newrelic.core.agent_protocol", "OtlpProtocol.send")
        def send_request_wrapper(wrapped, instance, args, kwargs):
            def _bind_params(method, payload=(), *args, **kwargs):
                return method, payload

            method, payload = _bind_params(*args, **kwargs)

            if method == "dimensional_metric_data" and payload:
                recorded_metrics.append(payload)

            return wrapped(*args, **kwargs)

        wrapped = send_request_wrapper(wrapped)
        val = wrapped(*args, **kwargs)
        assert recorded_metrics

        decoded_payloads = [payload_to_metrics(payload) for payload in recorded_metrics]
        for sent_summary_metrics, sent_count_metrics in decoded_payloads:
            for metric, tags, count in summary_metrics:
                if isinstance(tags, dict):
                    tags = frozenset(tags.items())

                if not count:
                    if metric in sent_summary_metrics:
                        data_points = data_points_to_dict(sent_summary_metrics[metric]["summary"]["data_points"])
                        assert tags not in data_points, f"({metric}, {tags and dict(tags)}) Unexpected but found."
                else:
                    assert metric in sent_summary_metrics, (
                        f"{metric} Not Found. Got: {list(sent_summary_metrics.keys())}"
                    )
                    data_points = data_points_to_dict(sent_summary_metrics[metric]["summary"]["data_points"])
                    assert tags in data_points, (
                        f"({metric}, {tags and dict(tags)}) Not Found. Got: {list(data_points.keys())}"
                    )

                    # Validate metric format
                    metric_container = data_points[tags]
                    for key in ("start_time_unix_nano", "time_unix_nano", "count", "sum", "quantile_values"):
                        assert key in metric_container, f"Invalid metric format. Missing key: {key}"
                    quantile_values = metric_container["quantile_values"]
                    assert len(quantile_values) == 2  # Min and Max

                    # Validate metric count
                    if count != "present":
                        assert int(metric_container["count"]) == count, (
                            f"({metric}, {tags and dict(tags)}): Expected: {count} Got: {metric_container['count']}"
                        )

            for metric, tags, count in count_metrics:
                if isinstance(tags, dict):
                    tags = frozenset(tags.items())

                if not count:
                    if metric in sent_count_metrics:
                        data_points = data_points_to_dict(sent_count_metrics[metric]["sum"]["data_points"])
                        assert tags not in data_points, f"({metric}, {tags and dict(tags)}) Unexpected but found."
                else:
                    assert metric in sent_count_metrics, f"{metric} Not Found. Got: {list(sent_count_metrics.keys())}"
                    data_points = data_points_to_dict(sent_count_metrics[metric]["sum"]["data_points"])
                    assert tags in data_points, (
                        f"({metric}, {tags and dict(tags)}) Not Found. Got: {list(data_points.keys())}"
                    )

                    # Validate metric format
                    assert sent_count_metrics[metric]["sum"].get("is_monotonic")
                    assert sent_count_metrics[metric]["sum"].get("aggregation_temporality") == 1
                    metric_container = data_points[tags]
                    for key in ("start_time_unix_nano", "time_unix_nano", "as_int"):
                        assert key in metric_container, f"Invalid metric format. Missing key: {key}"

                    # Validate metric count
                    if count != "present":
                        assert int(metric_container["as_int"]) == count, (
                            f"({metric}, {tags and dict(tags)}): Expected: {count} Got: {metric_container['count']}"
                        )

        return val

    return _validate_wrapper
