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
import threading

try:
    import grpc
    from newrelic.core.infinite_tracing_pb2 import Span, RecordStatus
except ImportError:
    grpc = None

_logger = logging.getLogger(__name__)


class StreamingRpc(object):
    """Streaming Remote Procedure Call

    This class keeps a stream_stream RPC alive, retrying after a timeout when
    errors are encountered. If grpc.StatusCode.UNIMPLEMENTED is encountered, a
    retry will not occur.
    """

    PATH = "/com.newrelic.trace.v1.IngestService/RecordSpan"

    def __init__(self, endpoint, stream_buffer, metadata, record_metric, ssl=True):
        if ssl:
            credentials = grpc.ssl_channel_credentials()
            channel = grpc.secure_channel(endpoint, credentials)
        else:
            channel = grpc.insecure_channel(endpoint)
        self.channel = channel
        self.metadata = metadata
        self.request_iterator = stream_buffer
        self.response_processing_thread = threading.Thread(
            target=self.process_responses, name="NR-StreamingRpc-process-responses"
        )
        self.response_processing_thread.daemon = True
        self.notify = self.condition()
        self.rpc = self.channel.stream_stream(
            self.PATH, Span.SerializeToString, RecordStatus.FromString
        )
        self.record_metric = record_metric

    @staticmethod
    def condition(*args, **kwargs):
        return threading.Condition(*args, **kwargs)

    def close(self):
        channel = None
        with self.notify:
            if self.channel:
                channel = self.channel
                self.channel = None
            self.notify.notify_all()

        if channel:
            _logger.debug("Closing streaming rpc.")
            channel.close()
            try:
                self.response_processing_thread.join(timeout=5)
            except Exception:
                pass
            _logger.debug("Streaming rpc close completed.")

    def connect(self):
        self.response_processing_thread.start()

    def process_responses(self):
        response_iterator = None

        while True:
            with self.notify:
                if self.channel and response_iterator:
                    code = response_iterator.code()
                    details = response_iterator.details()

                    self.record_metric(
                        "Supportability/InfiniteTracing/Span/gRPC/%s" % code.name,
                        {"count": 1},
                    )

                    if code is grpc.StatusCode.OK:
                        _logger.debug(
                            "Streaming RPC received OK "
                            "response code. The agent will attempt "
                            "to reestablish the stream immediately."
                        )
                    else:
                        self.record_metric(
                            "Supportability/InfiniteTracing/Span/Response/Error",
                            {"count": 1},
                        )

                        if code is grpc.StatusCode.UNIMPLEMENTED:
                            _logger.error(
                                "Streaming RPC received "
                                "UNIMPLEMENTED response code. "
                                "The agent will not attempt to "
                                "reestablish the stream."
                            )
                            break

                        _logger.warning(
                            "Streaming RPC closed. "
                            "Will attempt to reconnect in 15 seconds. "
                            "Code: %s Details: %s",
                            code,
                            details,
                        )
                        self.notify.wait(15)

                if not self.channel:
                    break

                response_iterator = self.rpc(
                    self.request_iterator, metadata=self.metadata
                )
                _logger.info("Streaming RPC connect completed.")

            try:
                for response in response_iterator:
                    _logger.debug("Stream response: %s", response)
            except Exception:
                pass

        self.close()
        _logger.info("Process response thread ending.")
