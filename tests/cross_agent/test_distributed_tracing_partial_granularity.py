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

import base64
import json
import random
from pathlib import Path

import pytest
import webtest
from testing_support.fixtures import override_application_settings, validate_attributes
from testing_support.validators.validate_error_event_attributes import validate_error_event_attributes
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

import newrelic.agent
from newrelic.api.application import application_settings
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.encoding_utils import (
    PARENT_TYPE,
    DistributedTracePayload,
    NrTraceState,
    W3CTraceParent,
    W3CTraceState,
)
from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.external_node import ExternalNode
from newrelic.core.function_node import FunctionNode
from newrelic.core.root_node import RootNode

FIXTURE_PARTIAL_GRANULARITY = Path(__file__).parent / "fixtures" / "distributed_tracing" / "partial_granularity.json"
FIXTURE_TRACER_INFO_STANDARD = Path(__file__).parent / "fixtures" / "distributed_tracing" / "tracer_info_standard.json"
FIXTURE_TRACER_INFO_TOO_MANY = (
    Path(__file__).parent / "fixtures" / "distributed_tracing" / "tracer_info_compact_too_many.json"
)


def load_tests():
    result = []
    with FIXTURE_PARTIAL_GRANULARITY.open(encoding="utf-8") as fh:
        tests = json.load(fh)

    for test in tests:
        _id = test.pop("test_name", None)
        test_desc = test.pop("comment", None)
        tracer_info = test.pop("tracer_info", None)
        expected_spans = test.pop("expected_spans", [])
        unexpected_spans = test.pop("unexpected_spans", [])
        expected_metrics = test.pop("expected_metrics", [])
        partial_granularity_type = test.pop("partial_granularity_type", "essential")
        assert not test, f"{test} has not been fully parsed"

        param = pytest.param(
            partial_granularity_type, tracer_info, expected_spans, unexpected_spans, expected_metrics, id=_id
        )
        result.append(param)

    return result


@pytest.fixture
def tracer_info_standard():
    def create_span_tree(root, data):
        for span in data:
            if "external" in span["name"].lower():
                agent_attrs = span["agent_attrs"]
                node = ExternalNode(
                    library="requests",
                    url=agent_attrs.pop("http.url"),
                    method="GET",
                    children=[],
                    start_time=span["timestamp"] / 1000,  # Convert to seconds.
                    end_time=span["timestamp"] / 1000 + span["duration_millis"] / 1000,
                    duration=span["duration_millis"] / 1000,  # Convert to seconds.
                    exclusive=0.1,
                    params={},
                    guid=span["name"],
                    agent_attributes=agent_attrs,
                    user_attributes=span.get("user_attrs", {}),
                    span_link_events=None,
                    span_event_events=None,
                )
                if "children" in span:
                    create_span_tree(node, span["children"])
            elif "inprocess" in span["name"].lower():
                node = FunctionNode(
                    group="Function",
                    name=span["name"],
                    children=[],
                    start_time=span["timestamp"] / 1000,  # Convert to seconds.
                    end_time=span["timestamp"] / 1000 + span["duration_millis"] / 1000,
                    duration=span["duration_millis"] / 1000,  # Convert to seconds.
                    exclusive=0.1,
                    label=None,
                    params=None,
                    rollup=None,
                    guid=span["name"],
                    agent_attributes={},
                    user_attributes={},
                    span_link_events=None,
                    span_event_events=None,
                )
                if "children" in span:
                    create_span_tree(node, span["children"])
            elif span["name"].startswith("Llm/"):
                node = FunctionNode(
                    group="Llm",
                    name=span["name"][4:],
                    children=[],
                    start_time=span["timestamp"] / 1000,  # Convert to seconds.
                    end_time=span["timestamp"] / 1000 + span["duration_millis"] / 1000,
                    duration=span["duration_millis"] / 1000,  # Convert to seconds.
                    exclusive=0.1,
                    label=None,
                    params=None,
                    rollup=None,
                    guid=span["name"],
                    agent_attributes={},
                    user_attributes={},
                    span_link_events=None,
                    span_event_events=None,
                )
                if "children" in span:
                    create_span_tree(node, span["children"])
            else:
                raise ValueError("Unknown span type")
            root.children.append(node)

    data = []
    with FIXTURE_TRACER_INFO_STANDARD.open(encoding="utf-8") as fh:
        data = json.load(fh)
    root = data["root_tracer"]
    root_node = RootNode(
        name=root["name"],
        children=[],
        start_time=root["timestamp"] / 1000,  # Convert to seconds.
        end_time=root["timestamp"] / 1000 + root["duration_millis"] / 1000,
        duration=root["duration_millis"] / 1000,  # Convert to seconds.
        exclusive=0.1,
        guid=root["name"],
        agent_attributes={},
        user_attributes={},
        path="OtherTransaction/Function/main",
        trusted_parent_span=None,
        tracing_vendors=None,
        span_link_events=None,
        span_event_events=None,
    )
    create_span_tree(root_node, root["children"])
    return root_node


@pytest.fixture
def tracer_info_too_many():
    def create_external(span):
        agent_attrs = span["agent_attrs"]
        node = ExternalNode(
            library="requests",
            url=agent_attrs["http.url"],
            method="GET",
            children=[],
            start_time=span["timestamp"] / 1000,  # Convert to seconds.
            end_time=span["timestamp"] / 1000 + span["duration_millis"] / 1000,
            duration=span["duration_millis"] / 1000,  # Convert to seconds.
            exclusive=0.1,
            params={},
            guid=span["name"],
            agent_attributes={key: value for key, value in agent_attrs.items() if key != "http.url"},
            user_attributes=span.get("user_attrs", {}),
            span_link_events=None,
            span_event_events=None,
        )
        return node

    data = []
    with FIXTURE_TRACER_INFO_TOO_MANY.open(encoding="utf-8") as fh:
        data = json.load(fh)
    root = data["root_tracer"]
    root_node = RootNode(
        name=root["name"],
        children=[],
        start_time=root["timestamp"] / 1000,  # Convert to seconds.
        end_time=root["timestamp"] / 1000 + root["duration_millis"] / 1000,
        duration=root["duration_millis"] / 1000,  # Convert to seconds.
        exclusive=0.1,
        guid=root["name"],
        agent_attributes={},
        user_attributes={},
        path="OtherTransaction/Function/main",
        trusted_parent_span=None,
        tracing_vendors=None,
        span_link_events=None,
        span_event_events=None,
    )
    children_formula = root["children_formula"]
    children = [
        create_external(
            {
                "timestamp": child * children_formula["duration_millis"]
                + child * children_formula["duration_gap_millis"],
                "duration_millis": children_formula["duration_millis"],
                "name": f"{children_formula['name_prefix']}{child + 1}",
                "agent_attrs": children_formula["agent_attrs"],
            }
        )
        for child in range(children_formula["num_children"])
    ]
    root_node.children.extend(children)
    return root_node


@pytest.mark.parametrize(
    "partial_granularity_type,tracer_info,expected_spans,unexpected_spans,expected_metrics", load_tests()
)
def test_distributed_tracing_partial_granularity(
    partial_granularity_type,
    tracer_info,
    expected_spans,
    unexpected_spans,
    expected_metrics,
    tracer_info_standard,
    tracer_info_too_many,
):
    if tracer_info == "tracer_info_standard.json":
        root = tracer_info_standard
    elif tracer_info == "tracer_info_compact_too_many.json":
        root = tracer_info_too_many
    else:
        raise ValueError(f"Unknown tracer_info={tracer_info}")

    @background_task()
    def _test():
        settings = application_settings()
        settings.distributed_tracing.sampler.full_granularity.enabled = False
        settings.distributed_tracing.sampler.partial_granularity.enabled = True
        settings.distributed_tracing.sampler.partial_granularity.type = partial_granularity_type

        span_event_method = root.PARTIAL_GRANULARITY_SPAN_EVENT_METHODS.get(
            settings.distributed_tracing.sampler.partial_granularity.type,
            root.PARTIAL_GRANULARITY_SPAN_EVENT_METHODS["essential"],
        )
        ct_exit_spans = {"instrumented": 0, "kept": 0, "dropped_ids": 0}
        spans = list(
            root.span_events_partial_granularity(
                settings,
                span_event_method,
                base_attrs=None,
                parent_guid=None,
                attr_class=dict,
                ct_exit_spans=ct_exit_spans,
            )
        )

        for expected_span in expected_spans:
            expected_span_name = list(expected_span.keys())[0]
            expected_span_attrs = expected_span[expected_span_name]
            expected_span_parent = expected_span_attrs["parent"]
            expected_span_exact_intrinsics = expected_span_attrs.get("intrinsics", {}).get("exact", {})
            expected_span_intrinsics = expected_span_attrs.get("intrinsics", {}).get("expected", {})
            expected_span_exact_agents = expected_span_attrs.get("agent_attrs", {}).get("exact", {})
            expected_span_agents = expected_span_attrs.get("agent_attrs", {}).get("expected", {})

            matching_span = None
            for span in spans:
                if span[0]["guid"] == expected_span_name:
                    matching_span = span
                    break
            assert matching_span[0].get("parentId") == expected_span_parent
            for attr, value in expected_span_exact_intrinsics.items():
                if attr == "nr.durations":
                    assert round(matching_span[0].get(attr, None), 2) == value
                else:
                    assert matching_span[0].get(attr, None) == value
            for attr in expected_span_intrinsics:
                assert attr in matching_span[0]
            for attr, value in expected_span_exact_agents.items():
                assert matching_span[2].get(attr, None) == value
            for attr in expected_span_agents:
                assert attr in matching_span[2]

        for unexpected in unexpected_spans:
            for span in spans:
                assert span[0]["name"] != unexpected

        if expected_metrics:
            metric = expected_metrics.pop(0)
            assert metric[0] == "Supportability/Java/PartialGranularity/NrIds/Dropped"
            assert metric[1] == ct_exit_spans["dropped_ids"]
        assert not expected_metrics  # assert all expected_metrics have been asserted

    _test()
