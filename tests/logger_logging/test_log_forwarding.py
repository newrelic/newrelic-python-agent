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

import logging

from newrelic.api.background_task import background_task
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction

from newrelic.packages import six

from testing_support.fixtures import reset_core_stats_engine
from testing_support.util import conditional_decorator
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.validators.validate_log_event_count_outside_transaction import (
    validate_log_event_count_outside_transaction,
)
from testing_support.validators.validate_log_events import validate_log_events
from testing_support.validators.validate_log_events_outside_transaction import validate_log_events_outside_transaction


def set_trace_ids():
    txn = current_transaction()
    if txn:
        txn._trace_id = "abcdefgh12345678"
    trace = current_trace()
    if trace:
        trace.guid = "abcdefgh"

def exercise_logging(logger):
    set_trace_ids()

    logger.debug("A")
    logger.info("B")
    logger.warning("C")
    logger.error("D")
    logger.critical("E")

    logger.error({"message": "F", "attr": 1})
    logger.warning({"attr": "G"})

    assert len(logger.caplog.records) == 5

def update_all(events, attrs):
    for event in events:
        event.update(attrs)


_common_attributes_service_linking = {
    "timestamp": None,
    "hostname": None,
    "entity.name": "Python Agent Test (logger_logging)",
    "entity.guid": None,
}
_common_attributes_trace_linking = {"span.id": "abcdefgh", "trace.id": "abcdefgh12345678"}
_common_attributes_trace_linking.update(_common_attributes_service_linking)

_test_logging_inside_transaction_events = [
    {"message": "C", "level": "WARNING"},
    {"message": "D", "level": "ERROR"},
    {"message": "E", "level": "CRITICAL"},
    {"message": "F", "level": "ERROR", "message.attr": 1},
    {"message.attr": "G", "level": "WARNING"},
]
update_all(_test_logging_inside_transaction_events, _common_attributes_trace_linking)


@validate_log_events(_test_logging_inside_transaction_events)
@validate_log_event_count(5)
@background_task()
def test_logging_inside_transaction(logger):
    exercise_logging(logger)


_test_logging_outside_transaction_events = [
    {"message": "C", "level": "WARNING"},
    {"message": "D", "level": "ERROR"},
    {"message": "E", "level": "CRITICAL"},
    {"message": "F", "level": "ERROR", "message.attr": 1},
    {"message.attr": "G", "level": "WARNING"},
]
update_all(_test_logging_outside_transaction_events, _common_attributes_service_linking)


@reset_core_stats_engine()
@validate_log_events_outside_transaction(_test_logging_outside_transaction_events)
@validate_log_event_count_outside_transaction(5)
def test_logging_outside_transaction(logger):
    exercise_logging(logger)


# Default context attrs
@validate_log_events(
    [
        {  # Fixed attributes
            "message": "context_attrs: arg1",
            "context.args": "('arg1',)",
            "context.filename": "test_log_forwarding.py",
            "context.funcName": "test_logging_context_attributes",
            "context.levelname": "ERROR",
            "context.levelno": 40,
            "context.module": "test_log_forwarding",
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
    forgone_attrs=["context.exc_info"],
)
@validate_log_events([{"message": "extras", "context.extra_attr": 1}])  # Extras on logger calls
@validate_log_events([{"message": "exc_info"}], required_attrs=["context.exc_info"])  # Exception info generation
# Stack info generation only on Py3
@conditional_decorator(six.PY3, validate_log_events([{"message": "stack_info"}], required_attrs=["context.stack_info"]))
@validate_log_event_count(4 if six.PY3 else 3)
@background_task()
def test_logging_context_attributes(logger):
    logger.error("context_attrs: %s", "arg1")
    logger.error("extras", extra={"extra_attr": 1})
    
    try:
        raise RuntimeError("Oops")
    except Exception:
        logger.error("exc_info", exc_info=True)

    if six.PY3:
        logger.error("stack_info", stack_info=True)

@reset_core_stats_engine()
def test_logging_newrelic_logs_not_forwarded(logger):
    @validate_log_event_count(0)
    @background_task()
    def test():
        nr_logger = logging.getLogger("newrelic")
        nr_logger.addHandler(logger.caplog)
        nr_logger.error("A")
        assert len(logger.caplog.records) == 1

    test()
