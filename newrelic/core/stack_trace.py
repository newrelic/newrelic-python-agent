"""This module implements functions for creating stack traces in format
required when sending errors and point of call for slow database queries
etc.

"""

import sys
import traceback

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

def stack_trace(tb=None, skip=0, limit=None):
    # The format here is the same as previously being sent, even though
    # it is not formatted correctly by the UI. After changes to allowed
    # stack trace format is allowed, this will return a dictionary
    # with high level properties of the stack trace, such as whether is
    # partial trace, as well as a reference to the actual stack frames.

    if tb is None:
        try:
            raise ZeroDivisionError
        except ZeroDivisionError:
            f = sys.exc_info()[2].tb_frame.f_back
    else:
        f = tb.tb_frame

    return ['File "{source}", line {line}, in {name}'.format(**d)
            for d in _extract_stack(f, skip, limit)]
