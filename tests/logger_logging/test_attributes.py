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

import pytest
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_events import validate_log_events

from newrelic.api.background_task import background_task


@validate_log_events(
    [
        {  # Fixed attributes
            "message": "context_attrs: arg1",
            "context.args": "('arg1',)",
            "context.filename": "test_attributes.py",
            "context.funcName": "test_logging_default_context_attributes",
            "context.levelname": "ERROR",
            "context.levelno": 40,
            "context.module": "test_attributes",
            "context.name": "my_app",
            "context.pathname": str(__file__),
            "context.processName": "MainProcess",
            "context.threadName": "MainThread",
        }
    ],
    required_attrs=[  # Variable attributes
        "context.created",
        "context.lineno",
        "context.msecs",
        "context.process",
        "context.relativeCreated",
        "context.thread",
    ],
)
@validate_log_event_count(1)
@background_task()
def test_logging_default_context_attributes(logger):
    logger.error("context_attrs: %s", "arg1")


@validate_log_events([{"message": "extras", "context.extra_attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_logging_extra_attributes(logger):
    logger.error("extras", extra={"extra_attr": 1})


@validate_log_events([{"message": "exc_info"}], required_attrs=["context.exc_info"])
@validate_log_event_count(1)
@background_task()
def test_logging_exc_info_context_attributes(logger):
    try:
        raise RuntimeError("Oops")
    except Exception:
        logger.exception("exc_info")


@validate_log_events([{"message": "stack_info"}], required_attrs=["context.stack_info"])
@validate_log_event_count(1)
@background_task()
def test_logging_stack_info_context_attributes(logger):
    logger.error("stack_info", stack_info=True)


@validate_log_events([{"message": "A", "message.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_logging_dict_message_and_attributes(logger):
    logger.error({"message": "A", "attr": 1})


@validate_log_events([{"message.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_logging_dict_attributes_only(logger):
    logger.error({"attr": 1})
