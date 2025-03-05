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


@pytest.fixture(scope="function")
def logger(structlog_caplog):
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.format_exc_info,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(),
        ],
        logger_factory=lambda *args, **kwargs: structlog_caplog,
    )

    _callsite_logger = structlog.get_logger(logger_attr=2)
    structlog.contextvars.bind_contextvars(context_attr=3)
    yield _callsite_logger
    structlog.contextvars.clear_contextvars()


@validate_log_events(
    [
        {  # Fixed attributes
            "message": "context_attrs: arg1",
            "context.kwarg_attr": 1,
            "context.logger_attr": 2,
            "context.context_attr": 3,
            "context.filename": "test_attributes.py",
            "context.func_name": "test_structlog_default_context_attributes",
            "context.module": "test_attributes",
            "context.pathname": str(__file__),
            "context.process_name": "MainProcess",
            "context.thread_name": "MainThread",
        }
    ],
    required_attrs=[  # Variable attributes
        "context.lineno",
        "context.process",
        "context.thread",
    ],
)
@validate_log_event_count(1)
@background_task()
def test_structlog_default_context_attributes(logger):
    logger.error("context_attrs: %s", "arg1", kwarg_attr=1)


@validate_log_events([{"message": "exc_info"}], required_attrs=["context.exception"])
@validate_log_event_count(1)
@background_task()
def test_structlog_exc_info_context_attributes(logger):
    try:
        raise RuntimeError("Oops")
    except Exception:
        logger.exception("exc_info")


@validate_log_events([{"message": "stack_info"}], required_attrs=["context.stack"])
@validate_log_event_count(1)
@background_task()
def test_structlog_stack_info_context_attributes(logger):
    logger.error("stack_info", stack_info=True)


@validate_log_events([{"message": "A", "message.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_structlog_message_attributes(logger):
    logger.error({"message": "A", "attr": 1})


@validate_log_events([{"message.attr": 1}])
@validate_log_event_count(1)
@background_task()
def test_structlog_attributes_only(logger):
    logger.error({"attr": 1})
