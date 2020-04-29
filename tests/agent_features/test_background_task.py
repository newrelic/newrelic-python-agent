from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask


def test_nested_context_managers():
    app = application_instance()
    outer = BackgroundTask(app, 'outer')
    inner = BackgroundTask(app, 'inner')
    with outer:
        with inner:
            assert not inner.enabled
