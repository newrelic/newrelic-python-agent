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

from newrelic.common.utilization import AzureFunctionUtilization


def test_utilization(monkeypatch):
    monkeypatch.setenv("REGION_NAME", "eastus2")
    monkeypatch.setenv(
        "WEBSITE_OWNER_NAME", "0b0d165f-aaaf-4a3b-b929-5f60588d95a3+testing-python-EastUS2webspace-Linux"
    )
    monkeypatch.setenv("WEBSITE_SITE_NAME", "test-func-linux")

    result = AzureFunctionUtilization.fetch()
    assert result, "Failed to parse utilization for Azure Functions."

    faas_app_name, cloud_region = result
    expected_faas_app_name = "/subscriptions/0b0d165f-aaaf-4a3b-b929-5f60588d95a3/resourceGroups/testing-python/providers/Microsoft.Web/sites/test-func-linux"
    assert faas_app_name == expected_faas_app_name
    assert cloud_region == "eastus2"


def test_utilization_bad_website_owner_name(monkeypatch):
    monkeypatch.setenv("REGION_NAME", "eastus2")
    monkeypatch.setenv("WEBSITE_OWNER_NAME", "ERROR")
    monkeypatch.setenv("WEBSITE_SITE_NAME", "test-func-linux")

    result = AzureFunctionUtilization.fetch()
    assert result is None, f"Expected failure but got result instead. {result}"
