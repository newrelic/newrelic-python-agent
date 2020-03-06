import pytest
import time
import os
import subprocess

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


def test_function_filename_absolute_path():

    file_path = os.path.dirname(os.path.abspath(__file__))
    test_file_path = os.path.join(file_path,
                                  "_test_filename_linenumber.py")
    cmd = ['python', test_file_path]
    returncode = subprocess.call(cmd)
    assert returncode == 0
