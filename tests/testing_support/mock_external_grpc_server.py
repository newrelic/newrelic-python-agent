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

from concurrent import futures
import grpc
import socket


# This defines an external grpc server test apps can use for testing.
#
# Example:
#
#   with MockExternalgRPCServer(port=PORT) as server:
#       add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
#               server)
#       ... test stuff ...


class MockExternalgRPCServer(object):
    def __init__(self, port=None, *args, **kwargs):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        if port:
            self.server.port = self.server.add_insecure_port('127.0.0.1:%s' % port)
            self.port = port
        else:
            # If port not set, try to bind to a port until successful
            retries = 5  # Set retry limit to prevent infinite loops
            self.port = None  # Initialize empty
            while not self.port and retries > 0:
                retries -= 1
                try:
                    # Obtain random open port
                    port = self.get_open_port()
                    # Attempt to bind to port
                    self.server.port = self.server.add_insecure_port('127.0.0.1:%s' % port)
                    self.port = port
                except OSError as exc:
                    # Reraise errors other than port already in use
                    if "Address already in use" not in exc:
                        raise

    @staticmethod
    def get_open_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def __enter__(self):
        self.server.start()
        return self.server

    def __exit__(self, type, value, tb):
        # Set grace period to None so that the server shuts down immediately
        # when the context manager exits. This will hopefully prevent tests
        # from hanging while waiting for the server to shut down.
        # https://github.com/grpc/grpc/blob/662ec97674dd0918f4db4c21f5f47038c535a9ba/src/python/grpcio/grpc/_server.py#L729
        self.server.stop(grace=None)
