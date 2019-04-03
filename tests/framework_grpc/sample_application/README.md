# Sample gRPC Application

Contained in this directory is a sample gRPC application that includes all four
end point types (unary unary, unary stream, stream unary, and stream stream)
both with and without exceptions raised.

The python code for the service is generated at run time as a command in the
tox.ini file. The generated python files are excluded from version control.
