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


INI_FILE_INFINITE_TRACING = b"""
[newrelic]
infinite_tracing.trace_observer_host = y
infinite_tracing.trace_observer_port = 1234
infinite_tracing.span_queue_size = 2000
"""


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize(
    "ini,env,expected_host,log",
    (
        (INI_FILE_EMPTY, {}, None, None),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_HOST": "x://host:443/path"}, "host", "WARNING"),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_HOST": "who/knows"}, None, "ERROR"),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_HOST": ":shrug:"}, None, "ERROR"),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_HOST": "x"}, "x", None),
        (INI_FILE_INFINITE_TRACING, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_HOST": "x"}, "y", None),
    ),
)
def test_infinite_tracing_host(ini, env, expected_host, log, global_settings, caplog):
    settings = global_settings()
    assert settings.infinite_tracing.trace_observer_host == expected_host

    if log:
        records = caplog.get_records("setup")
        assert sum(1 for record in records if record.levelname == log) == 1
    else:
        assert not caplog.get_records("setup")


@pytest.mark.parametrize(
    "ini,env,expected_port",
    (
        (INI_FILE_EMPTY, {}, 443),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_PORT": "6789"}, 6789),
        (INI_FILE_INFINITE_TRACING, {"NEW_RELIC_INFINITE_TRACING_TRACE_OBSERVER_PORT": "6789"}, 1234),
    ),
)
def test_infinite_tracing_port(ini, env, expected_port, global_settings):
    settings = global_settings()
    assert settings.infinite_tracing.trace_observer_port == expected_port


# Tests for loading Infinite Tracing span queue size setting
# and testing values precedence
@pytest.mark.parametrize(
    "ini,env,expected_size",
    (
        (INI_FILE_EMPTY, {}, 10000),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE": "invalid"}, 10000),
        (INI_FILE_EMPTY, {"NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE": "5000"}, 5000),
        (INI_FILE_INFINITE_TRACING, {"NEW_RELIC_INFINITE_TRACING_SPAN_QUEUE_SIZE": "3000"}, 2000),
    ),
)
def test_infinite_tracing_span_queue_size(ini, env, expected_size, global_settings):
    settings = global_settings()
    assert settings.infinite_tracing.span_queue_size == expected_size


@pytest.mark.parametrize(
    "ini,env",
    ((INI_FILE_INFINITE_TRACING, {"NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_ENABLED": "true"}),),
)
def test_partial_granularity_dissabled_when_infinite_tracing_enabled(ini, env, global_settings):
    settings = global_settings()
    assert settings.distributed_tracing.sampler.partial_granularity.enabled
    assert settings.infinite_tracing.enabled

    app_settings = finalize_application_settings(settings=settings)

    assert not app_settings.distributed_tracing.sampler.partial_granularity.enabled
    assert app_settings.infinite_tracing.enabled
