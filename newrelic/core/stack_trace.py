# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module implements functions for creating stack traces in format
required when sending errors and point of call for slow database queries
etc.

"""

import itertools
import sys

from newrelic.core.config import global_settings

_global_settings = global_settings()


def _format_stack_trace(frames):
    result = ["Traceback (most recent call last):"]
    result.extend([f'File "{f["source"]}", line {f["line"]}, in {f["name"]}' for f in frames])
    return result


def _extract_stack(frame, skip, limit):
    if frame is None:
        return []

    # For calculating the stack trace we have the bottom most frame we
    # are interested in. We need to work upwards to get the full stack.
    # We append to a list and reverse at the end to get things in the
    # order we want as it is more efficient.

    n = 0
    frame_list = []

    while frame is not None and skip > 0:
        frame = frame.f_back
        skip -= 1

    while frame is not None and n < limit:
        frame_list.append({"source": frame.f_code.co_filename, "line": frame.f_lineno, "name": frame.f_code.co_name})

        frame = frame.f_back
        n += 1

    frame_list.reverse()

    return frame_list


def current_stack(skip=0, limit=None):
    if limit is None:
        limit = _global_settings.max_stack_trace_lines

    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        frame = sys.exc_info()[2].tb_frame.f_back

    return _format_stack_trace(_extract_stack(frame, skip, limit))


def _extract_tb(tb, limit):
    if tb is None:
        return []

    # The first traceback object is actually connected to the top most
    # frame where the exception was caught. As the limit needs to apply
    # to the bottom most, we need to traverse the complete list of
    # traceback objects and calculate as we go what would be the top
    # traceback object. Only once we have done that can we then work
    # out what frames to return.

    n = 0
    top = tb

    while tb is not None:
        if n >= limit:
            top = top.tb_next

        tb = tb.tb_next
        n += 1

    n = 0
    frame_list = []

    # We have now the top traceback object for the limit of what we are
    # to return. The bottom most will be that where the error occurred.

    tb = top

    while tb is not None and n < limit:
        frame = tb.tb_frame
        frame_list.append({"source": frame.f_code.co_filename, "line": tb.tb_lineno, "name": frame.f_code.co_name})

        tb = tb.tb_next
        n += 1

    return frame_list


def exception_stack(tb, limit=None):
    if tb is None:
        return []

    if limit is None:
        limit = _global_settings.max_stack_trace_lines

    # The traceback objects provide a chain for stack frames from the
    # top point of where the exception was caught, down to where the
    # exception was raised. This is not the complete stack, so we need
    # to prefix that with the stack trace for the point of the
    # try/except, which is derived from the frame one above that
    # associated with the top most traceback object.

    _tb_stack = _extract_tb(tb, limit)

    if len(_tb_stack) < limit:
        _current_stack = _extract_stack(tb.tb_frame.f_back, skip=0, limit=limit - len(_tb_stack))
    else:
        _current_stack = []

    return _format_stack_trace(itertools.chain(_current_stack, _tb_stack))
