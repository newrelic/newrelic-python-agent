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


INI_FILE_W3C = b"""
[newrelic]
distributed_tracing.exclude_newrelic_header = true
"""

INI_FILE_FULL_GRAN_CONFLICTS = b"""
[newrelic]
distributed_tracing.sampler.remote_parent_sampled = default
distributed_tracing.sampler.remote_parent_not_sampled = default
distributed_tracing.sampler.full_granularity.root = always_on
distributed_tracing.sampler.full_granularity.remote_parent_sampled = always_on
distributed_tracing.sampler.full_granularity.remote_parent_not_sampled = always_off
"""

INI_FILE_FULL_GRAN_CONFLICTS_ADAPTIVE = b"""
[newrelic]
distributed_tracing.sampler.remote_parent_sampled = always_on
distributed_tracing.sampler.remote_parent_not_sampled = always_off
distributed_tracing.sampler.full_granularity.root.adaptive.sampling_target = 5
distributed_tracing.sampler.full_granularity.remote_parent_sampled.adaptive.sampling_target = 10
distributed_tracing.sampler.full_granularity.remote_parent_not_sampled.adaptive.sampling_target = 20
"""

INI_FILE_FULL_GRAN_MULTIPLE_SAMPLERS = b"""
[newrelic]
distributed_tracing.sampler.full_granularity.root.adaptive.sampling_target = 5
distributed_tracing.sampler.full_granularity.remote_parent_sampled.adaptive.sampling_target = 10
distributed_tracing.sampler.full_granularity.remote_parent_not_sampled.adaptive.sampling_target = 20
distributed_tracing.sampler.full_granularity.root.trace_id_ratio_based.sampling_target = 5
distributed_tracing.sampler.full_granularity.remote_parent_sampled.trace_id_ratio_based.sampling_target = 10
distributed_tracing.sampler.full_granularity.remote_parent_not_sampled.trace_id_ratio_based.sampling_target = 20
"""

INI_FILE_PARTIAL_GRAN_CONFLICTS_ADAPTIVE = b"""
[newrelic]
distributed_tracing.sampler.partial_granularity.remote_parent_sampled = always_on
distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled = always_off
distributed_tracing.sampler.partial_granularity.root.adaptive.sampling_target = 5
distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target = 10
distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target = 20
"""

INI_FILE_PARTIAL_GRAN_MULTIPLE_SAMPLERS = b"""
[newrelic]
distributed_tracing.sampler.partial_granularity.root.adaptive.sampling_target = 5
distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target = 10
distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target = 20
distributed_tracing.sampler.partial_granularity.root.trace_id_ratio_based.sampling_target = 5
distributed_tracing.sampler.partial_granularity.remote_parent_sampled.trace_id_ratio_based.sampling_target = 10
distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.trace_id_ratio_based.sampling_target = 20
"""


# Tests for loading settings and testing for values precedence
@pytest.mark.parametrize("ini,env,expected_format", ((INI_FILE_EMPTY, {}, False), (INI_FILE_W3C, {}, True)))
def test_distributed_trace_setings(ini, env, expected_format, global_settings):
    settings = global_settings()
    assert settings.distributed_tracing.exclude_newrelic_header == expected_format


@pytest.mark.parametrize(
    "ini,env,expected",
    (
        (  # Defaults to adaptive (default) sampler.
            INI_FILE_EMPTY,
            {},
            ("default", "default", "default", None, None, None),
        ),
        (  # More specific full granularity path overrides less specific path in ini file.
            INI_FILE_FULL_GRAN_CONFLICTS,
            {},
            ("always_on", "always_on", "always_off", None, None, None),
        ),
        (  # More specific sampler path overrides less specific path in ini file.
            INI_FILE_FULL_GRAN_CONFLICTS_ADAPTIVE,
            {},
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
        (  # ini file configuration takes precedence over env vars.
            INI_FILE_FULL_GRAN_CONFLICTS_ADAPTIVE,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_ROOT_ADAPTIVE_SAMPLING_TARGET": "50",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "50",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "30",
            },
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
        (  # More specific full granularity path overrides less specific path in env vars.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_SAMPLED": "default",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_NOT_SAMPLED": "default",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_ROOT": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED": "always_off",
            },
            ("always_on", "always_on", "always_off", None, None, None),
        ),
        (  # Simple configuration works.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_ROOT": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_NOT_SAMPLED": "always_off",
            },
            ("always_on", "always_on", "always_off", None, None, None),
        ),
        (  # More specific sampler path overrides less specific path in env vars.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_ROOT": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_REMOTE_PARENT_NOT_SAMPLED": "always_off",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_ROOT_ADAPTIVE_SAMPLING_TARGET": "20",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "20",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_FULL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "20",
            },
            ("adaptive", "adaptive", "adaptive", 20, 20, 20),
        ),
        (  # Ignores other unknown samplers.
            INI_FILE_FULL_GRAN_MULTIPLE_SAMPLERS,
            {},
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
    ),
)
def test_full_granularity_precedence(ini, env, global_settings, expected):
    settings = global_settings()

    app_settings = finalize_application_settings(settings=settings)

    assert app_settings.distributed_tracing.sampler.full_granularity._root == expected[0]
    assert app_settings.distributed_tracing.sampler.full_granularity._remote_parent_sampled == expected[1]
    assert app_settings.distributed_tracing.sampler.full_granularity._remote_parent_not_sampled == expected[2]
    assert app_settings.distributed_tracing.sampler.full_granularity.root.adaptive.sampling_target == expected[3]
    assert (
        app_settings.distributed_tracing.sampler.full_granularity.remote_parent_sampled.adaptive.sampling_target
        == expected[4]
    )
    assert (
        app_settings.distributed_tracing.sampler.full_granularity.remote_parent_not_sampled.adaptive.sampling_target
        == expected[5]
    )


@pytest.mark.parametrize(
    "ini,env,expected",
    (
        (  # Defaults to adaptive (default) sampler.
            INI_FILE_EMPTY,
            {},
            ("default", "default", "default", None, None, None),
        ),
        (  # More specific sampler path overrides less specific path in ini file.
            INI_FILE_PARTIAL_GRAN_CONFLICTS_ADAPTIVE,
            {},
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
        (  # ini config takes precedence over env vars.
            INI_FILE_PARTIAL_GRAN_CONFLICTS_ADAPTIVE,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED": "always_off",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "20",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "30",
            },
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
        (  # Simple configuration works.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_ROOT": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED": "always_off",
            },
            ("always_on", "always_on", "always_off", None, None, None),
        ),
        (  # More specific sampler path overrides less specific path in env vars.
            INI_FILE_EMPTY,
            {
                "NEW_RELIC_ENABLED": "true",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_ROOT": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_SAMPLED": "always_on",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED": "always_off",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_ROOT_ADAPTIVE_SAMPLING_TARGET": "5",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "10",
                "NEW_RELIC_DISTRIBUTED_TRACING_SAMPLER_PARTIAL_GRANULARITY_REMOTE_PARENT_NOT_SAMPLED_ADAPTIVE_SAMPLING_TARGET": "20",
            },
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
        (  # Ignores other unknown samplers.
            INI_FILE_PARTIAL_GRAN_MULTIPLE_SAMPLERS,
            {},
            ("adaptive", "adaptive", "adaptive", 5, 10, 20),
        ),
    ),
)
def test_partial_granularity_precedence(ini, env, global_settings, expected):
    settings = global_settings()

    app_settings = finalize_application_settings(settings=settings)

    assert app_settings.distributed_tracing.sampler.partial_granularity._root == expected[0]
    assert app_settings.distributed_tracing.sampler.partial_granularity._remote_parent_sampled == expected[1]
    assert app_settings.distributed_tracing.sampler.partial_granularity._remote_parent_not_sampled == expected[2]
    assert app_settings.distributed_tracing.sampler.partial_granularity.root.adaptive.sampling_target == expected[3]
    assert (
        app_settings.distributed_tracing.sampler.partial_granularity.remote_parent_sampled.adaptive.sampling_target
        == expected[4]
    )
    assert (
        app_settings.distributed_tracing.sampler.partial_granularity.remote_parent_not_sampled.adaptive.sampling_target
        == expected[5]
    )
