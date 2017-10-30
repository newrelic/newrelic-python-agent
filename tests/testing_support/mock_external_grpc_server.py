from concurrent import futures
import grpc


# This defines an external grpc server test apps can use for testing.
#
# Example:
#
#   with MockExternalgRPCServer(port=PORT) as server:
#       add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
#               server)
#       ... test stuff ...


class MockExternalgRPCServer(object):

    def __init__(self, port=50051, *args, **kwargs):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=50))
        self.server.port = self.server.add_insecure_port('[::]:%s' % port)

    def __enter__(self):
        self.server.start()
        return self.server

    def __exit__(self, type, value, tb):
        # Set grace period to None so that the server shuts down immediately
        # when the context manager exits. This will hopefully prevent tests
        # from hanging while waiting for the server to shut down.
        # https://github.com/grpc/grpc/blob/662ec97674dd0918f4db4c21f5f47038c535a9ba/src/python/grpcio/grpc/_server.py#L729
        self.server.stop(grace=None)
