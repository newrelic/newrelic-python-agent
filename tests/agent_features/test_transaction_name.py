from newrelic.api.background_task import background_task
from newrelic.api.transaction import set_transaction_name, set_background_task

from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
        'test_transaction_name:test_transaction_name_default_bt',
        group='Function', background_task=True)
@background_task()
def test_transaction_name_default_bt():
    pass

@validate_transaction_metrics(
        'test_transaction_name:test_transaction_name_default_wt',
        group='Function', background_task=False)
@background_task()
def test_transaction_name_default_wt():
    set_background_task(False)

@validate_transaction_metrics('Transaction', group='Custom',
        background_task=True)
@background_task()
def test_transaction_name_valid_override_bt():
    set_transaction_name('Transaction', group='Custom')

@validate_transaction_metrics('Transaction', group='Function',
        background_task=True)
@background_task()
def test_transaction_name_empty_group_bt():
    set_transaction_name('Transaction', group='')

@validate_transaction_metrics('Transaction', group='Function/Group',
        background_task=True)
@background_task()
def test_transaction_name_leading_slash_on_group_bt():
    set_transaction_name('Transaction', group='/Group')
