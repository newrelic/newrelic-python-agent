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
from testing_support.fixtures import (
    core_application_stats_engine,
    override_application_settings,
    reset_core_stats_engine,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import BackgroundTask


@override_application_settings({"event_harvest_config.harvest_limits.analytic_event_data": 1})
@pytest.mark.parametrize("first_transaction_saved", [True, False])
def test_priority_used_in_transaction_events(first_transaction_saved):
    first_priority = 1 if first_transaction_saved else 0
    second_priority = 0 if first_transaction_saved else 1

    @reset_core_stats_engine()
    def _test():
        # Stats engine
        stats_engine = core_application_stats_engine()

        with BackgroundTask(application(), name="T1") as txn:
            txn._priority = first_priority

        with BackgroundTask(application(), name="T2") as txn:
            txn._priority = second_priority

        transaction_events = list(stats_engine.transaction_events)
        assert len(transaction_events) == 1

        # Highest priority should win.
        # Priority can be 1 or 2 depending on randomness in sampling computation.
        assert stats_engine.transaction_events.pq[0][0] >= 1

        if first_transaction_saved:
            assert transaction_events[0][0]["name"].endswith("/T1")
        else:
            assert transaction_events[0][0]["name"].endswith("/T2")

    _test()


@override_application_settings({"event_harvest_config.harvest_limits.error_event_data": 1})
@pytest.mark.parametrize("first_transaction_saved", [True, False])
def test_priority_used_in_transaction_error_events(first_transaction_saved):
    first_priority = 1 if first_transaction_saved else 0
    second_priority = 0 if first_transaction_saved else 1

    @reset_core_stats_engine()
    def _test():
        with BackgroundTask(application(), name="T1") as txn:
            txn._priority = first_priority
            try:
                raise ValueError("OOPS")
            except ValueError:
                txn.notice_error()

        with BackgroundTask(application(), name="T2") as txn:
            txn._priority = second_priority
            try:
                raise ValueError("OOPS")
            except ValueError:
                txn.notice_error()

        # Stats engine
        stats_engine = core_application_stats_engine()

        error_events = list(stats_engine.error_events)
        assert len(error_events) == 1

        # highest priority should win
        assert stats_engine.error_events.pq[0][0] == 1

        if first_transaction_saved:
            assert error_events[0][0]["transactionName"].endswith("/T1")
        else:
            assert error_events[0][0]["transactionName"].endswith("/T2")

    _test()


@override_application_settings({"event_harvest_config.harvest_limits.custom_event_data": 1})
@pytest.mark.parametrize("first_transaction_saved", [True, False])
def test_priority_used_in_transaction_custom_events(first_transaction_saved):
    first_priority = 1 if first_transaction_saved else 0
    second_priority = 0 if first_transaction_saved else 1

    @reset_core_stats_engine()
    def _test():
        with BackgroundTask(application(), name="T1") as txn:
            txn._priority = first_priority
            txn.record_custom_event("foobar", {"foo": "bar"})

        with BackgroundTask(application(), name="T2") as txn:
            txn._priority = second_priority
            txn.record_custom_event("barbaz", {"foo": "bar"})

        # Stats engine
        stats_engine = core_application_stats_engine()

        custom_events = list(stats_engine.custom_events)
        assert len(custom_events) == 1

        # highest priority should win
        assert stats_engine.custom_events.pq[0][0] == 1

        if first_transaction_saved:
            assert custom_events[0][0]["type"] == "foobar"
        else:
            assert custom_events[0][0]["type"] == "barbaz"

    _test()
