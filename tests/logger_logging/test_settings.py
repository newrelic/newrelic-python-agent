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

from newrelic.packages import six
from newrelic.api.background_task import background_task
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_log_event_count import validate_log_event_count
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

def basic_logging(logger):
    logger.warning("C")


_settings_matrix = [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, False),
]


@pytest.mark.parametrize("feature_setting,subfeature_setting,expected", _settings_matrix)
@reset_core_stats_engine()
def test_log_forwarding_settings(logger, feature_setting, subfeature_setting, expected):
    @override_application_settings({
        "application_logging.enabled": feature_setting,
        "application_logging.forwarding.enabled": subfeature_setting,
    })
    @validate_log_event_count(1 if expected else 0)
    @background_task()
    def test():
        basic_logging(logger)
        assert len(logger.caplog.records) == 1

    test()


@pytest.mark.parametrize("feature_setting,subfeature_setting,expected", _settings_matrix)
@reset_core_stats_engine()
def test_local_decorating_settings(logger, feature_setting, subfeature_setting, expected):
    @override_application_settings({
        "application_logging.enabled": feature_setting,
        "application_logging.local_decorating.enabled": subfeature_setting,
    })
    @background_task()
    def test():
        basic_logging(logger)
        assert len(logger.caplog.records) == 1
        message = logger.caplog.records.pop()
        if expected:
            assert len(message) > 1
        else:
            assert len(message) == 1

    test()


@pytest.mark.parametrize("feature_setting,subfeature_setting,expected", _settings_matrix)
@reset_core_stats_engine()
def test_log_metrics_settings(logger, feature_setting, subfeature_setting, expected):
    metric_count = 1 if expected else None
    txn_name = "test_settings:test_log_metrics_settings.<locals>.test" if six.PY3 else "test_settings:test"

    @override_application_settings({
        "application_logging.enabled": feature_setting,
        "application_logging.metrics.enabled": subfeature_setting,
    })
    @validate_transaction_metrics(
        txn_name,
        custom_metrics=[
            ("Logging/lines", metric_count),
            ("Logging/lines/WARNING", metric_count),
        ],
        background_task=True,
    )
    @background_task()
    def test():
        basic_logging(logger)
        assert len(logger.caplog.records) == 1

    test()
