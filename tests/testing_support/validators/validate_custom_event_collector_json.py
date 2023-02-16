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
from newrelic.common.object_wrapper import transient_function_wrapper


def validate_custom_event_collector_json(num_events=1):
    """Validate the format, types and number of custom events."""

    @transient_function_wrapper("newrelic.core.application", "Application.record_transaction")
    def _validate_custom_event_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise

        stats = instance._stats_engine
        settings = stats.settings

        agent_run_id = 666
        sampling_info = stats.custom_events.sampling_info
        samples = list(stats.custom_events)

        # Emulate the payload used in data_collector.py

        payload = (agent_run_id, sampling_info, samples)
        collector_json = json_encode(payload)

        decoded_json = json.loads(collector_json)

        decoded_agent_run_id = decoded_json[0]
        decoded_sampling_info = decoded_json[1]
        decoded_events = decoded_json[2]

        assert decoded_agent_run_id == agent_run_id
        assert decoded_sampling_info == sampling_info

        max_setting = settings.event_harvest_config.harvest_limits.custom_event_data
        assert decoded_sampling_info["reservoir_size"] == max_setting

        assert decoded_sampling_info["events_seen"] == num_events
        assert len(decoded_events) == num_events

        for (intrinsics, attributes) in decoded_events:
            assert isinstance(intrinsics, dict)
            assert isinstance(attributes, dict)

        return result

    return _validate_custom_event_collector_json
