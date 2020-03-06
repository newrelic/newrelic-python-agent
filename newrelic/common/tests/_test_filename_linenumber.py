import os
from newrelic.common.metadata_utils import get_function_filename_linenumber


def func():
    pass


def main():
    filename, line_number = get_function_filename_linenumber(func)
    assert filename == os.path.abspath(__file__), \
                                       "Found filename: %s" % filename
    assert line_number == 5, "Found line number: %s" % line_number


if __name__ == "__main__":
    main()
