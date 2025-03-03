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

from newrelic.common.encoding_utils import json_encode
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper


def validate_log_event_collector_json(num_logs=1):
    """Validate the format, types and number of logs of the data we
    send to the collector for harvest.
    """

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_log_event_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            samples = list(instance.log_events)

            # emulate the payload used in data_collector.py

            payload = ({"logs": tuple(log._asdict() for log in samples)},)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            log_events = decoded_json[0]["logs"]

            assert len(log_events) == num_logs
            for event in log_events:
                # event is an array containing timestamp, level, message, attributes
                assert len(event) == 4
                assert isinstance(event["timestamp"], int)
                assert isinstance(event["level"], str)
                assert isinstance(event["message"], str)
                assert isinstance(event["attributes"], dict)

                expected_attribute_keys = sorted(
                    ["entity.guid", "entity.name", "entity.type", "hostname", "span.id", "trace.id"]
                )
                assert sorted(event["attributes"].keys()) == expected_attribute_keys

        return result

    return _validate_log_event_collector_json
