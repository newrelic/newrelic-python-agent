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

import random
import tempfile
import json
import time
from pathlib import Path

import pytest
from testing_support.fixtures import failing_endpoint, override_generic_settings, override_application_settings
from testing_support.validators.validate_function_not_called import validate_function_not_called

from newrelic.api.application import application_instance
from newrelic.api.application import register_application
from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task
from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.core.application import Application
from newrelic.core.config import finalize_application_settings, global_settings
from newrelic.core.custom_event import create_custom_event
from newrelic.core.error_node import ErrorNode
from newrelic.core.external_node import ExternalNode
from newrelic.core.function_node import FunctionNode
from newrelic.core.log_event_node import LogEventNode
from newrelic.core.root_node import RootNode
from newrelic.core.stats_engine import CustomMetrics, DimensionalMetrics, SampledDataSet
from newrelic.core.transaction_node import TransactionNode
from newrelic.network.exceptions import RetryDataForRequest
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "samplers" / "harvest_sampling_rates.json"

def replace_section(setting):
    end = setting.split(".")[-1]
    if end in ("root", "remote_parent_sampled", "remote_parent_not_sampled"):
        return ".".join([*setting.split(".")[:-1], f"_{end}"])
    return setting

def parse_to_config_paths(settings, setting, config):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, dict) and not value:
                new_setting = replace_section(setting)
                settings[new_setting] = key
                continue
            # If there's a case where we have root.adaptive.sampling_target we also
            # need to set _root = "adaptive". This usually happens in the config or
            # env var parsing so this is special handling only needed for tests.
            if key in ("root", "remote_parent_sampled", "remote_parent_not_sampled"):
                new_setting = ".".join([setting, f"_{key}"])
                v = list(value.keys())[0] if isinstance(value, dict) else value
                settings[new_setting] = v
            new_setting = ".".join([setting, key])
            parse_to_config_paths(settings, new_setting, value)
    else:
        new_setting = replace_section(setting)
        settings[new_setting] = config

def load_tests():
    result = []
    with FIXTURE.open(encoding="utf-8") as fh:
        tests = json.load(fh)

    for test in tests:
        _id = test.pop("test_name", None)
        test_desc = test.pop("comment", None)

        config = test.pop("config", {})
        settings = {}
        parse_to_config_paths(settings, "distributed_tracing", config)

        if "distributed_tracing.sampler.adaptive_sampling_target" in settings:
            settings["sampling_target"] = settings.pop("distributed_tracing.sampler.adaptive_sampling_target")
        root = test.pop("root", 0)
        parent_sampled_no_matching_acct_id = test.pop("parent_sampled_no_matching_acct_id", 0)
        parent_not_sampled_no_matching_acct_id = test.pop("parent_not_sampled_no_matching_acct_id", 0)
        parent_sampled_matching_acct_id_sampled_true = test.pop("parent_sampled_matching_acct_id_sampled_true", 0)
        parent_not_sampled_matching_acct_id_sampled_true = test.pop("parent_not_sampled_matching_acct_id_sampled_true", 0)
        expected_sampled = test.pop("expected_sampled", None)
        expected_sampled_full = test.pop("expected_sampled_full", None)
        expected_sampled_partial = test.pop("expected_sampled_partial", None)
        expected_adaptive_sampler_decisions = test.pop("expected_adaptive_sampler_decisions", None)
        variance = test.pop("variance", 0)
        assert not test, f"{test} has not been fully parsed."

        param = pytest.param(
            settings,
            root,
            parent_sampled_no_matching_acct_id,
            parent_not_sampled_no_matching_acct_id,
            parent_sampled_matching_acct_id_sampled_true,
            parent_not_sampled_matching_acct_id_sampled_true,
            expected_sampled,
            expected_sampled_full,
            expected_sampled_partial,
            expected_adaptive_sampler_decisions,
            variance,
            id=_id
        )
        result.append(param)

    return result


@pytest.mark.parametrize(
    "settings,root,parent_sampled_no_matching_acct_id,parent_not_sampled_no_matching_acct_id,parent_sampled_matching_acct_id_sampled_true,parent_not_sampled_matching_acct_id_sampled_true,expected_sampled,expected_sampled_full,expected_sampled_partial,expected_adaptive_sampler_decisions,variance",
    load_tests(),
)
def test_harvest_sampling_rates(
    settings,
    root,
    parent_sampled_no_matching_acct_id,
    parent_not_sampled_no_matching_acct_id,
    parent_sampled_matching_acct_id_sampled_true,
    parent_not_sampled_matching_acct_id_sampled_true,
    expected_sampled,
    expected_sampled_full,
    expected_sampled_partial,
    expected_adaptive_sampler_decisions,
    variance,
):
    global total
    total = 0
    global partial
    partial = 0

    overide_settings = {"trusted_account_id": "33", "trusted_account_key": "33", "event_harvest_config.harvest_limits.span_event_data": 10000}
    overide_settings.update(settings)

    @override_application_settings(overide_settings)
    def _test(test_adaptive=False, test_totals=False, num_tests=1):
        app = application_instance("Python Agent Test (cross_agent_tests)")
        application = app._agent._applications.get("Python Agent Test (cross_agent_tests)")
        # Re-initialize sampler proxy after overriding settings.
        application.sampler.__init__(app.settings)
        # Re-initialize span event with new harvest value.
        application._stats_engine.reset_span_events()
        # Reset adaptive sampling decision count.
        global adaptive_sampling_decisons
        adaptive_sampling_decisons = 0

        @count_adaptive_sampling_decisions()
        @background_task()
        def _transaction(headers):
            txn = current_transaction()

            txn.accept_distributed_trace_headers(headers, "HTTP")

        for n in range(root):
            _transaction({})

        for n in range(parent_sampled_no_matching_acct_id):
            trace_id = f"{random.getrandbits(128):032x}"
            _transaction(
                {
                     "traceparent": f"00-{trace_id}-00f067aa0ba902b7-01",
                     "tracestate": "22@nr=0-0-33-2827902-0af7651916cd43dd--1-1.2-1518469636035",
                }
            )

        for n in range(parent_not_sampled_no_matching_acct_id):
            trace_id = f"{random.getrandbits(128):032x}"
            _transaction(
                {
                     "traceparent": f"00-{trace_id}-00f067aa0ba902b7-00",
                     "tracestate": "22@nr=0-0-33-2827902-0af7651916cd43dd--1-1.2-1518469636035",
                }
            )

        for n in range(parent_sampled_matching_acct_id_sampled_true):
            trace_id = f"{random.getrandbits(128):032x}"
            _transaction(
                {
                     "traceparent": f"00-{trace_id}-00f067aa0ba902b7-01",
                     "tracestate": "33@nr=0-0-33-2827902-0af7651916cd43dd--1-1.2-1518469636035",
                }
            )

        for n in range(parent_not_sampled_matching_acct_id_sampled_true):
            trace_id = f"{random.getrandbits(128):032x}"
            _transaction(
                {
                     "traceparent": f"00-{trace_id}-00f067aa0ba902b7-00",
                     "tracestate": "33@nr=0-0-33-2827902-0af7651916cd43dd--1-1.2-1518469636035",
                }
            )

        global total
        total += application._stats_engine.span_events.num_samples
        global partial
        partial += len([event for event in application._stats_engine.span_events.samples if event[2].get("nr.pg")])

        if test_totals:
            if expected_sampled is not None:
                assert expected_sampled - expected_sampled*variance <= total/num_tests <= expected_sampled +expected_sampled* variance
            if expected_sampled_partial is not None:
                assert expected_sampled_partial - expected_sampled_partial*variance <= partial/num_tests <= expected_sampled_partial + expected_sampled_partial*variance
            if expected_sampled_full is not None:
                assert expected_sampled_full - expected_sampled_full*variance <= (total - partial)/num_tests <= expected_sampled_full + expected_sampled_full*variance

        if test_adaptive and expected_adaptive_sampler_decisions is not None:
            assert expected_adaptive_sampler_decisions - expected_adaptive_sampler_decisions*variance <= adaptive_sampling_decisons <= expected_adaptive_sampler_decisions + expected_adaptive_sampler_decisions*variance

        application.harvest()
        assert application._stats_engine.span_events.num_samples == 0

    num_tests = 5
    for n in range(num_tests):
        if n == 0:
            _test(test_adaptive=True)
        elif n == num_tests-1:
            _test(num_tests=num_tests, test_totals=True)
        else:
            _test()

def count_adaptive_sampling_decisions():
    @transient_function_wrapper("newrelic.core.samplers.adaptive_sampler", "AdaptiveSampler.compute_sampled")
    def _count_adaptive_sampling_decisions(wrapped, instance, args, kwargs):
        global adaptive_sampling_decisons
        adaptive_sampling_decisons += 1
        return wrapped(*args, **kwargs)

    return _count_adaptive_sampling_decisions
