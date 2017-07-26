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
