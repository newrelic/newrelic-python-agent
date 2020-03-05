import pytest
import time
import os

import newrelic.api.function_trace

from newrelic.common.metadata_utils import get_function_filename_linenumber


class MetadataUtilsTest(object):
    @newrelic.api.function_trace.function_trace()
    def class_method_test(self):
        pass


def function_test():
    pass


test_object = MetadataUtilsTest()


@pytest.mark.parametrize('func', (
    (function_test),
    (test_object.class_method_test),
))
def test_get_function_filename_linenumber(func):
    filename, line_number = get_function_filename_linenumber(func)
    assert filename == os.path.abspath(__file__)
    assert line_number


@pytest.mark.parametrize('func', (
    (time.sleep),
))
def test_get_function_filename_linenumber_error_handling(func):
    filename, line_number = get_function_filename_linenumber(func)
    assert filename is None
    assert line_number is None
