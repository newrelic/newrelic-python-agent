from newrelic.core.mtb_pb2 import Span, AttributeValue


def test_send(grpc_stub):
    count = 5
    metadata = (('api_key', ''),)

    def spans():
        for _ in range(count):
            yield Span(
                trace_id="0",
                intrinsics={"key": AttributeValue(string_value='value')},
                user_attributes={"key": AttributeValue(string_value='value')},
                agent_attributes={"key": AttributeValue(string_value='value')},
            )
    res = grpc_stub.RecordSpan(spans(), metadata=metadata)
    result = list(res)
    assert result[-1].messages_seen == count
