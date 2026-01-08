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

import asyncio
import copy
import json
import random
import time

from newrelic.core.samplers.adaptive_sampler import AdaptiveSampler
from newrelic.core.samplers.trace_id_ratio_based_sampler import TraceIdRatioBasedSampler
from pathlib import Path
import pytest
import webtest
from testing_support.fixtures import override_application_settings, validate_attributes, validate_attributes_complete
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_function_called import validate_function_called
from testing_support.validators.validate_function_not_called import validate_function_not_called
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_object_attributes import validate_transaction_object_attributes

from newrelic.api.application import application_instance
from newrelic.api.function_trace import function_trace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper

try:
    from newrelic.core.infinite_tracing_pb2 import AttributeValue, Span
except:
    AttributeValue = None
    Span = None

from testing_support.mock_external_http_server import MockExternalHTTPHResponseHeadersServer
from testing_support.validators.validate_span_events import check_value_equals, validate_span_events

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask, background_task
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import (
    accept_distributed_trace_headers,
    current_span_id,
    current_trace_id,
    current_transaction,
    insert_distributed_trace_headers,
)
from newrelic.api.web_transaction import WSGIWebTransaction
from newrelic.api.wsgi_application import wsgi_application
from newrelic.core.attribute import Attribute

FIXTURE = Path(__file__).parent / "fixtures" / "samplers" / "sampler_configuration.json"

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
        expected_samplers = test.pop("expected_samplers", {})
        param = pytest.param(
            settings,
            expected_samplers,
            id=_id
        )
        result.append(param)

    return result

SECTIONS = {
    "full_root": (True, 0),
    "full_remote_parent_sampled": (True, 1),
    "full_remote_parent_not_sampled": (True, 2),
    "partial_root": (False, 0),
    "partial_remote_parent_sampled": (False, 1),
    "partial_remote_parent_not_sampled": (False, 2),
}

@pytest.mark.parametrize(
    "settings,expected_samplers",
    load_tests(),
)
def test_sampler_configuration(
    settings,
    expected_samplers,
):
    @override_application_settings(settings)
    @background_task()
    def _test():
        txn = current_transaction()
        application = txn._application._agent._applications.get(txn.settings.app_name)
        # Re-initialize sampler proxy after overriding settings.
        application.sampler.__init__(txn.settings)

        for sampler, attributes in expected_samplers.items():
            instance = SECTIONS[sampler]
            sampler_instance = application.sampler.get_sampler(*instance)
            if attributes["type"] == "adaptive":
                assert isinstance(sampler_instance, AdaptiveSampler)
            elif attributes["type"] == "trace_id_ratio_based":
                assert isinstance(sampler_instance, TraceIdRatioBasedSampler)
                if "ratio" in attributes:
                    assert sampler_instance.ratio == attributes["ratio"]
            if attributes.get("is_global_adaptive_sampler", False):
                assert sampler_instance is application.sampler._samplers["global"]

    _test()
