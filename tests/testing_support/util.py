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

import re
import socket
import sys
import tempfile
import time
from functools import wraps
from pathlib import Path


def _to_int(version_str):
    m = re.match(r"\d+", version_str)
    return int(m.group(0)) if m else 0


def version2tuple(version_str):
    """Convert version, even if it contains non-numeric chars.

    >>> version2tuple('9.4rc1.1')
    (9, 4)

    """

    parts = version_str.split(".")[:2]
    return tuple(map(_to_int, parts))


def instance_hostname(hostname):
    if hostname in ["localhost", "127.0.0.1"]:
        hostname = socket.gethostname()
    return hostname


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def conditional_decorator(condition, decorator):
    """Applies a decorator if the condition is true. Accepts 0 argument callables for the condition."""

    def _conditional_decorator(func):
        if callable(condition):
            condition_eval = condition()
        else:
            condition_eval = condition

        if condition_eval:
            return decorator(func)
        else:
            return func

    return _conditional_decorator


def retry(attempts=5, wait=5):
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            retry_count = 1
            while retry_count < attempts:
                try:
                    return test_func(*args, **kwargs)
                except AssertionError as assert_error:
                    time.sleep(wait)
                    retry_count += 1
            # Preserve original traceback in case assertion fails.
            return test_func(*args, **kwargs)

        return wrapper

    return decorator


def NamedTemporaryFile(*args, **kwargs):
    """A wrapper around tempfile.NamedTemporaryFile that fixes issues with file flags on Windows."""
    if sys.platform == "win32":
        # Set delete=False to prevent file flags being set incorrectly on Windows.
        kwargs["delete"] = False

    # Create the temporary file
    temp_file = tempfile.NamedTemporaryFile(*args, **kwargs)
    temp_file.path = Path(temp_file.name)  # Add path attribute for convenience

    # Patch the __exit__ method to manually remove the file on exit
    original_exit = temp_file.__exit__

    def remove_on_exit(*args, **kwargs):
        original_exit(*args, **kwargs)
        # Clean up the file manually
        if temp_file.path.exists():
            temp_file.path.unlink()

    temp_file.__exit__ = remove_on_exit

    return temp_file
