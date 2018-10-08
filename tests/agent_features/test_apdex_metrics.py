import webtest

from testing_support.validators.validate_apdex_metrics import (
        validate_apdex_metrics)
from testing_support.sample_applications import simple_app


normal_application = webtest.TestApp(simple_app)


# NOTE: This test validates that the server-side apdex_t is set to 0.5
# If the server-side configuration changes, this test will start to fail.


@validate_apdex_metrics(
    name='',
    group='Uri',
    apdex_t_min=0.5,
    apdex_t_max=0.5,
)
def test_apdex():
    normal_application.get('/')
