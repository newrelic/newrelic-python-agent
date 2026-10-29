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
from conftest import FAKE_SDK_KEY
from ldclient.config import DEFAULT_BASE_URI, Config
from ldclient.hook import Hook, Metadata
from testing_support.fixtures import override_generic_settings

from newrelic.core.config import global_settings
from newrelic.hooks import observability_ldclient

CUSTOM_BASE_URI = "https://ld.example.com"

launch_darkly_disabled = override_generic_settings(global_settings(), {"launch_darkly_integration.enabled": False})


class UserHook(Hook):
    def __init__(self, name):
        self.name = name

    @property
    def metadata(self):
        return Metadata(name=self.name)

    def before_evaluation(self, series_context, data):
        return data

    def after_evaluation(self, series_context, data, detail):
        return data


def is_nr_hook(hook):
    return type(hook).__name__ == "NewRelicHook"


def nr_hooks(config):
    return [hook for hook in config.hooks if is_nr_hook(hook)]


@pytest.mark.parametrize(
    "make_hooks",
    [
        pytest.param(lambda hooks: None, id="none"),
        pytest.param(lambda hooks: [], id="empty"),
        pytest.param(list, id="list"),
        pytest.param(tuple, id="tuple"),
        pytest.param(lambda hooks: (hook for hook in hooks), id="generator"),
    ],
)
def test_nr_hook_appended(make_hooks):
    user_hooks = [UserHook("first"), UserHook("second")]
    hooks = make_hooks(user_hooks)
    expected_user_hooks = [] if not hooks else user_hooks

    config = Config(FAKE_SDK_KEY, hooks=hooks)

    assert config.hooks[:-1] == expected_user_hooks
    assert is_nr_hook(config.hooks[-1])
    assert len(nr_hooks(config)) == 1


def test_user_hooks_list_not_mutated():
    user_hooks = [UserHook("first")]

    config = Config(FAKE_SDK_KEY, hooks=user_hooks)

    assert user_hooks == [user_hooks[0]]
    assert len(config.hooks) == 2


@pytest.mark.parametrize(
    "args,kwargs,expected_base_uri",
    [
        pytest.param((FAKE_SDK_KEY,), {}, DEFAULT_BASE_URI, id="positional"),
        pytest.param((FAKE_SDK_KEY, CUSTOM_BASE_URI), {}, CUSTOM_BASE_URI, id="positional_base_uri"),
        pytest.param((), {"sdk_key": FAKE_SDK_KEY}, DEFAULT_BASE_URI, id="keyword"),
        pytest.param(
            (), {"sdk_key": FAKE_SDK_KEY, "base_uri": f"{CUSTOM_BASE_URI}/"}, CUSTOM_BASE_URI, id="keyword_base_uri"
        ),
    ],
)
def test_arguments_preserved_when_enabled(args, kwargs, expected_base_uri):
    user_hook = UserHook("user")
    config = Config(*args, hooks=[user_hook], **kwargs)

    assert config.sdk_key == FAKE_SDK_KEY
    assert config.base_uri == expected_base_uri
    nr_hook = nr_hooks(config)[0]
    assert nr_hook._base_uri == expected_base_uri
    assert len(config.hooks) == 2


@pytest.mark.parametrize(
    "args,kwargs,expected_base_uri",
    [
        pytest.param((FAKE_SDK_KEY,), {}, DEFAULT_BASE_URI, id="positional"),
        pytest.param((FAKE_SDK_KEY, CUSTOM_BASE_URI), {}, CUSTOM_BASE_URI, id="positional_base_uri"),
        pytest.param((), {"sdk_key": FAKE_SDK_KEY}, DEFAULT_BASE_URI, id="keyword"),
        pytest.param(
            (), {"sdk_key": FAKE_SDK_KEY, "base_uri": CUSTOM_BASE_URI}, CUSTOM_BASE_URI, id="keyword_base_uri"
        ),
    ],
)
@launch_darkly_disabled
def test_arguments_preserved_when_disabled(args, kwargs, expected_base_uri):
    user_hook = UserHook("user")
    config = Config(*args, hooks=[user_hook], **kwargs)

    assert config.sdk_key == FAKE_SDK_KEY
    assert config.base_uri == expected_base_uri
    assert config.hooks == [user_hook]


def test_hook_creation_failure_falls_back(monkeypatch, caplog):
    def _raise(*args, **kwargs):
        raise RuntimeError("Hook creation failed")

    monkeypatch.setattr(observability_ldclient, "NewRelicHook", _raise)
    user_hook = UserHook("user")

    with caplog.at_level(logging.ERROR, logger="newrelic"):
        config = Config(FAKE_SDK_KEY, CUSTOM_BASE_URI, hooks=[user_hook])

    assert config.sdk_key == FAKE_SDK_KEY
    assert config.base_uri == CUSTOM_BASE_URI
    assert config.hooks == [user_hook]
    assert any("Failed to add New Relic hook" in record.getMessage() for record in caplog.records)


def test_invalid_arguments_raise_once(caplog):
    with caplog.at_level(logging.ERROR, logger="newrelic"):
        with pytest.raises(TypeError, match="not_a_real_argument"):
            Config(FAKE_SDK_KEY, not_a_real_argument=True)

    assert not any("Failed to add New Relic hook" in record.getMessage() for record in caplog.records)


def test_error_raised_by_config_not_retried(caplog):
    # Errors raised by Config.__init__ itself should propagate from a single call, and not be
    # mistaken for a failure to add the New Relic hook.

    class InvalidURI:
        """Raises when Config.__init__ normalizes it, counting how many times that happens."""

        def __init__(self):
            self.calls = 0

        def rstrip(self, chars=None):
            self.calls += 1
            raise ValueError("Invalid URI")

    events_uri = InvalidURI()

    with caplog.at_level(logging.ERROR, logger="newrelic"):
        with pytest.raises(ValueError, match="Invalid URI"):
            Config(FAKE_SDK_KEY, events_uri=events_uri)

    assert events_uri.calls == 1
    assert not any("Failed to add New Relic hook" in record.getMessage() for record in caplog.records)


def test_plugin_warning_when_not_registered(ld_client, caplog):
    with caplog.at_level(logging.WARNING, logger="newrelic"):
        with ld_client(plugins=False):
            pass

    assert any(record.getMessage() == observability_ldclient.OBSERVABILITY_PLUGIN_WARNING for record in caplog.records)


def test_no_plugin_warning_when_registered(ld_client, caplog):
    with caplog.at_level(logging.WARNING, logger="newrelic"):
        with ld_client():
            pass

    assert observability_ldclient.OBSERVABILITY_PLUGIN_REGISTERED
    assert not any(
        record.getMessage() == observability_ldclient.OBSERVABILITY_PLUGIN_WARNING for record in caplog.records
    )


@launch_darkly_disabled
def test_no_plugin_warning_when_disabled(ld_client, caplog):
    with caplog.at_level(logging.WARNING, logger="newrelic"):
        with ld_client(plugins=False):
            pass

    assert not any(
        record.getMessage() == observability_ldclient.OBSERVABILITY_PLUGIN_WARNING for record in caplog.records
    )


def test_plugin_register_calls_original(ld_client, ld_spans, monkeypatch):
    import ldobserve.observe

    monkeypatch.setattr(ldobserve.observe, "_instance", None)

    with ld_client():
        assert observability_ldclient.OBSERVABILITY_PLUGIN_REGISTERED
        # The original register() ran, which called (the test double of) ldobserve._init.
        assert ldobserve.observe._instance is not None
