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

import logging

import pytest
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.graphql_trace import GraphQLOperationTrace, GraphQLResolverTrace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace
from newrelic.api.transaction import current_transaction, end_of_transaction


@validate_transaction_metrics(
    "test_trace_after_end_of_transaction",
    background_task=True,
    scoped_metrics=[("Function/foobar", None)],
)
@background_task(name="test_trace_after_end_of_transaction")
def test_trace_after_end_of_transaction(caplog):
    end_of_transaction()
    with FunctionTrace("foobar"):
        pass

    error_messages = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert not error_messages


@pytest.mark.parametrize(
    "trace_type,args",
    (
        (DatabaseTrace, ("select * from foo",)),
        (DatastoreTrace, ("db_product", "db_target", "db_operation")),
        (ExternalTrace, ("lib", "url")),
        (FunctionTrace, ("name",)),
        (GraphQLOperationTrace, ()),
        (GraphQLResolverTrace, ()),
        (MemcacheTrace, ("command",)),
        (MessageTrace, ("lib", "operation", "dst_type", "dst_name")),
        (SolrTrace, ("lib", "command")),
    ),
)
@background_task()
def test_trace_finalizes_with_transaction_missing_settings(monkeypatch, trace_type, args):
    txn = current_transaction()
    try:
        with trace_type(*args):
            # Validate no errors are raised when finalizing trace with no settings
            monkeypatch.setattr(txn, "_settings", None)
    finally:
        # Ensure transaction still has settings when it exits to prevent other crashes making errors hard to read
        monkeypatch.undo()
        assert txn.settings
