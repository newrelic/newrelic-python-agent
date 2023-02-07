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
from conftest import CONDITION_CLS

from newrelic.common.streaming_utils import StreamBuffer, StreamBufferIterator
from newrelic.core.infinite_tracing_pb2 import Span, SpanBatch


class StopIterationOnWait(CONDITION_CLS):
    def wait(self, *args, **kwargs):
        raise StopIteration()


@staticmethod
def stop_iteration_condition(*args, **kwargs):
    return StopIterationOnWait(*args, **kwargs)


@pytest.fixture(scope="function")
def stop_iteration_on_wait(monkeypatch):
    monkeypatch.setattr(StreamBuffer, "condition", stop_iteration_condition)


def test_stream_buffer_iterator_batching(stop_iteration_on_wait, batching):
    stream_buffer = StreamBuffer(5, batching=batching)

    for _ in range(5):
        span = Span(intrinsics={}, agent_attributes={}, user_attributes={})
        stream_buffer.put(span)

    buffer_contents = list(stream_buffer)
    if batching:
        assert len(buffer_contents) == 1
        assert isinstance(buffer_contents.pop(), SpanBatch)
    else:
        assert len(buffer_contents) == 5
        assert all(isinstance(element, Span) for element in stream_buffer)


def test_stream_buffer_iterator_max_batch_size(stop_iteration_on_wait):
    stream_buffer = StreamBuffer(StreamBufferIterator.MAX_BATCH_SIZE + 1, batching=True)

    # Add 1 more span than the maximum batch size
    for _ in range(StreamBufferIterator.MAX_BATCH_SIZE + 1):
        span = Span(intrinsics={}, agent_attributes={}, user_attributes={})
        stream_buffer.put(span)

    # Pull all span batches out of buffer
    buffer_contents = list(stream_buffer)
    assert len(buffer_contents) == 2

    # Large batch
    batch = buffer_contents.pop(0)
    assert isinstance(batch, SpanBatch)
    assert len(batch.spans) == StreamBufferIterator.MAX_BATCH_SIZE

    # Single span batch
    batch = buffer_contents.pop(0)
    assert isinstance(batch, SpanBatch)
    assert len(batch.spans) == 1


def test_stream_buffer_queue_size():
    stream_buffer = StreamBuffer(1)

    # Add more spans than queue can hold
    for _ in range(2):
        span = Span(intrinsics={}, agent_attributes={}, user_attributes={})
        stream_buffer.put(span)

    # Ensure spans are dropped and not stored
    assert len(stream_buffer) == 1
    assert stream_buffer._dropped == 1
    assert stream_buffer._seen == 2
