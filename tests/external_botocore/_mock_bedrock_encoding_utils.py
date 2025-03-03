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
"""Utilities for encoding and decoding streaming payloads from Bedrock."""

import base64
import binascii
import json


def crc(b):
    """Encode the crc32 of the bytes stream into a 4 byte sequence."""
    return int_to_escaped_bytes(binascii.crc32(b), 4)


def int_to_escaped_bytes(i, num_bytes=1):
    """Convert an integer into an arbitrary number of bytes."""
    return bytes.fromhex(f"{{:0{str(num_bytes * 2)}x}}".format(i))


def encode_headers(headers):
    """Encode a dictionary of headers into bedrock's binary format."""
    new_headers = []
    for h, v in headers.items():
        if not h.startswith(":"):
            h = f":{h}"
        h = h.encode("utf-8")
        v = v.encode("utf-8")
        new_headers.append(b"".join((int_to_escaped_bytes(len(h)), h, b"\x07\x00", int_to_escaped_bytes(len(v)), v)))
    return b"".join(new_headers)


def decode_body(body):
    """Decode the mixed JSON and base64 encoded body of a streaming response into a dictionary."""
    body = body.decode("utf-8")
    body = json.loads(body)
    body = body["bytes"]
    body = base64.b64decode(body)
    body = body.decode("utf-8")
    return json.loads(body)


def encode_body(body, malformed_body=False):
    """Encode a dictionary body into JSON, base64, then JSON again under a bytes key."""

    body = json.dumps(body, separators=(",", ":"))
    if malformed_body:
        # Remove characters from end of body to make it unreadable
        body = body[:-4]

    body = body.encode("utf-8")
    body = base64.b64encode(body)
    body = body.decode("utf-8")
    body = {"bytes": body}
    body = json.dumps(body, separators=(",", ":"))
    body = body.encode("utf-8")
    return body


def encode_streaming_payload(headers, body, malformed_body=False):
    """Encode dictionary headers and dictionary body into bedrock's binary payload format including calculated lengths and CRC32."""
    headers = encode_headers(headers)
    body = encode_body(body, malformed_body=malformed_body)

    header_length = len(headers)
    payload_length = len(body)
    total_length = 16 + payload_length + header_length

    prelude = int_to_escaped_bytes(total_length, 4) + int_to_escaped_bytes(header_length, 4)
    prelude_crc = crc(prelude)

    payload = prelude + prelude_crc + headers + body
    payload_crc = crc(payload)

    return payload + payload_crc
