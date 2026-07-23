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

import time
from unittest.mock import MagicMock, patch

from newrelic.hooks.messagebroker_kafkapython import (
    _bootstrap_cache_key,
    _fetch_cluster_id_kafka_python,
    _kafka_cluster_id_cache,
    wrap_KafkaProducer_send,
)


# ---------------------------------------------------------------------------
# PY-1 regression: wrap_KafkaProducer_send must not overwrite the Kafka
# message routing key with the broker address string.
# ---------------------------------------------------------------------------

class TestProducerSendKeyPreservation:
    """The Kafka message routing key must survive the wrap_KafkaProducer_send
    instrumentation unchanged, regardless of whether cluster ID is cached."""

    def _make_producer_instance(self, bootstrap_servers=None):
        instance = MagicMock()
        instance.config = {
            "bootstrap_servers": bootstrap_servers or ["broker1:9092", "broker2:9092"],
        }
        return instance

    def _bind_send_args(self, topic, value=None, key=None, headers=None):
        """Return positional args as wrap_KafkaProducer_send receives them."""
        return (topic,), {"value": value, "key": key, "headers": headers or []}

    def test_message_key_not_overwritten_with_cluster_id_in_cache(self):
        """Key must not be replaced by broker address string when cluster ID cached."""
        cluster_id = "test-cluster-uuid"
        cache_key = "broker1:9092,broker2:9092"
        _kafka_cluster_id_cache[cache_key] = (cluster_id, time.monotonic())

        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance()
        args, kwargs = self._bind_send_args("my-topic", value=b"v", key=b"original-key")

        try:
            with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
                mock_txn.return_value = MagicMock()  # active transaction
                wrap_KafkaProducer_send(wrapped, instance, args, kwargs)
        finally:
            _kafka_cluster_id_cache.pop(cache_key, None)

        # The wrapped callable must have been called with key=b"original-key",
        # not key="broker1:9092,broker2:9092" or any other broker-derived string.
        assert wrapped.called, "wrapped() was never called"
        call_kwargs = wrapped.call_args[1]
        assert call_kwargs["key"] == b"original-key", (
            f"Message key was corrupted: got {call_kwargs['key']!r}, "
            f"expected b'original-key'. Likely cause: cache lookup variable "
            f"reused the name 'key', overwriting the Kafka routing key."
        )

    def test_message_key_not_overwritten_when_no_cluster_id_cached(self):
        """Key must not be replaced even when cluster ID is not yet in the cache."""
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance(bootstrap_servers=["broker-no-cache:9092"])
        args, kwargs = self._bind_send_args("topic", key="string-key-123")

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = MagicMock()
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        assert wrapped.called
        assert wrapped.call_args[1]["key"] == "string-key-123", (
            "Message key corrupted even when cluster ID was not in cache."
        )

    def test_none_key_preserved(self):
        """A None routing key must remain None (common case for unkeyed messages)."""
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance()
        args, kwargs = self._bind_send_args("topic", key=None)

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = MagicMock()
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        assert wrapped.call_args[1]["key"] is None, "None key was corrupted."

    def test_no_transaction_bypasses_instrumentation(self):
        """Without an active NR transaction, wrapped() is called with original args."""
        wrapped = MagicMock(return_value=MagicMock())
        instance = self._make_producer_instance()
        args = ("topic",)
        kwargs = {"value": b"v", "key": b"my-key"}

        with patch("newrelic.hooks.messagebroker_kafkapython.current_transaction") as mock_txn:
            mock_txn.return_value = None  # no active transaction
            wrap_KafkaProducer_send(wrapped, instance, args, kwargs)

        # wrapped() called directly with original args — no instrumentation applied
        assert wrapped.called
        wrapped.assert_called_once_with(*args, **kwargs)


# ---------------------------------------------------------------------------
# Cluster ID is fetched via KafkaAdminClient.describe_cluster() in a
# background daemon thread — no passive MetadataResponse interception.
# ---------------------------------------------------------------------------

class TestFetchClusterIdKafkaPython:
    """_fetch_cluster_id_kafka_python populates the cache via KafkaAdminClient."""

    def _cache_key(self, servers):
        return _bootstrap_cache_key(servers)

    def test_cluster_id_written_to_cache_on_success(self):
        """A successful describe_cluster() stores the cluster UUID in the module cache."""
        servers = ["broker-fetch1:9092"]
        cache_key = self._cache_key(servers)
        _kafka_cluster_id_cache.pop(cache_key, None)

        mock_admin = MagicMock()
        mock_admin.describe_cluster.return_value = {"cluster_id": "fetched-uuid", "brokers": []}

        with patch("kafka.admin.KafkaAdminClient", return_value=mock_admin):
            _fetch_cluster_id_kafka_python(servers)
            # Allow the daemon thread to finish
            time.sleep(0.5)

        try:
            cached = _kafka_cluster_id_cache.get(cache_key)
            assert isinstance(cached, tuple)
            assert cached[0] == "fetched-uuid"
        finally:
            _kafka_cluster_id_cache.pop(cache_key, None)

    def test_sentinel_prevents_duplicate_fetches(self):
        """While a fetch is in-flight (sentinel ''), a second call does not spawn a thread."""
        servers = ["broker-sentinel:9092"]
        cache_key = self._cache_key(servers)
        _kafka_cluster_id_cache[cache_key] = ""  # pre-set sentinel

        with patch("newrelic.hooks.messagebroker_kafkapython.threading.Thread") as mock_thread:
            _fetch_cluster_id_kafka_python(servers)
            mock_thread.assert_not_called()

        _kafka_cluster_id_cache.pop(cache_key, None)

    def test_existing_resolved_entry_not_refetched(self):
        """A fully-resolved cache entry (non-empty) skips the fetch and returns immediately."""
        servers = ["broker-resolved:9092"]
        cache_key = self._cache_key(servers)
        _kafka_cluster_id_cache[cache_key] = ("already-resolved-uuid", time.monotonic())

        with patch("newrelic.hooks.messagebroker_kafkapython.threading.Thread") as mock_thread:
            _fetch_cluster_id_kafka_python(servers)
            mock_thread.assert_not_called()

        _kafka_cluster_id_cache.pop(cache_key, None)

    def test_sentinel_removed_on_failure(self):
        """If KafkaAdminClient raises, the sentinel is removed so future instances can retry."""
        servers = ["broker-fail:9092"]
        cache_key = self._cache_key(servers)
        _kafka_cluster_id_cache.pop(cache_key, None)

        # Raise at construction time — this hits the outer except in _run() which
        # removes the sentinel. Raising only on connect() wouldn't work because
        # MagicMock.describe_cluster() auto-creates a truthy return value, causing
        # the cache to be populated with a MagicMock instead of being cleared.
        with patch("kafka.admin.KafkaAdminClient", side_effect=Exception("connection refused")):
            _fetch_cluster_id_kafka_python(servers)
            time.sleep(0.3)

        assert _kafka_cluster_id_cache.get(cache_key) is None
