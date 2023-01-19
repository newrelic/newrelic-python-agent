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

try:
    from elasticsearch.connection.base import Connection
    is_v8 = False
except ImportError:
    from elastic_transport._node._base import BaseNode as Connection
    from elastic_transport._models import NodeConfig
    is_v8 = True

SKIP_IF_V7 = pytest.mark.skipif(not is_v8, reason="Skipping v8 tests.")
SKIP_IF_V8 = pytest.mark.skipif(is_v8, reason="Skipping v7 tests.")


def test_connection_default():
    conn = Connection()
    assert conn._nr_host_port == ("localhost", "9200")


@SKIP_IF_V8
def test_connection_host_arg():
    conn = Connection("the_host")
    assert conn._nr_host_port == ("the_host", "9200")


@SKIP_IF_V8
def test_connection_args():
    conn = Connection("the_host", 9999)
    assert conn._nr_host_port == ("the_host", "9999")


@SKIP_IF_V8
def test_connection_kwargs():
    conn = Connection(host="foo", port=8888)
    assert conn._nr_host_port == ("foo", "8888")


@SKIP_IF_V7
def test_connection_config():
    conn = Connection(NodeConfig(host="foo", port=8888))
    assert conn._nr_host_port == ("foo", "8888")
