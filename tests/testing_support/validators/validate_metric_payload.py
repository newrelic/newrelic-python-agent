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

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_metric_payload(metrics=[]):
    # Validates metrics as they are sent to the collector. Useful for testing
    # Supportability metrics that are created at harvest time.

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        recorded_metrics = []

        @transient_function_wrapper('newrelic.core.agent_protocol',
                'AgentProtocol.send')
        def send_request_wrapper(wrapped, instance, args, kwargs):
            def _bind_params(method, payload=(), *args, **kwargs):
                return method, payload

            method, payload = _bind_params(*args, **kwargs)

            if method == 'metric_data' and payload:
                sent_metrics = {}
                for metric_info, metric_values in payload[3]:
                    metric_key = (metric_info['name'], metric_info['scope'])
                    sent_metrics[metric_key] = metric_values

                recorded_metrics.append(sent_metrics)

            return wrapped(*args, **kwargs)

        wrapped = send_request_wrapper(wrapped)
        val = wrapped(*args, **kwargs)
        assert recorded_metrics

        for sent_metrics in recorded_metrics:
            for metric, count in metrics:
                # only look for unscoped metrics
                unscoped_metric = (metric, '')
                if not count:
                    assert unscoped_metric not in sent_metrics, unscoped_metric
                else:
                    assert unscoped_metric in sent_metrics, unscoped_metric
                    metric_values = sent_metrics[unscoped_metric]
                    assert metric_values[0] == count, "%s: Expected: %d Got: %d" % (metric, count, metric_values[0])

        return val

    return _validate_wrapper
