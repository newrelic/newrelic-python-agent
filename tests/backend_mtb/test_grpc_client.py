import grpc
from newrelic.core.mtb_pb2_grpc import IngestServiceStub
from newrelic.core.mtb_pb2 import Span, AttributeValue

def test_send(mock_grpc_server):
    count = 5
    metadata = (('api_key', ''),)
    endpoint = 'localhost:%s' % mock_grpc_server
    channel = grpc.insecure_channel(endpoint)
    client = IngestServiceStub(channel)
    def spans():
        for _ in range(count):
            yield Span(
                trace_id="0",
                intrinsics={"key": AttributeValue(string_value='value')},
                user_attributes={"key": AttributeValue(string_value='value')},
                agent_attributes={"key": AttributeValue(string_value='value')},
            )
    res = client.RecordSpan(spans(), metadata=metadata)
    result = list(res)
    assert result[-1].messages_seen == count
