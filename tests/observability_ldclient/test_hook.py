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

import pytest
from ldclient import Context
from ldclient.evaluation import EvaluationDetail
from ldclient.hook import EvaluationSeriesContext
from testing_support.fixtures import dt_enabled
from testing_support.util import conditional_decorator
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.hooks.observability_ldclient import _NewRelicHook as NewRelicHook

FLAG_KEY = "my-flag"
CONTEXT_KEY = "user-key"
ENVIRONMENT_ID = "env-1234"

BASE_ATTRS = {
    "feature_flag.key": FLAG_KEY,
    "feature_flag.provider.name": "LaunchDarkly",
    "feature_flag.context.id": CONTEXT_KEY,
}
ALL_ATTR_NAMES = {
    "feature_flag.key",
    "feature_flag.provider.name",
    "feature_flag.context.id",
    "feature_flag.result.variationIndex",
    "feature_flag.result.reason.kind",
    "feature_flag.result.reason.inExperiment",
    "feature_flag.result.value",
    "feature_flag.set.id",
    "feature_flag.url.full",
}


def series_context(environment_id=None, context=None):
    return EvaluationSeriesContext(
        key=FLAG_KEY,
        context=context or Context.create(CONTEXT_KEY),
        default_value=False,
        method="variation",
        environment_id=environment_id,
    )


def exercise_hook(series_context, detail, base_uri=None):
    """Run after_evaluation, returning the hook's return value."""
    hook = NewRelicHook(base_uri=base_uri)
    data = {"some": "data"}

    result = hook.after_evaluation(series_context, data, detail)
    assert result is data
    return result


@pytest.mark.parametrize("in_transaction", [True, False], ids=("in_transaction", "outside_transaction"))
def test_hook_input_data_unmodified(in_transaction):
    original_data = {"some": "data"}
    data = original_data.copy()
    context = series_context()
    detail = EvaluationDetail(value=True, variation_index=0, reason={"kind": "FALLTHROUGH"})
    hook = NewRelicHook()

    assert hook.metadata.name == "newrelic-hook"

    @conditional_decorator(in_transaction, background_task(name="test_hook_metadata_unmodified"))
    def _test(data):
        assert bool(current_transaction()) == in_transaction

        data = hook.before_evaluation(series_context=context, data=data)
        assert data == original_data, "Data modified by hook."

        data = hook.after_evaluation(series_context=context, data=data, detail=detail)
        assert data == original_data, "Data modified by hook."

    _test(data)


@dt_enabled
@validate_span_events(
    count=1,
    exact_users={
        **BASE_ATTRS,
        "feature_flag.result.variationIndex": 2,
        "feature_flag.result.reason.kind": "RULE_MATCH",
        "feature_flag.result.reason.inExperiment": True,
        "feature_flag.result.value": "blue",
        "feature_flag.set.id": ENVIRONMENT_ID,
        "feature_flag.url.full": f"https://app.launchdarkly.com/goto/flags/{FLAG_KEY}?envId={ENVIRONMENT_ID}",
    },
)
@background_task()
def test_all_attributes_truthy():
    exercise_hook(
        series_context(environment_id=ENVIRONMENT_ID),
        EvaluationDetail(
            value="blue", variation_index=2, reason={"kind": "RULE_MATCH", "ruleIndex": 0, "inExperiment": True}
        ),
    )


@dt_enabled
@validate_span_events(
    count=1,
    # Falsey flag results (0 / False) are valid and must still be recorded.
    exact_users={**BASE_ATTRS, "feature_flag.result.variationIndex": 0, "feature_flag.result.value": False},
    unexpected_users={
        "feature_flag.result.reason.kind",
        "feature_flag.result.reason.inExperiment",
        "feature_flag.set.id",
        "feature_flag.url.full",
    },
)
@background_task()
def test_all_attributes_falsey():
    exercise_hook(
        series_context(environment_id=""),
        EvaluationDetail(value=False, variation_index=0, reason={"kind": "", "inExperiment": False}),
    )


@dt_enabled
@validate_span_events(count=1, exact_users=BASE_ATTRS, unexpected_users=ALL_ATTR_NAMES - set(BASE_ATTRS))
@background_task()
def test_all_attributes_none():
    # The SDK reports variation_index=None whenever the default value was returned.
    exercise_hook(series_context(environment_id=None), EvaluationDetail(value=None, variation_index=None, reason=None))


@pytest.mark.parametrize("reason", [{}, None], ids=["empty", "none"])
@dt_enabled
@validate_span_events(
    count=1,
    exact_users={**BASE_ATTRS, "feature_flag.result.value": True},
    unexpected_users={"feature_flag.result.reason.kind", "feature_flag.result.reason.inExperiment"},
)
@background_task()
def test_missing_reason_still_records_flag(reason):
    exercise_hook(series_context(), EvaluationDetail(value=True, variation_index=0, reason=reason))


@dt_enabled
@validate_span_events(count=1, exact_users={"feature_flag.result.reason.inExperiment": True})
@background_task()
def test_in_experiment_recorded():
    # LaunchDarkly reports experiment membership with the camelCase "inExperiment" reason key.
    exercise_hook(
        series_context(),
        EvaluationDetail(value=True, variation_index=0, reason={"kind": "FALLTHROUGH", "inExperiment": True}),
    )


@pytest.mark.parametrize(
    "reason",
    [{"kind": "FALLTHROUGH"}, {"kind": "FALLTHROUGH", "inExperiment": False}, {"in_experiment": True}],
    ids=["absent", "false", "snake_case"],
)
@dt_enabled
@validate_span_events(count=1, unexpected_users={"feature_flag.result.reason.inExperiment"})
@background_task()
def test_in_experiment_omitted(reason):
    exercise_hook(series_context(), EvaluationDetail(value=True, variation_index=0, reason=reason))


@pytest.mark.parametrize("value", [True, False, 0, 5, 1.5, "", "str"])
def test_value_recorded(value):
    @validate_span_events(count=1, exact_users={"feature_flag.result.value": value})
    @dt_enabled
    @background_task()
    def _test():
        exercise_hook(
            series_context(), EvaluationDetail(value=value, variation_index=0, reason={"kind": "FALLTHROUGH"})
        )

    _test()


@validate_span_events(count=1, exact_users=BASE_ATTRS, unexpected_users={"feature_flag.result.value"})
@dt_enabled
@background_task()
def test_value_none_omitted():
    exercise_hook(series_context(), EvaluationDetail(value=None, variation_index=None, reason={"kind": "FALLTHROUGH"}))


@pytest.mark.parametrize(
    "base_uri,expected_base",
    [
        (None, "https://app.launchdarkly.com"),
        ("https://ld.example.com", "https://ld.example.com"),
        ("https://ld.example.com/", "https://ld.example.com"),
    ],
    ids=["default", "custom", "trailing_slash"],
)
def test_environment_id_direct_link(base_uri, expected_base):
    @validate_span_events(
        count=1,
        exact_users={
            "feature_flag.set.id": ENVIRONMENT_ID,
            "feature_flag.url.full": f"{expected_base}/goto/flags/{FLAG_KEY}?envId={ENVIRONMENT_ID}",
        },
    )
    @dt_enabled
    @background_task()
    def _test():
        exercise_hook(
            series_context(environment_id=ENVIRONMENT_ID),
            EvaluationDetail(value=True, variation_index=0, reason={"kind": "FALLTHROUGH"}),
            base_uri=base_uri,
        )

    _test()


@pytest.mark.parametrize("environment_id", [None, "", 1234], ids=["none", "empty", "not_str"])
@validate_span_events(
    count=1, exact_users=BASE_ATTRS, unexpected_users={"feature_flag.set.id", "feature_flag.url.full"}
)
@dt_enabled
@background_task()
def test_environment_id_missing_omits_link(environment_id):
    exercise_hook(
        series_context(environment_id=environment_id),
        EvaluationDetail(value=True, variation_index=0, reason={"kind": "FALLTHROUGH"}),
    )


class BrokenContext:
    @property
    def key(self):
        raise ValueError("Broken context")


@validate_span_events(count=1, unexpected_users=ALL_ATTR_NAMES)
@dt_enabled
@background_task()
def test_exception_is_logged_and_swallowed(caplog):
    with caplog.at_level(logging.ERROR, logger="newrelic"):
        exercise_hook(
            series_context(context=BrokenContext()),
            EvaluationDetail(value=True, variation_index=0, reason={"kind": "FALLTHROUGH"}),
        )

    assert any("failed to enrich span" in record.getMessage() for record in caplog.records)
