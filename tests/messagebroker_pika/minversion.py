import sys
import pytest
import pika

pika_version_info = tuple(int(num) for num in pika.__version__.split('.')[:2])

new_pika_xfail = pytest.mark.xfail(
        condition=pika_version_info[0] > 0, strict=True,
        reason='test fails if pika version is 1.x or greater')
new_pika_xfail_py37 = pytest.mark.xfail(
        condition=pika_version_info[0] > 0 and sys.version_info >= (3, 7),
        strict=True,
        reason='test fails if pika version is 1.x or greater')
new_pika_skip = pytest.mark.skipif(
        condition=pika_version_info[0] > 0,
        reason='test hangs if pika version is 1.x or greater')
