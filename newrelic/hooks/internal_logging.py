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

from newrelic.common.object_wrapper import wrap_function_wrapper

def is_null_handlers(handler):
    from logging.handlers import NullHandler


def bind_callHandlers(record):
    return record


def wrap_callHandlers(wrapped, instance, args, kwargs):
    record = bind_callHandlers(*args, **kwargs)

    logger_name = getattr(instance, "name", None)
    if logger_name and logger_name.split(".")[0] == "newrelic":
        return wrapped(*args, **kwargs)

    wrap_handlers(instance)

    return wrapped(*args, **kwargs)


def wrap_handlers(logger):
    handlers = logger.handlers
    for handler in handlers:
        breakpoint()
        pass

    # Recurse up parent tree
    if logger.propagate and logger.parent is not None:
        wrap_handlers(logger.parent)


def instrument_cpython_Lib_logging_init(module):
    if hasattr(module, "Logger"):
        if hasattr(module.Logger, "callHandlers"):
            wrap_function_wrapper(module, "Logger.callHandlers", wrap_callHandlers)
