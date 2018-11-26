from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_metric_payload(metrics=[]):
    # Validates metrics as they are sent to the collector. Useful for testing
    # Supportability metrics that are created at harvest time.

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        recorded_metrics = []

        @transient_function_wrapper('newrelic.core.data_collector',
                'ApplicationSession.send_request')
        def send_request_wrapper(wrapped, instance, args, kwargs):
            def _bind_params(session, url, method, license_key,
                    agent_run_id=None, request_headers_map=None, payload=(),
                    *args, **kwargs):
                return method, payload

            method, payload = _bind_params(*args, **kwargs)

            if method == 'metric_data' and payload:
                sent_metrics = {}
                for metric_info, metric_values in payload[3]:
                    metric_key = (metric_info['name'], metric_info['scope'])
                    sent_metrics[metric_key] = metric_values

                recorded_metrics.append(sent_metrics)

            return wrapped(*args, **kwargs)

        _new_wrapper = send_request_wrapper(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert recorded_metrics

        for sent_metrics in recorded_metrics:
            for metric, count in metrics:
                # only look for unscoped metrics
                unscoped_metric = (metric, '')
                if not count:
                    assert unscoped_metric not in sent_metrics
                else:
                    assert unscoped_metric in sent_metrics
                    metric_values = sent_metrics[unscoped_metric]
                    assert metric_values[0] == count

        return val

    return _validate_wrapper
