"""This module implements functions for creating stack traces in format
required when sending errors and point of call for slow database queries
etc.

"""

import sys

# No global configuration setting for number of stack frames to retain
# at this point. Python itself generally imposes a 1000 stack frame
# limit but this can be overridden if sys.tracebacklimit has been set.

_traceback_limit = (hasattr(sys, 'tracebacklimit') and
        sys.tracebacklimit or 1000)

def _extract_stack(f, skip=0, limit=None):
    if limit is None:
        limit = _traceback_limit

    n = 0
    l = []

    while f is not None and skip > 0:
        f = f.f_back
        skip -= 1

    while f is not None and n < limit:
        l.append(dict(source=f.f_code.co_filename,
                line=f.f_lineno, name=f.f_code.co_name))

        f = f.f_back
        n += 1

    l.reverse()

    return l

def current_stack(skip=0, limit=None):
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        f = sys.exc_info()[2].tb_frame.f_back

    result = ['Traceback (most recent call last):']
    result.extend(['File "{source}", line {line}, in {name}'.format(**d)
            for d in _extract_stack(f, skip, limit)])

    return result

def _extract_tb(tb, limit=None):
    if limit is None:
        limit = _traceback_limit

    n = 0
    l = []

    while tb is not None and n < limit:
        f = tb.tb_frame
        l.append(dict(source=f.f_code.co_filename,
                line=f.f_lineno, name=f.f_code.co_name))

        tb = tb.tb_next
        n += 1

    return l

def exception_stack(tb, limit=None):
    if tb is None:
        return []

    if limit is None:
        limit = _traceback_limit

    _tb_stack = _extract_tb(tb, limit)

    result = ['Traceback (most recent call last):']
    result.extend(['File "{source}", line {line}, in {name}'.format(**d)
            for d in _tb_stack])

    return result
