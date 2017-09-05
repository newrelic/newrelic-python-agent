from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.config import global_settings

from newrelic.core.application import Application


def validate_metric_payload(metrics=[], endpoints_called=[]):
    @transient_function_wrapper('newrelic.core.data_collector',
            'DeveloperModeSession.send_request')
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(session, url, method, license_key,
                agent_run_id=None, payload=()):
            return method, payload

        method, payload = _bind_params(*args, **kwargs)
        endpoints_called.append(method)

        if method == 'metric_data' and payload:
            sent_metrics = {}
            for metric_info, metric_values in payload[3]:
                metric_key = (metric_info['name'], metric_info['scope'])
                sent_metrics[metric_key] = metric_values

            for metric in metrics:
                assert metric in sent_metrics, metric

        return wrapped(*args, **kwargs)

    return send_request_wrapper


required_metrics = [
    ('Supportability/Events/TransactionError/Seen', ''),
    ('Supportability/Events/TransactionError/Sent', ''),
    ('Supportability/Events/Customer/Seen', ''),
    ('Supportability/Events/Customer/Sent', ''),
    ('Supportability/Python/RequestSampler/requests', ''),
    ('Supportability/Python/RequestSampler/samples', ''),
    ('Instance/Reporting', ''),
]


endpoints_called = []


@validate_metric_payload(metrics=required_metrics,
        endpoints_called=endpoints_called)
def test_application_harvest():
    settings = global_settings()
    settings.developer_mode = True
    settings.license_key = '**NOT A LICENSE KEY**'

    app = Application('Python Agent Test (Harvest Loop)')
    app.connect_to_data_collector()

    app.harvest()

    # Verify that the metric_data endpoint is the 2nd to last endpoint called
    # Last endpoint called is get_agent_commands
    assert endpoints_called[-2] == 'metric_data'
