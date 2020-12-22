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
import mock
import os
import pytest

import newrelic.common.utilization as u

DOCKER_FIXTURE = os.path.join(os.curdir, 'fixtures', 'docker_container_id')


def _load_docker_test_attributes():
    """Returns a list of docker test attributes in the form:
       [(<filename>, <containerId>), ...]

    """
    docker_test_attributes = []
    test_cases = os.path.join(DOCKER_FIXTURE, 'cases.json')
    with open(test_cases, 'r') as fh:
        js = fh.read()
    json_list = json.loads(js)
    for json_record in json_list:
        docker_test_attributes.append(
            (json_record['filename'], json_record['containerId']))
    return docker_test_attributes


@pytest.mark.parametrize('filename, containerId',
                          _load_docker_test_attributes())
def test_docker_container_id(filename, containerId):
    path = os.path.join(DOCKER_FIXTURE, filename)
    with open(path, 'rb') as f:
        with mock.patch.object(u, 'open', create=True, return_value=f):
            if containerId is not None:
                assert u.DockerUtilization.detect() == {'id': containerId}
            else:
                assert u.DockerUtilization.detect() is None
