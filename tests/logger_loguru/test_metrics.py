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

from newrelic.api.background_task import background_task
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_custom_metrics_outside_transaction import validate_custom_metrics_outside_transaction
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


def exercise_logging(logger):
    logger.warning("C")
    logger.error("D")
    logger.critical("E")
    
    assert len(logger.caplog.records) == 3


_test_logging_unscoped_metrics = [
    ("Logging/lines", 3),
    ("Logging/lines/WARNING", 1),
    ("Logging/lines/ERROR", 1),
    ("Logging/lines/CRITICAL", 1),
]

@reset_core_stats_engine()
def test_logging_metrics_inside_transaction(logger):
    @validate_transaction_metrics(
        "test_metrics:test_logging_metrics_inside_transaction.<locals>.test",
        custom_metrics=_test_logging_unscoped_metrics,
        background_task=True,
    )
    @background_task()
    def test():
        exercise_logging(logger)

    test()


@reset_core_stats_engine()
def test_logging_metrics_outside_transaction(logger):
    @validate_custom_metrics_outside_transaction(_test_logging_unscoped_metrics)
    @reset_core_stats_engine()
    def test():
        exercise_logging(logger)

    test()
