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

"""Unit tests for cluster-ID additions in messagebroker_kafkapython.

These tests exercise the wrapper functions directly with mocks — no real Kafka
broker required. They verify correctness of arguments passed to the underlying
`wrapped` callable without any network I/O.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from newrelic.core.config import global_settings
from newrelic.hooks.messagebroker_kafkapython import _read_cluster_id, wrap_KafkaProducer_send


def _enable_cluster_metrics(monkeypatch):
    settings = global_settings()
    monkeypatch.setattr(settings.kafka, "cluster_metrics_enabled", True)


# ---------------------------------------------------------------------------
# PY-1 regression: wrap_KafkaProducer_send must not overwrite the Kafka
# message routing key with the broker address string.
# ---------------------------------------------------------------------------

class TestProducerSendKeyPreservation:
    """The Kafka message routing key must survive the wrap_KafkaProducer_send
    instrumentation unchanged, regardless of whether a cluster ID is resolved."""

    def _make_producer_instance(self, bootstrap_servers=None, cluster_id=None):
        instance = MagicMock()
        instance.config = {
            "bootstrap_servers": bootstrap_servers or ["broker1:9092", "broker2:9092"],
        }
        instance._metadata = SimpleNamespace(cluster_id=cluster_id)
        return instance

    def _bind_send_args(self, topic, value=None, key=None, headers=None):
        """Return positional args as wrap_KafkaProducer_send receives them."""
        return (topic,), {"value": value, "key": key, "headers": headers or []}

    def test_message_key_not_overwritten_with_cluster_id_resolved(self, monkeypatch):
        """Key must not be replaced by broker address string when a cluster ID is resolved."""
        _enable_cluster_metrics(monkeypatch)
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance(cluster_id="test-cluster-uuid")
        args, kwargs = self._bind_send_args("my-topic", value=b"v", key=b"original-key")

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = MagicMock()  # active transaction
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        # The wrapped callable must have been called with key=b"original-key",
        # not key="broker1:9092,broker2:9092" or any other broker-derived string.
        assert wrapped.called, "wrapped() was never called"
        call_kwargs = wrapped.call_args[1]
        assert call_kwargs["key"] == b"original-key", (
            f"Message key was corrupted: got {call_kwargs['key']!r}, expected b'original-key'."
        )

    def test_message_key_not_overwritten_when_no_cluster_id_resolved(self, monkeypatch):
        """Key must not be replaced even when no cluster ID is resolved."""
        _enable_cluster_metrics(monkeypatch)
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance(bootstrap_servers=["broker-no-cluster:9092"], cluster_id=None)
        args, kwargs = self._bind_send_args("topic", key="string-key-123")

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = MagicMock()
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        assert wrapped.called
        assert wrapped.call_args[1]["key"] == "string-key-123", (
            "Message key corrupted even when no cluster ID was resolved."
        )

    def test_none_key_preserved(self, monkeypatch):
        """A None routing key must remain None (common case for unkeyed messages)."""
        _enable_cluster_metrics(monkeypatch)
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance(cluster_id="test-cluster-uuid")
        args, kwargs = self._bind_send_args("topic", key=None)

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = MagicMock()
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        assert wrapped.call_args[1]["key"] is None, "None key was corrupted."

    def test_no_transaction_bypasses_instrumentation(self, monkeypatch):
        """Without an active NR transaction, wrapped() is called with original args."""
        _enable_cluster_metrics(monkeypatch)
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance(cluster_id="test-cluster-uuid")
        args = ("topic",)
        kwargs = {"value": b"v", "key": b"my-key"}

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = None  # no active transaction
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        # wrapped() called directly with original args — no instrumentation applied
        assert wrapped.called
        wrapped.assert_called_once_with(*args, **kwargs)


# ---------------------------------------------------------------------------
# Cluster ID is a passive, synchronous read off kafka-python's own
# ClusterMetadata object — no AdminClient, no background thread, no cache.
# ---------------------------------------------------------------------------

class TestReadClusterId:
    def test_returns_none_when_cluster_metrics_disabled(self):
        instance = MagicMock()
        instance._metadata = SimpleNamespace(cluster_id="some-id")
        assert _read_cluster_id(instance) is None

    def test_reads_from_producer_metadata_attribute(self, monkeypatch):
        _enable_cluster_metrics(monkeypatch)
        instance = MagicMock(spec=["_metadata"])
        instance._metadata = SimpleNamespace(cluster_id="producer-cluster-id")
        assert _read_cluster_id(instance) == "producer-cluster-id"

    def test_reads_from_consumer_client_cluster_attribute(self, monkeypatch):
        _enable_cluster_metrics(monkeypatch)
        instance = MagicMock(spec=["_client"])
        instance._client = SimpleNamespace(cluster=SimpleNamespace(cluster_id="consumer-cluster-id"))
        assert _read_cluster_id(instance) == "consumer-cluster-id"

    def test_returns_none_when_metadata_not_yet_populated(self, monkeypatch):
        _enable_cluster_metrics(monkeypatch)
        instance = MagicMock(spec=["_metadata"])
        instance._metadata = SimpleNamespace(cluster_id=None)
        assert _read_cluster_id(instance) is None

    def test_returns_none_when_no_metadata_or_client_attribute(self, monkeypatch):
        _enable_cluster_metrics(monkeypatch)
        instance = MagicMock(spec=[])
        assert _read_cluster_id(instance) is None
