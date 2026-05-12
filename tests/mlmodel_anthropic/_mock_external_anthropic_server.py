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

import json

RESPONSES = {
    "How many letters are in the word Python?": [
        {"content-type": "application/json", "x-envoy-upstream-service-time": "1741"},
        200,
        {
            "id": "msg_bdrk_014ocTG8jdK3hU9F6oydApxE",
            "container": None,
            "content": [{"citations": None, "text": 'The word "Python" has 6 letters: P-y-t-h-o-n.', "type": "text"}],
            "model": "claude-sonnet-4-5-20250929",
            "role": "assistant",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "type": "message",
            "usage": {
                "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "inference_geo": None,
                "input_tokens": 16,
                "output_tokens": 26,
                "server_tool_use": None,
                "service_tier": None,
            },
        },
    ],
    "Who invented the Python programming language?": [
        {"content-type": "application/json", "x-envoy-upstream-service-time": "2306"},
        200,
        {
            "id": "msg_bdrk_011xHVWDrGwfs3TVEBJQHXuT",
            "container": None,
            "content": [
                {
                    "citations": None,
                    "text": "Guido van Rossum invented the Python programming language.",
                    "type": "text",
                }
            ],
            "model": "claude-sonnet-4-5-20250929",
            "role": "assistant",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "type": "message",
            "usage": {
                "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "inference_geo": None,
                "input_tokens": 14,
                "output_tokens": 76,
                "server_tool_use": None,
                "service_tier": None,
            },
        },
    ],
    "Invalid API key.": [
        {"content-type": "application/json", "x-envoy-upstream-service-time": "5"},
        400,
        {"error": {"message": "Unreadable token, please pass a valid token."}},
    ],
    "Model does not exist.": [
        {"content-type": "application/json", "x-envoy-upstream-service-time": "53"},
        422,
        {
            "error": {
                "message": "The given model doesn't exist in the requested endpoint",
                "code": 422,
                "model": "does-not-exist",
                "endpoint": "chat_completion",
            }
        },
    ],
}

STREAMED_RESPONSES = {
    "How many letters are in the word Python?": [
        {"content-type": "text/event-stream; charset=utf-8", "x-envoy-upstream-service-time": "70"},
        200,
        [
            'event: message_start\ndata: {"message": {"id": "msg_bdrk_014ocTG8jdK3hU9F6oydApxE", "container": null, "content": [], "model": "claude-sonnet-4-5-20250929", "role": "assistant", "stop_reason": null, "stop_sequence": null, "type": "message", "usage": {"cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "inference_geo": null, "input_tokens": 16, "output_tokens": 1, "server_tool_use": null, "service_tier": null}}, "type": "message_start"}\n\n',
            'event: content_block_start\ndata: {"content_block": {"citations": null, "text": "", "type": "text"}, "index": 0, "type": "content_block_start"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "The", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " word \\"Python\\" has 6 ", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "letters:", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " P-y", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "-t-h-o-n", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": ".", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_stop\ndata: {"index": 0, "type": "content_block_stop"}\n\n',
            'event: message_delta\ndata: {"delta": {"container": null, "stop_reason": "end_turn", "stop_sequence": null}, "type": "message_delta", "usage": {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "input_tokens": 16, "output_tokens": 26, "server_tool_use": null}}\n\n',
            'event: message_stop\ndata: {"type": "message_stop", "amazon-bedrock-invocationMetrics": {"inputTokenCount": 16, "outputTokenCount": 26, "invocationLatency": 1708, "firstByteLatency": 1405}}\n\n',
        ],
    ],
    "Who invented the Python programming language?": [
        {"content-type": "text/event-stream; charset=utf-8", "x-envoy-upstream-service-time": "68"},
        200,
        [
            'event: message_start\ndata: {"message": {"id": "msg_bdrk_0166tS73zjiCoHGKst81zoZX", "container": null, "content": [], "model": "claude-sonnet-4-5-20250929", "role": "assistant", "stop_reason": null, "stop_sequence": null, "type": "message", "usage": {"cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "inference_geo": null, "input_tokens": 14, "output_tokens": 9, "server_tool_use": null, "service_tier": null}}, "type": "message_start"}\n\nevent: content_block_start\ndata: {"content_block": {"citations": null, "text": "", "type": "text"}, "index": 0, "type": "content_block_start"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "Guido van Rossum invented the", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " Python programming language. He began", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " working", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " on Python in the late 1980", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "s,", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " and the first", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " version was released in 1991.", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " Van Rossum served", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " as Python", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\nevent: content_block_delta\ndata: {"delta": {"text": "\'s \\"", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": "Benevolent Dictator For", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " Life\\" (BDFL) until", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " he", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " stepped down from", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " that", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_delta\ndata: {"delta": {"text": " role in 2018.", "type": "text_delta"}, "index": 0, "type": "content_block_delta"}\n\n',
            'event: content_block_stop\ndata: {"index": 0, "type": "content_block_stop"}\n\n',
            'event: message_delta\ndata: {"delta": {"container": null, "stop_reason": "end_turn", "stop_sequence": null}, "type": "message_delta", "usage": {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "input_tokens": 14, "output_tokens": 76, "server_tool_use": null}}\n\n',
            'event: message_stop\ndata: {"type": "message_stop", "amazon-bedrock-invocationMetrics": {"inputTokenCount": 14, "outputTokenCount": 75, "invocationLatency": 2140, "firstByteLatency": 1360}}\n\n',
        ],
    ],
    "Invalid API key.": [
        {"content-type": "application/json", "x-envoy-upstream-service-time": "4"},
        400,
        ['{"error":{"message":"Unreadable token, please pass a valid token."}}'],
    ],
    "Model does not exist.": [
        {"content-type": "text/event-stream; charset=utf-8", "x-envoy-upstream-service-time": "32"},
        200,
        [
            'event: error\ndata: {"type": "error", "error": {"type": "api_error", "message": "The given model doesn\'t exist in the requested endpoint"}}\n\n'
        ],
    ],
}


def _extract_prompt(content):
    """Extract the first user message content string from a parsed request body."""
    messages = content.get("messages", [])
    for message in messages:
        msg_content = message.get("content", "")
        if isinstance(msg_content, str):
            return msg_content
        if isinstance(msg_content, list):
            for block in msg_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")
    return ""


def simple_get(self):
    content_len = int(self.headers.get("content-length", 0))
    content = json.loads(self.rfile.read(content_len).decode("utf-8")) if content_len else {}

    stream = content.get("stream", False)
    prompt = _extract_prompt(content)

    mocked_responses = STREAMED_RESPONSES if stream else RESPONSES

    headers, status_code, response_body = None, 500, {"error": "No matching response found"}
    for key, value in mocked_responses.items():
        if prompt.startswith(key):
            headers, status_code, response_body = value
            break

    self.send_response(status_code)
    if headers:
        for k, v in headers.items():
            self.send_header(k, v)
    self.end_headers()

    if stream and status_code < 400 and isinstance(response_body, list):
        for response_chunk in response_body:
            self.wfile.write(response_chunk.encode("utf-8"))  # No need for JSON, already a string
    else:
        self.wfile.write(json.dumps(response_body).encode("utf-8"))
