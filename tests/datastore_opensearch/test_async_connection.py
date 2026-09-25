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

from conftest import OPENSEARCH_SETTINGS
from opensearchpy._async.http_aiohttp import AsyncConnection

HOST = {"scheme": "http", "host": OPENSEARCH_SETTINGS["host"], "port": int(OPENSEARCH_SETTINGS["port"])}


def test_connection_default():
    conn = AsyncConnection(**HOST)
    assert conn._nr_host_port == (OPENSEARCH_SETTINGS["host"], OPENSEARCH_SETTINGS["port"])


def test_connection_host_arg():
    conn = AsyncConnection("the_host")
    assert conn._nr_host_port == ("the_host", "9200")


def test_connection_args():
    conn = AsyncConnection("the_host", 9999)
    assert conn._nr_host_port == ("the_host", "9999")


def test_connection_kwargs():
    conn = AsyncConnection(host="foo", port=8888)
    assert conn._nr_host_port == ("foo", "8888")
