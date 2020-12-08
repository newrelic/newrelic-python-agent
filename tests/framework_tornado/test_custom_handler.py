import pytest
from testing_support.fixtures import validate_transaction_metrics

pytestmark = pytest.mark.custom_app


def test_custom_handler(app):
    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version

    @validate_transaction_metrics(
        name='_target_application:CustomApplication',
        rollup_metrics=((FRAMEWORK_METRIC, 1),),
    )
    def _test():
        response = app.fetch('/')
        assert response.code == 200
        assert response.body == b'*'

    _test()
