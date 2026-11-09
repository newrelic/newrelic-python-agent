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

"""Mock replacements for the OTel SDK pipeline that ldobserve builds, so no telemetry leaves the test process."""

from types import SimpleNamespace

import pytest
from opentelemetry.sdk._logs.export import InMemoryLogExporter
from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class NoOpMetricExporter(MetricExporter):
    """Accepts OTLPMetricExporter's arguments and discards all metrics."""

    def __init__(self, *args, preferred_temporality=None, **kwargs):
        super().__init__(preferred_temporality=preferred_temporality)

    def export(self, metrics_data, timeout_millis=10_000, **kwargs):
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis=10_000):
        return True

    def shutdown(self, timeout_millis=30_000, **kwargs):
        pass


class RecordingSpanProcessor(SpanProcessor):
    """Records every ended span, including unsampled ones that exporters never see."""

    def __init__(self):
        self.spans = []

    def on_end(self, span):
        self.spans.append(span)


@pytest.fixture(autouse=True)
def offline_ldobserve_pipeline(monkeypatch):
    """Replace every network-facing component of ldobserve's real OTel pipeline.

    Tests that run the real ldobserve._init() still build the full pipeline, but nothing is
    exported over gRPC and no sampling config is fetched. Without this, the real metric
    exporter retries against an unreachable endpoint with exponential backoff when the
    MeterProvider shuts down at exit, hanging the test process.
    """
    from ldobserve._otel import configuration

    monkeypatch.setattr(configuration, "SamplingTraceExporter", lambda *args, **kwargs: InMemorySpanExporter())
    monkeypatch.setattr(configuration, "SamplingLogExporter", lambda *args, **kwargs: InMemoryLogExporter())
    monkeypatch.setattr(configuration, "OTLPMetricExporter", NoOpMetricExporter)
    monkeypatch.setattr(configuration, "get_sampling_config", lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def ld_spans(monkeypatch):
    """Replace the LaunchDarkly observability tracer with one that records spans in memory.

    ObservabilityPlugin.register() normally builds a real OTel pipeline (gRPC exporters and
    background threads) via ldobserve._init(). That is replaced so that registering the plugin
    installs the in-memory tracer instead, and no span ever leaves the process.

    Returns a namespace with:
      * spans: every span ended through the tracer, in order, including unsampled ones.
      * exporter: an InMemorySpanExporter, which (like ldobserve's real exporter) only receives sampled spans.
    """
    import ldobserve
    import ldobserve.observe

    recorder = RecordingSpanProcessor()
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(recorder)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    mock_observe_instance = SimpleNamespace(_tracer=provider.get_tracer("test"))

    def _init(*args, **kwargs):
        ldobserve.observe._instance = mock_observe_instance

    monkeypatch.setattr(ldobserve, "_init", _init)
    monkeypatch.setattr(ldobserve.observe, "_instance", mock_observe_instance)

    return SimpleNamespace(spans=recorder.spans, exporter=exporter)
