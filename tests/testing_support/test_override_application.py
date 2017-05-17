from testing_support.fixtures import override_application_name

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction

@override_application_name(app_name='my-application-name')
@background_task()
def test_override_application_name():
    transaction = current_transaction()
    assert transaction.application.name == 'my-application-name'
