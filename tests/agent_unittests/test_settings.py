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

from newrelic.core.config import finalize_application_settings

INI_FILE_EMPTY = b"""
[newrelic]
"""

INI_FILE_DEPRECATED_HARVEST_SETTINGS = b"""
[newrelic]
event_harvest_config.harvest_limits.analytic_event_data = 100
event_harvest_config.harvest_limits.span_event_data = 100
event_harvest_config.harvest_limits.error_event_data = 100
event_harvest_config.harvest_limits.custom_event_data = 100
event_harvest_config.harvest_limits.log_event_data = 100
"""

INI_FILE_NEW_HARVEST_SETTINGS = b"""
[newrelic]
transaction_events.max_samples_stored = 100
span_events.max_samples_stored = 100
error_collector.max_event_samples_stored = 100
custom_insights_events.max_samples_stored = 100
application_logging.forwarding.max_samples_stored = 100
"""

INI_FILE_NEW_AND_DEPRECATED_HARVEST_SETTINGS = b"""
[newrelic]
event_harvest_config.harvest_limits.analytic_event_data = 100
event_harvest_config.harvest_limits.span_event_data = 100
event_harvest_config.harvest_limits.error_event_data = 100
event_harvest_config.harvest_limits.custom_event_data = 100
event_harvest_config.harvest_limits.log_event_data = 100
transaction_events.max_samples_stored = 200
span_events.max_samples_stored = 200
error_collector.max_event_samples_stored = 200
custom_insights_events.max_samples_stored = 200
application_logging.forwarding.max_samples_stored = 200
"""

INI_FILE_NEW_HARVEST_SETTINGS_ZERO = b"""
[newrelic]
transaction_events.max_samples_stored = 0
span_events.max_samples_stored = 0
error_collector.max_event_samples_stored = 0
custom_insights_events.max_samples_stored = 0
application_logging.forwarding.max_samples_stored = 0
"""

INI_FILE_NEW_ZERO_AND_DEPRECATED_HARVEST_SETTINGS = b"""
[newrelic]
event_harvest_config.harvest_limits.analytic_event_data = 100
event_harvest_config.harvest_limits.span_event_data = 100
event_harvest_config.harvest_limits.error_event_data = 100
event_harvest_config.harvest_limits.custom_event_data = 100
event_harvest_config.harvest_limits.log_event_data = 100
transaction_events.max_samples_stored = 0
span_events.max_samples_stored = 0
error_collector.max_event_samples_stored = 0
custom_insights_events.max_samples_stored = 0
application_logging.forwarding.max_samples_stored = 0
"""


@pytest.mark.parametrize(
    "ini,env,expected",
    (
        (INI_FILE_DEPRECATED_HARVEST_SETTINGS, {}, 100),
        (INI_FILE_NEW_HARVEST_SETTINGS, {}, 100),
        (INI_FILE_NEW_AND_DEPRECATED_HARVEST_SETTINGS, {}, 200),
        (  # ENV VAR configuration works.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ANALYTICS_EVENTS_MAX_SAMPLES_STORED": 100,
                "NEW_RELIC_SPAN_EVENTS_MAX_SAMPLES_STORED": 100,
                "NEW_RELIC_ERROR_COLLECTOR_MAX_EVENT_SAMPLES_STORED": 100,
                "NEW_RELIC_CUSTOM_INSIGHTS_EVENTS_MAX_SAMPLES_STORED": 100,
                "NEW_RELIC_APPLICATION_LOGGING_FORWARDING_MAX_SAMPLES_STORED": 100,
            },
            100,
        ),
        # A value of 0 should be treated as a real possible setting, and not ignored in favor of the default value.
        (INI_FILE_NEW_HARVEST_SETTINGS_ZERO, {}, 0),
        # A value of 0 should also still win over the deprecated value, even if it is non-zero.
        (INI_FILE_NEW_ZERO_AND_DEPRECATED_HARVEST_SETTINGS, {}, 0),
    ),
)
def test_harvest_settings_precedence(ini, env, global_settings, expected):
    settings = global_settings()

    app_settings = finalize_application_settings(settings=settings)

    assert app_settings.event_harvest_config.harvest_limits.analytic_event_data == expected
    assert app_settings.event_harvest_config.harvest_limits.span_event_data == expected
    assert app_settings.event_harvest_config.harvest_limits.error_event_data == expected
    assert app_settings.event_harvest_config.harvest_limits.custom_event_data == expected
    assert app_settings.event_harvest_config.harvest_limits.log_event_data == expected
