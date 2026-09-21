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
import inspect

import opensearchpy
import opensearchpy._async.client as async_client_module
import pytest
from opensearchpy.client.utils import NamespacedClient
from testing_support.validators.validate_datastore_trace_inputs import validate_datastore_trace_inputs

from newrelic.api.background_task import background_task


@pytest.mark.parametrize(
    "sub_module,method,args,kwargs,expected_index",
    [
        (None, "exists", (), {"index": "contacts", "id": 1}, "contacts"),
        (None, "info", (), {}, None),
        (None, "search", (), {"index": "contacts"}, "contacts"),
        (None, "msearch", (), {"body": [{}, {"query": {"match_all": {}}}], "index": "contacts"}, "contacts"),
        ("indices", "exists", (), {"index": "contacts"}, "contacts"),
        ("indices", "exists_template", (), {"name": "no-exist"}, None),
        ("cat", "count", (), {"index": "contacts"}, "contacts"),
        ("cat", "health", (), {}, None),
        ("cluster", "get_settings", (), {}, None),
        ("cluster", "health", (), {"index": "contacts"}, "contacts"),
        ("nodes", "info", (), {}, None),
        ("snapshot", "status", (), {}, None),
        ("tasks", "list", (), {}, None),
        ("ingest", "processor_grok", (), {}, None),
    ],
)
def test_method_on_async_client_datastore_trace_inputs(
    loop, async_client, sub_module, method, args, kwargs, expected_index
):
    expected_operation = f"{sub_module}.{method}" if sub_module else method

    @validate_datastore_trace_inputs(target=expected_index, operation=expected_operation)
    @background_task()
    async def _test():
        if not sub_module:
            await getattr(async_client, method)(*args, **kwargs)
        else:
            await getattr(getattr(async_client, sub_module), method)(*args, **kwargs)

    loop.run_until_complete(_test())


def _test_methods_wrapped(_object, ignored_methods=None):
    if not ignored_methods:
        ignored_methods = {"perform_request", "transport", "options"}

    def is_wrapped(m):
        return hasattr(getattr(_object, m), "__wrapped__")

    methods = {m for m in dir(_object) if not m[0] == "_"}
    uninstrumented = {m for m in (methods - ignored_methods) if not is_wrapped(m)}
    assert not uninstrumented, f"There are uninstrumented methods: {uninstrumented}"


def _all_async_client_classes():
    classes = [opensearchpy.AsyncOpenSearch]
    for name in dir(async_client_module):
        obj = getattr(async_client_module, name)
        if inspect.isclass(obj) and issubclass(obj, NamespacedClient) and obj is not NamespacedClient:
            classes.append(obj)
    return classes


@pytest.mark.parametrize("client_class", _all_async_client_classes(), ids=lambda c: c.__name__)
def test_async_instrumented_methods(client_class):
    _test_methods_wrapped(client_class)
