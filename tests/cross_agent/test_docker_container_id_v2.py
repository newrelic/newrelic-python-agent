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

import json
from pathlib import Path

import pytest
from conftest import FAILING_ON_WINDOWS

import newrelic.common.utilization as u

DOCKER_FIXTURE = Path(__file__).parent / "fixtures" / "docker_container_id_v2"


def _load_docker_test_attributes():
    """Returns a list of docker test attributes in the form:
    [(<filename>, <containerId>), ...]

    """
    test_cases = DOCKER_FIXTURE / "cases.json"
    with test_cases.open(encoding="utf-8") as fh:
        json_list = json.load(fh)
    docker_test_attributes = [(json_record["filename"], json_record["containerId"]) for json_record in json_list]
    return docker_test_attributes


def mock_open(mock_file):
    def _mock_open(path, mode):
        filename = str(path)
        if filename == "/proc/self/cgroup":
            raise FileNotFoundError
        elif filename == "/proc/self/mountinfo":
            return mock_file
        raise RuntimeError

    return _mock_open


@FAILING_ON_WINDOWS
@pytest.mark.parametrize("filename, containerId", _load_docker_test_attributes())
def test_docker_container_id_v2(monkeypatch, filename, containerId):
    path = DOCKER_FIXTURE / filename
    with path.open("rb") as f:
        monkeypatch.setattr(Path, "open", mock_open(f), raising=False)
        if containerId is not None:
            assert u.DockerUtilization.detect() == {"id": containerId}
        else:
            assert u.DockerUtilization.detect() is None
