import grpc
from newrelic.core.mtb_pb2 import Span, AttributeValue, RecordStatus

def test_send(mock_grpc_server):
    count = 5
    metadata = (('api_key', ''),)
    endpoint = 'localhost:%s' % mock_grpc_server
    channel = grpc.insecure_channel(endpoint)
    record_span = channel.stream_stream(
        "/com.newrelic.trace.v1.IngestService/RecordSpan",
        Span.SerializeToString,
        RecordStatus.FromString,
    )

    def spans():
        for _ in range(count):
            yield Span(
                trace_id="0",
                intrinsics={"key": AttributeValue(string_value='value')},
                user_attributes={"key": AttributeValue(string_value='value')},
                agent_attributes={"key": AttributeValue(string_value='value')},
            )
    res = record_span(spans(), metadata=metadata)
    result = list(res)
    assert result[-1].messages_seen == count
