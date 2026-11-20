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

from newrelic.common.utilization import CommonUtilization, KubernetesUtilization


@pytest.mark.parametrize(
    "host",
    ("fd95:b6e3:daad::1", "2001:db8:0:0:0:0:0:1", "::1", "::ffff:192.0.2.13", "192.0.2.13", "kubernetes.default.svc"),
)
def test_kubernetes_service_host(monkeypatch, host):
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", f"  {host}  ")

    assert KubernetesUtilization.detect() == {"kubernetes_service_host": host}


@pytest.mark.parametrize("host", ("", " ", "fd95::1!", "fd95::1\ninvalid", "a" * 256))
def test_kubernetes_invalid_service_host(monkeypatch, host):
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", host)

    assert KubernetesUtilization.detect() is None


def test_kubernetes_service_host_missing(monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    assert KubernetesUtilization.detect() is None


def test_other_utilization_vendors_still_reject_colons():
    assert not CommonUtilization.valid_chars("fd95:b6e3:daad::1")
