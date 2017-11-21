from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance


def test_transaction_running_at_request(app):
    nr_app = application_instance()
    with BackgroundTask(nr_app, 'test_transaction_running_at_request'):
        # Verify that weird things happening don't actually crash the
        # customer's application
        response = app.fetch('/simple/fast')
        assert response.code == 200


def test_get_status_raises_exception(app):
    response = app.fetch('/bad-get-status')
    assert response.code == 200
