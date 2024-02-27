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

# import os
# import pytest
# from pinecone import Pinecone, ServerlessSpec
# from pinecone import Pinecone, PodSpec

from time import sleep

from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version

PINECONE_VERSION = get_package_version("pinecone")

# Future instrumentation points: gRPC Pinecone


# count for describe_collection will be different based on
# whether mock server is enabled or not.
_scoped_metrics = [
    ("Datastore/operation/Pinecone/list_indexes", 1),
    ("Datastore/statement/Pinecone/python-test/describe_index", 1),
    ("Datastore/operation/Pinecone/upsert", 1),
    ("Datastore/operation/Pinecone/query", 1),
    ("Datastore/operation/Pinecone/update", 1),
    ("Datastore/operation/Pinecone/fetch", 1),
    ("Datastore/operation/Pinecone/describe_index_stats", 1),
    ("Datastore/statement/Pinecone/python-test/create_collection", 1),
    # ("Datastore/operation/Pinecone/describe_collection", 2),
    ("Datastore/operation/Pinecone/list_collections", 1),
    ("Datastore/operation/Pinecone/delete_collection", 1),
    ("Datastore/statement/Pinecone/python-test/configure_index", 1),
]
_rollup_metrics = [
    # ("Datastore/all", 13),
    # ("Datastore/Pinecone/all", 13),
    # ("Datastore/allOther", 13),
    # ("Datastore/Pinecone/allOther", 13),
    ("Datastore/operation/Pinecone/describe_index", 1),
    ("Datastore/operation/Pinecone/list_indexes", 1),
    ("Datastore/operation/Pinecone/upsert", 1),
    ("Datastore/operation/Pinecone/query", 1),
    ("Datastore/operation/Pinecone/update", 1),
    ("Datastore/operation/Pinecone/fetch", 1),
    ("Datastore/operation/Pinecone/describe_index_stats", 1),
    ("Datastore/operation/Pinecone/create_collection", 1),
    # ("Datastore/operation/Pinecone/describe_collection", 2), # 60+ in production
    ("Datastore/operation/Pinecone/list_collections", 1),
    ("Datastore/operation/Pinecone/delete_collection", 1),
    ("Datastore/operation/Pinecone/configure_index", 1),
]


@validate_transaction_metrics(
    "test_pinecone:test_suite_new",
    # scoped_metrics=_scoped_metrics,
    # rollup_metrics=_rollup_metrics,
    custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
    background_task=True,
)
@background_task()
def test_suite_new(pinecone_instance, pinecone_index_instance):
    for _ in pinecone_instance.list_indexes():
        pass

    index_status = pinecone_instance.describe_index("python-test")
    assert index_status["status"]["ready"]

    pinecone_index_instance.upsert(vectors=[("id-1", [0.1, 0.2, 0.3, 0.4])], namespace="python-namespace")

    match = pinecone_index_instance.query(top_k=1, vector=[0.1, 0.2, 0.3, 0.4], namespace="python-namespace")
    assert match["matches"][0]["id"] == "id-1"

    pinecone_index_instance.update(id="id-1", values=[0.5, 0.6, 0.7, 0.8], namespace="python-namespace")

    result = pinecone_index_instance.fetch(ids=["id-1"], namespace="python-namespace")
    assert result["vectors"]["id-1"]["values"] == [0.5, 0.6, 0.7, 0.8]

    result = pinecone_index_instance.describe_index_stats(ids=["id-1"], namespace="python-namespace")
    assert result

    pinecone_instance.create_collection("python-collection", "python-test")

    for _ in pinecone_instance.list_collections():
        pass

    while pinecone_instance.describe_collection("python-collection")["status"] != "Ready":
        sleep(1)

    pinecone_instance.delete_collection("python-collection")

    pinecone_instance.configure_index("python-test", pod_type="p1.x2")

    # Pause the test while deleting the collection.
    # This takes a little while
    # In mock server, we will only have describe_collection in "Ready"y
    # state so that this will be skipped (and effectively act as though
    # the collection was deleted quickly)
    try:
        while pinecone_instance.describe_collection("python-collection")["status"] == "Terminating":
            sleep(1)
    except Exception:
        # There is no collection anymore because it has finally been deleted.
        # We can allow the test to resume/end
        pass


def test_suite(pinecone_instance, pinecone_index_instance):

    _scoped_metrics_describe_index = [
        ("Datastore/statement/Pinecone/python-test/describe_index", 1),
    ]
    _rollup_metrics_describe_index = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/describe_index", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_describe_index",
        scoped_metrics=_scoped_metrics_describe_index,
        rollup_metrics=_rollup_metrics_describe_index,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_describe_index():
        return pinecone_instance.describe_index("python-test")

    _scoped_metrics_list_indexes = [
        ("Datastore/operation/Pinecone/list_indexes", 1),
    ]
    _rollup_metrics_list_indexes = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/list_indexes", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_list_indexes",
        scoped_metrics=_scoped_metrics_list_indexes,
        rollup_metrics=_rollup_metrics_list_indexes,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_list_indexes():
        flag = False
        for index in pinecone_instance.list_indexes():
            # AI team has a sample index called "games"
            # assert index.name in ["python-test", "games"]
            if index.name == "python-test":
                flag = True
        assert flag

    _scoped_metrics_upsert = [
        ("Datastore/operation/Pinecone/upsert", 1),
    ]
    _rollup_metrics_upsert = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/upsert", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_upsert",
        scoped_metrics=_scoped_metrics_upsert,
        rollup_metrics=_rollup_metrics_upsert,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_upsert():
        pinecone_index_instance.upsert(vectors=[("id-1", [0.1, 0.2, 0.3, 0.4])], namespace="python-namespace")

    _scoped_metrics_query = [
        ("Datastore/operation/Pinecone/query", 1),
    ]
    _rollup_metrics_query = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/query", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_query",
        scoped_metrics=_scoped_metrics_query,
        rollup_metrics=_rollup_metrics_query,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_query():
        match = pinecone_index_instance.query(top_k=1, vector=[0.1, 0.2, 0.3, 0.4], namespace="python-namespace")
        assert match["matches"][0]["id"] == "id-1"

    _scoped_metrics_update = [
        ("Datastore/operation/Pinecone/update", 1),
    ]
    _rollup_metrics_update = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/update", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_update",
        scoped_metrics=_scoped_metrics_update,
        rollup_metrics=_rollup_metrics_update,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_update():
        pinecone_index_instance.update(id="id-1", values=[0.5, 0.6, 0.7, 0.8], namespace="python-namespace")

    _scoped_metrics_fetch = [
        ("Datastore/operation/Pinecone/fetch", 1),
    ]
    _rollup_metrics_fetch = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/fetch", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_fetch",
        scoped_metrics=_scoped_metrics_fetch,
        rollup_metrics=_rollup_metrics_fetch,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_fetch():
        result = pinecone_index_instance.fetch(ids=["id-1"], namespace="python-namespace")
        assert result["vectors"]["id-1"]["values"] == [0.5, 0.6, 0.7, 0.8]

    _scoped_metrics_describe_index_stats = [
        ("Datastore/operation/Pinecone/describe_index_stats", 1),
    ]
    _rollup_metrics_describe_index_stats = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/describe_index_stats", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_describe_index_stats",
        scoped_metrics=_scoped_metrics_describe_index_stats,
        rollup_metrics=_rollup_metrics_describe_index_stats,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_describe_index_stats():
        result = pinecone_index_instance.describe_index_stats(ids=["id-1"], namespace="python-namespace")
        assert result

    _scoped_metrics_create_collection = [
        ("Datastore/statement/Pinecone/python-test/create_collection", 1),
    ]
    _rollup_metrics_create_collection = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/create_collection", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_create_collection",
        scoped_metrics=_scoped_metrics_create_collection,
        rollup_metrics=_rollup_metrics_create_collection,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_create_collection():
        pinecone_instance.create_collection("python-collection", "python-test")

    _scoped_metrics_describe_collection = [
        ("Datastore/operation/Pinecone/describe_collection", 1),
    ]
    _rollup_metrics_describe_collection = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/describe_collection", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_describe_collection",
        scoped_metrics=_scoped_metrics_describe_collection,
        rollup_metrics=_rollup_metrics_describe_collection,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_describe_collection():
        return pinecone_instance.describe_collection("python-collection")

    _scoped_metrics_list_collections = [
        ("Datastore/operation/Pinecone/list_collections", 1),
    ]
    _rollup_metrics_list_collections = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/list_collections", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_list_collections",
        scoped_metrics=_scoped_metrics_list_collections,
        rollup_metrics=_rollup_metrics_list_collections,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_list_collections():
        for collection_name in pinecone_instance.list_collections():
            assert collection_name["name"] == "python-collection"

    _scoped_metrics_delete_collection = [
        ("Datastore/operation/Pinecone/delete_collection", 1),
    ]
    _rollup_metrics_delete_collection = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/delete_collection", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_delete_collection",
        scoped_metrics=_scoped_metrics_delete_collection,
        rollup_metrics=_rollup_metrics_delete_collection,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_delete_collection():
        pinecone_instance.delete_collection("python-collection")

    _scoped_metrics_configure_index = [
        ("Datastore/statement/Pinecone/python-test/configure_index", 1),
    ]
    _rollup_metrics_configure_index = [
        ("Datastore/all", 1),
        ("Datastore/Pinecone/all", 1),
        ("Datastore/allOther", 1),
        ("Datastore/Pinecone/allOther", 1),
        ("Datastore/operation/Pinecone/configure_index", 1),
    ]

    @validate_transaction_metrics(
        "test_pinecone:test_suite.<locals>._test_configure_index",
        scoped_metrics=_scoped_metrics_configure_index,
        rollup_metrics=_rollup_metrics_configure_index,
        custom_metrics=[("Python/ML/Pinecone/%s" % PINECONE_VERSION, 1)],
        background_task=True,
    )
    @background_task()
    def _test_configure_index():
        pinecone_instance.configure_index("python-test", pod_type="p1.x2")

    ###################
    # Test suite

    index_info = _test_describe_index()

    # Pause the test while index is being initialized
    # This sometimes takes a while
    while not index_info["status"]["ready"]:
        sleep(1)
        index_info = pinecone_instance.describe_index("python-test")

    _test_list_indexes()
    _test_upsert()
    _test_query()
    _test_update()
    _test_fetch()
    _test_describe_index_stats()
    _test_create_collection()
    collection_info = _test_describe_collection()

    # Pause the test while collection is being created
    # This takes a little while
    while collection_info["status"] != "Ready":
        sleep(1)
        collection_info = pinecone_instance.describe_collection("python-collection")

    _test_list_collections()
    _test_delete_collection()

    # Pause the test while deleting the collection.
    # This takes a little while
    collection_termination_status = "Terminating"
    try:
        while collection_termination_status == "Terminating":
            sleep(1)
            collection_termination_status = pinecone_instance.describe_collection("python-collection")["status"]
    except Exception:
        # There is no collection anymore because it has finally been deleted.
        # We can allow the test to resume/end
        pass

    _test_configure_index()

    index_info = pinecone_instance.describe_index("python-test")
    assert index_info["spec"]["pod"]["pod_type"] == "p1.x2"
