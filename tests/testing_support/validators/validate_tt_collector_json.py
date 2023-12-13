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

from newrelic.common.encoding_utils import unpack_field
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.common.system_info import LOCALHOST_EQUIVALENTS
from newrelic.core.database_utils import SQLConnections
from newrelic.packages import six


def _lookup_string_table(name, string_table, default=None):
    try:
        index = int(name.lstrip("`"))
        return string_table[index]
    except ValueError:
        return default


def validate_tt_collector_json(
    required_params=None,
    forgone_params=None,
    should_exist=True,
    datastore_params=None,
    datastore_forgone_params=None,
    message_broker_params=None,
    message_broker_forgone_params=None,
    exclude_request_uri=False,
):
    """make assertions based off the cross-agent spec on transaction traces"""
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    datastore_params = datastore_params or {}
    datastore_forgone_params = datastore_forgone_params or {}
    message_broker_params = message_broker_params or {}
    message_broker_forgone_params = message_broker_forgone_params or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        traces_recorded = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def _validate_tt_collector_json(wrapped, instance, args, kwargs):

            result = wrapped(*args, **kwargs)

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)
            traces_recorded.append(trace_data)

            return result

        def _validate_trace(trace):
            assert isinstance(trace[0], float)  # absolute start time (ms)
            assert isinstance(trace[1], float)  # duration (ms)
            assert trace[0] > 0  # absolute time (ms)
            assert isinstance(trace[2], six.string_types)  # transaction name
            if trace[2].startswith("WebTransaction"):
                if exclude_request_uri:
                    assert trace[3] is None  # request url
                else:
                    assert isinstance(trace[3], six.string_types)
                    # query parameters should not be captured
                    assert "?" not in trace[3]

            # trace details -- python agent always uses condensed trace array

            trace_details, string_table = unpack_field(trace[4])
            assert len(trace_details) == 5
            assert isinstance(trace_details[0], float)  # start time (ms)

            # the next two items should be empty dicts, old parameters stuff,
            # placeholders for now

            assert isinstance(trace_details[1], dict)
            assert len(trace_details[1]) == 0
            assert isinstance(trace_details[2], dict)
            assert len(trace_details[2]) == 0

            # root node in slot 3

            root_node = trace_details[3]
            assert isinstance(root_node[0], float)  # entry timestamp
            assert isinstance(root_node[1], float)  # exit timestamp
            assert root_node[2] == "ROOT"
            assert isinstance(root_node[3], dict)
            assert len(root_node[3]) == 0  # spec shows empty (for root)
            children = root_node[4]
            assert isinstance(children, list)

            # there are two optional items at the end of trace segments,
            # class name that segment is in, and method name function is in;
            # Python agent does not use these (only Java does)

            # let's just test the first child
            trace_segment = children[0]
            assert isinstance(trace_segment[0], float)  # entry timestamp
            assert isinstance(trace_segment[1], float)  # exit timestamp
            assert isinstance(trace_segment[2], six.string_types)  # scope
            assert isinstance(trace_segment[3], dict)  # request params
            assert isinstance(trace_segment[4], list)  # children

            assert trace_segment[0] >= root_node[0]  # trace starts after root

            def _check_params_and_start_time(node):
                children = node[4]
                for child in children:
                    assert child[0] >= node[0]  # child started after parent
                    _check_params_and_start_time(child)

                params = node[3]
                assert isinstance(params, dict)

                # We should always report exclusive_duration_millis on a
                # segment. This allows us to override exclusive time
                # calculations on APM.
                assert "exclusive_duration_millis" in params
                assert isinstance(params["exclusive_duration_millis"], float)

                segment_name = _lookup_string_table(node[2], string_table, default=node[2])
                if segment_name.startswith("Datastore"):
                    for key in datastore_params:
                        assert key in params, key
                        assert params[key] == datastore_params[key], "Expected %s. Got %s." % (datastore_params[key], params[key])
                    for key in datastore_forgone_params:
                        assert key not in params, key

                    # if host is reported, it cannot be localhost
                    if "host" in params:
                        assert params["host"] not in LOCALHOST_EQUIVALENTS

                elif segment_name.startswith("MessageBroker"):
                    for key in message_broker_params:
                        assert key in params, key
                        assert params[key] == message_broker_params[key]
                    for key in message_broker_forgone_params:
                        assert key not in params, key

            _check_params_and_start_time(trace_segment)

            attributes = trace_details[4]

            assert "intrinsics" in attributes
            assert "userAttributes" in attributes
            assert "agentAttributes" in attributes

            assert isinstance(trace[5], six.string_types)  # GUID
            assert trace[6] is None  # reserved for future use
            assert trace[7] is False  # deprecated force persist flag

            # x-ray session ID

            assert trace[8] is None

            # Synthetics ID

            assert trace[9] is None or isinstance(trace[9], six.string_types)

            assert isinstance(string_table, list)
            for name in string_table:
                assert isinstance(name, six.string_types)  # metric name

        _new_wrapper = _validate_tt_collector_json(wrapped)
        val = _new_wrapper(*args, **kwargs)
        trace_data = traces_recorded.pop()
        trace = trace_data[0]  # 1st trace
        _validate_trace(trace)
        return val

    return _validate_wrapper
