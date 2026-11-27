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
import contextlib

import pytest
from _mock_ldobserve_pipeline import ld_spans, offline_ldobserve_pipeline
from opentelemetry import propagate, trace
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture
from testing_support.fixtures import newrelic_caplog as caplog

from newrelic.api.opentelemetry import opentelemetry_context_propagator

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "opentelemetry.enabled": True,
    "opentelemetry.traces.enabled": True,
    "launch_darkly_integration.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (observability_ldclient)", default_settings=_default_settings
)

FAKE_SDK_KEY = "not-a-real-secret"
FLAG_KEY = "example-flag-key"
CONTEXT_KEY = "example-context-key"


@pytest.fixture(scope="session")
def tracer():
    propagate.set_global_textmap(opentelemetry_context_propagator)

    tracer_provider = trace.get_tracer_provider()
    return tracer_provider.get_tracer()


@pytest.fixture(autouse=True)
def reset_integration_state(monkeypatch):
    from newrelic.core import stats_engine
    from newrelic.hooks import observability_ldclient

    monkeypatch.setattr(observability_ldclient, "OBSERVABILITY_PLUGIN_REGISTERED", False)
    monkeypatch.setattr(stats_engine, "LAUNCH_DARKLY_UNAVAILABLE_WARNED", False)


@pytest.fixture(scope="session")
def observability_plugin():
    from ldobserve import ObservabilityConfig, ObservabilityPlugin

    # The plugin constructor runs OTel auto-instrumentation and edits environment
    # variables, so only build it once per session.
    observability_config = ObservabilityConfig(
        service_name="test-service",
        service_version="0.0.0",
        # Avoid ldobserve's own background exporter reaching real LaunchDarkly
        # observability endpoints.
        otlp_endpoint="http://localhost:4317",
        backend_url="http://localhost:4317",
        disable_export_error_logging=True,
        instrument_logging=False,
    )
    return ObservabilityPlugin(observability_config)


@pytest.fixture
def ld_client(observability_plugin):
    """Context manager factory yielding an initialized LDClient backed by an in-memory TestData source."""
    from ldclient.client import LDClient
    from ldclient.config import Config
    from ldclient.integrations.test_data import TestData

    @contextlib.contextmanager
    def _ld_client(flag_key=FLAG_KEY, configure_flag=None, plugins=True):
        # In-memory flag data source: avoids any real streaming/polling connection
        # to LaunchDarkly while still running real flag-rule evaluation logic.
        td = TestData.data_source()
        flag = td.flag(flag_key)
        flag = configure_flag(flag) if configure_flag else flag.variation_for_all(True)
        td.update(flag)

        config = Config(
            FAKE_SDK_KEY,
            update_processor_class=td,
            send_events=False,
            diagnostic_opt_out=True,
            plugins=[observability_plugin] if plugins else None,
        )
        with LDClient(config=config) as client:
            assert client.is_initialized()
            yield client

    return _ld_client


@pytest.fixture
def ld_context():
    import ldclient

    return (
        ldclient.Context.builder(CONTEXT_KEY)
        .set("firstName", "Sandy")
        .set("lastName", "Smith")
        .set("email", "sandy@example.com")
        .set("groups", ["Acme", "Global Health Services"])
        .build()
    )
