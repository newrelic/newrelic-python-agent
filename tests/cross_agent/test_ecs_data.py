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

import os

import pytest
from fixtures.ecs_container_id.ecs_mock_server import bad_response_mock_server, mock_server
from test_pcf_utilization_data import Environ

import newrelic.common.utilization as u


@pytest.mark.parametrize("env_key", ["ECS_CONTAINER_METADATA_URI_V4", "ECS_CONTAINER_METADATA_URI"])
def test_ecs_docker_container_id(env_key, mock_server):
    mock_endpoint = f"http://localhost:{int(mock_server.port)}"
    env_dict = {env_key: mock_endpoint}

    with Environ(env_dict):
        data = u.ECSUtilization.detect()

    assert data == {"ecsDockerId": "1e1698469422439ea356071e581e8545-2769485393"}


@pytest.mark.parametrize(
    "env_dict", [{"ECS_CONTAINER_METADATA_URI_V4": "http:/invalid-uri"}, {"ECS_CONTAINER_METADATA_URI_V4": None}]
)
def test_ecs_docker_container_id_bad_uri(env_dict, mock_server):
    with Environ(env_dict):
        data = u.ECSUtilization.detect()

    assert data is None


def test_ecs_docker_container_id_bad_response(bad_response_mock_server):
    mock_endpoint = f"http://localhost:{int(bad_response_mock_server.port)}"
    env_dict = {"ECS_CONTAINER_METADATA_URI": mock_endpoint}

    with Environ(env_dict):
        data = u.ECSUtilization.detect()

    assert data is None


def test_ecs_container_id_no_metadata_env_vars():
    assert u.ECSUtilization.detect() is None
