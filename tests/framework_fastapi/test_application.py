import pytest
from testing_support.fixtures import validate_transaction_metrics


@pytest.mark.parametrize("endpoint,transaction_name", (
    ("/sync", "_target_application:sync"),
    ("/async", "_target_application:non_sync"),
))
def test_application(app, endpoint, transaction_name):
    @validate_transaction_metrics(transaction_name)
    def _test():
        response = app.get(endpoint)
        assert response.status == 200

    _test()
