"""This module implements functions for creating stack traces in format
required when sending errors and point of call for slow database queries
etc.

"""

import sys
import itertools

from .config import global_settings

_global_settings = global_settings()

def _extract_stack(f, skip=0, limit=None):
    if f is None:
        return []

    if limit is None:
        limit = _global_settings.max_stack_trace_lines

    # For calculating the stack trace we have the bottom most frame we
    # are interested in. We need to work upwards to get the full stack.
    # We append to a list and reverse at the end to get things in the
    # order we want as it is more effecient.

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
    if tb is None:
        return []

    while tb is not None:
        last = tb
        tb = tb.tb_next

    return _extract_stack(last.tb_frame, limit=limit)

def exception_stack(tb, limit=None):
    if tb is None:
        return []

    if limit is None:
        limit = _global_settings.max_stack_trace_lines

    # The traceback objects provide a chain for stack frames from the
    # top point of where the exception was caught, down to where the
    # exception was raised. This is not the complete stack, so we need
    # to prefix that with the stack trace for the point of the
    # try/except, which is derived from the frame associated with the
    # top most traceback object.

    _tb_stack = _extract_tb(tb, limit)

    if len(_tb_stack) < limit:
        _current_stack = _extract_stack(tb.tb_frame, skip=1,
                limit=limit-len(_tb_stack))
    else:
        _current_stack = []

    result = ['Traceback (most recent call last):']
    result.extend(['File "{source}", line {line}, in {name}'.format(**d)
            for d in itertools.chain(_current_stack, _tb_stack)])

    return result
