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


def payload_to_ml_events(payload):
    if type(payload) is not dict:
        message = MessageToDict(payload, use_integers_for_enums=True, preserving_proto_field_name=True)
    else:
        message = payload

    inference_logs = []
    apm_logs = []
    resource_log_records = message.get("resource_logs")
    for resource_logs in resource_log_records:
        resource = resource_logs.get("resource")
        assert resource
        resource_attrs = resource.get("attributes")
        assert {
            "key": "instrumentation.provider",
            "value": {"string_value": "newrelic-opentelemetry-python-ml"},
        } in resource_attrs
        scope_logs = resource_logs.get("scope_logs")
        assert len(scope_logs) == 1
        scope_logs = scope_logs[0]

        scope = scope_logs.get("scope")
        assert scope is None
        logs = scope_logs.get("log_records")
        event_name = get_event_name(logs)
        if event_name == "InferenceEvent":
            inference_logs = logs
        else:
            # Make sure apm entity attrs are present on the resource.
            expected_apm_keys = ("entity.type", "entity.name", "entity.guid", "hostname", "instrumentation.provider")
            assert all(attr["key"] in expected_apm_keys for attr in resource_attrs)
            assert all(attr["value"] not in ("", None) for attr in resource_attrs)

            apm_logs = logs

    return inference_logs, apm_logs


def validate_ml_event_payload(ml_events=None):
    # Validates OTLP events as they are sent to the collector.

    ml_events = ml_events or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        recorded_ml_events = []

        @transient_function_wrapper("newrelic.core.agent_protocol", "OtlpProtocol.send")
        def send_request_wrapper(wrapped, instance, args, kwargs):
            def _bind_params(method, payload=(), *args, **kwargs):
                return method, payload

            method, payload = _bind_params(*args, **kwargs)

            if method == "ml_event_data" and payload:
                recorded_ml_events.append(payload)

            return wrapped(*args, **kwargs)

        wrapped = send_request_wrapper(wrapped)
        val = wrapped(*args, **kwargs)
        assert recorded_ml_events

        decoded_payloads = [payload_to_ml_events(payload) for payload in recorded_ml_events]
        decoded_inference_payloads = [payload[0] for payload in decoded_payloads]
        decoded_apm_payloads = [payload[1] for payload in decoded_payloads]
        all_apm_logs = normalize_logs(decoded_apm_payloads)
        all_inference_logs = normalize_logs(decoded_inference_payloads)

        for expected_event in ml_events.get("inference", []):
            assert expected_event in all_inference_logs, f"{expected_event} Not Found. Got: {all_inference_logs}"

        for expected_event in ml_events.get("apm", []):
            assert expected_event in all_apm_logs, f"{expected_event} Not Found. Got: {all_apm_logs}"
        return val

    return _validate_wrapper


def normalize_logs(decoded_payloads):
    all_logs = []
    for sent_logs in decoded_payloads:
        for data_point in sent_logs:
            for key in ("time_unix_nano",):
                assert key in data_point, f"Invalid log format. Missing key: {key}"
                all_logs.append(
                    {attr["key"]: attribute_to_value(attr["value"]) for attr in (data_point.get("attributes") or [])}
                )
    return all_logs


def get_event_name(logs):
    for attr in logs[0]["attributes"]:
        if attr["key"] == "event.name":
            return attr["value"]["string_value"]
