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

import tempfile
from pathlib import Path

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

from newrelic.core.config import global_settings
from newrelic.api.application import application_instance

from testing_support.fixtures import override_application_settings

settings = global_settings()


@override_application_settings(
    {
        "audit_log_file": tempfile.NamedTemporaryFile().name,
    }
)
def test_audit_logging():
    provider = MeterProvider()
    metrics.set_meter_provider(provider)

    meter = provider.get_meter("test_meter")
    counter = meter.create_counter(
        name="test_counter",
        description="A test counter",
        unit="1",
    )
    counter.add(2)
    counter.add(4, {"attribute_key": "attribute_value"})
    counter.add(3)

    for metric_reader in provider._all_metric_readers:
        metric_reader.collect()

    audit_log_path = Path(application_instance().settings.audit_log_file)

    with audit_log_path.open("rb") as f:
        assert b'v1/metrics' in f.read()
