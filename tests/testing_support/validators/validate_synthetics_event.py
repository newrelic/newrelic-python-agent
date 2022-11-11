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


from newrelic.common.object_wrapper import (
    function_wrapper,
    transient_function_wrapper,
)

def validate_synthetics_event(required_attrs=None, forgone_attrs=None, should_exist=True):
    required_attrs = required_attrs or []
    forgone_attrs = forgone_attrs or []
    failed = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_synthetics_event(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        try:
            if not should_exist:
                assert instance.synthetics_events == []
            else:
                assert len(instance.synthetics_events) == 1
                event = instance.synthetics_events[0]
                assert event is not None
                assert len(event) == 3

                def _flatten(event):
                    result = {}
                    for elem in event:
                        for k, v in elem.items():
                            result[k] = v
                    return result

                flat_event = _flatten(event)

                assert "nr.guid" in flat_event, "name=%r, event=%r" % ("nr.guid", flat_event)

                for name, value in required_attrs:
                    assert name in flat_event, "name=%r, event=%r" % (name, flat_event)
                    assert flat_event[name] == value, "name=%r, value=%r, event=%r" % (name, value, flat_event)

                for name, value in forgone_attrs:
                    assert name not in flat_event, "name=%r, value=%r, event=%r" % (name, value, flat_event)
        except Exception as e:
            failed.append(e)

        return result

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        _new_wrapper = _validate_synthetics_event(wrapped)
        result = _new_wrapper(*args, **kwargs)
        if failed:
            e = failed.pop()
            raise e
        return result

    return wrapper

