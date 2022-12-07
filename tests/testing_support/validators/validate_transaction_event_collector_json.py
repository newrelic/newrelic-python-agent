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


def validate_transaction_event_collector_json():
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_event_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            samples = list(instance.transaction_events)

            # recreate what happens right before data is sent to the collector
            # in data_collector.py during the harvest via analytic_event_data
            agent_run_id = 666
            payload = (agent_run_id, samples)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            assert decoded_json[0] == agent_run_id

            # list of events

            events = decoded_json[1]

            for event in events:

                # event is an array containing intrinsics, user-attributes,
                # and agent-attributes

                assert len(event) == 3
                for d in event:
                    assert isinstance(d, dict)

        return result

    return _validate_transaction_event_collector_json
