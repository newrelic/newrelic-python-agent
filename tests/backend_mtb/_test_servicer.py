from newrelic.core.mtb_pb2 import RecordStatus
from newrelic.core.mtb_pb2_grpc import IngestServiceServicer


class Servicer(IngestServiceServicer):
    def RecordSpan(self, spans, context):
        count = 0
        for span in spans:
            count += 1
            yield RecordStatus(messages_seen=count)
