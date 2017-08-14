from concurrent import futures
import grpc
import threading


# This defines an external grpc server test apps can use for testing.
#
# Example:
#
#   with MockExternalgRPCServer(port=PORT) as server:
#       add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
#               server)
#       ... test stuff ...
#
# The server runs on a separate thread meaning it won't block the test app.


class MockExternalgRPCServer(threading.Thread):

    def __init__(self, port=50051, *args, **kwargs):
        super(MockExternalgRPCServer, self).__init__(*args, **kwargs)

        self.port = port
        self.daemon = True

        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self.server.add_insecure_port('[::]:%s' % self.port)

        self.shutdown_event = threading.Event()

    def __enter__(self):
        self.start()
        return self.server

    def __exit__(self, type, value, tb):
        self.stop()

    def run(self):
        self.server.start()
        self.shutdown_event.wait()

    def stop(self):
        self.server.stop(grace=0.1)
        self.shutdown_event.set()
        self.join()
