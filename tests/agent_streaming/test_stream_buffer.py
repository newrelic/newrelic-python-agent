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

from newrelic.common.streaming_utils import StreamBuffer

from newrelic.core.infinite_tracing_pb2 import Span, SpanBatch

from conftest import CONDITION_CLS


class StopIterationOnWait(CONDITION_CLS):
    def wait(self, *args, **kwargs):
        raise StopIteration()

@staticmethod
def stop_iteration_condition(*args, **kwargs):
    return StopIterationOnWait(*args, **kwargs)


def test_stream_buffer_iterator_batching(monkeypatch, batching):
    monkeypatch.setattr(StreamBuffer, "condition", stop_iteration_condition)

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


def test_stream_buffer_queue_size():
    stream_buffer = StreamBuffer(1)

    for _ in range(2):
        span = Span(intrinsics={}, agent_attributes={}, user_attributes={})
        stream_buffer.put(span)

    assert len(stream_buffer) == 1
    assert stream_buffer._dropped == 1
    assert stream_buffer._seen == 2
