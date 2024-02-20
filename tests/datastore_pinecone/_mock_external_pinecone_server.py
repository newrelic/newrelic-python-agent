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

import pytest
from testing_support.mock_external_http_server import MockExternalHTTPServer

RESPONSES = {
    "('CreateIndexRequest', \"{'dimension': 4,\\n 'metric': 'cosine',\\n 'name': 'py\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {
            "name": "python-test",
            "dimension": 4,
            "metric": "cosine",
            "spec": {
                "pod": {"environment": "us-east-1-aws", "replicas": 1, "shards": 1, "pod_type": "p1.x1", "pods": 1}
            },
            "status": {"ready": False, "state": "Initializing"},
            "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
        },
    ],
    "('UpsertRequest', \"{'namespace': 'python-namespace',\\n 'vectors': [{'i\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {"upserted_count": 1},
    ],
    "('QueryRequest', \"{'namespace': 'python-namespace', 'top_k': 1, 'vec\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {"results": [], "matches": [{"id": "id-1", "score": 1.0, "values": []}], "namespace": "python-namespace"},
    ],
    "('UpdateRequest', \"{'id': 'id-1', 'namespace': 'python-namespace', 'v\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        "{}",
    ],
    "('DescribeIndexStatsRequest', \"{'ids': ['id-1'], 'namespace': 'python-namespace'}\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {
            "namespaces": {"python-namespace": {"vector_count": 1}},
            "dimension": 4,
            "index_fullness": 0.0,
            "total_vector_count": 1,
        },
    ],
    "('CreateCollectionRequest', \"{'name': 'python-collection', 'source': 'python-te\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {"name": "python-collection", "status": "Initializing", "environment": "us-east-1-aws", "dimension": 4},
    ],
    "('ConfigureIndexRequest', \"{'spec': {'pod': {'pod_type': 'p1.x2'}}}\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        {
            "name": "python-test",
            "dimension": 4,
            "metric": "cosine",
            "spec": {
                "pod": {"environment": "us-east-1-aws", "replicas": 1, "shards": 1, "pod_type": "p1.x2", "pods": 1}
            },
            "status": {"ready": True, "state": "Ready"},
            "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
        },
    ],
    "('DeleteRequest', \"{'ids': 'python-test'}\")": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.0.3 (urllib3:2.2.0)",
        },
        "{}",
    ],
}


# TODO: rewrite for Pinecone
@pytest.fixture(scope="session")
def simple_get(extract_shortened_prompt):
    def _simple_get(self):
        content_len = int(self.headers.get("content-length"))
        content = json.loads(self.rfile.read(content_len).decode("utf-8"))

        prompt = extract_shortened_prompt(content)
        if not prompt:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("Could not parse prompt.".encode("utf-8"))
            return

        headers, response = ({}, "")

        mocked_responses = RESPONSES

        for k, v in mocked_responses.items():
            if prompt.startswith(k):
                headers, response = v
                break
        else:  # If no matches found
            self.send_response(500)
            self.end_headers()
            self.wfile.write(("Unknown Prompt:\n%s" % prompt).encode("utf-8"))
            return

        # # Send response code
        # self.send_response(status_code)

        # Send headers
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        # Send response body
        self.wfile.write(json.dumps(response).encode("utf-8"))
        return

    return _simple_get


@pytest.fixture(scope="session")
def MockExternalPineconeServer(simple_get):
    class _MockExternalPineconeServer(MockExternalHTTPServer):
        # To use this class in a test one needs to start and stop this server
        # before and after making requests to the test app that makes the external
        # calls.

        def __init__(self, handler=simple_get, port=None, *args, **kwargs):
            super(_MockExternalPineconeServer, self).__init__(handler=handler, port=port, *args, **kwargs)

    return _MockExternalPineconeServer


@pytest.fixture(scope="session")
def extract_shortened_prompt():
    def _extract_shortened_prompt(content):
        request_type = type(content).__name__
        shortened_request = content.to_str()[:50]

        return str((request_type, shortened_request))

    return _extract_shortened_prompt


if __name__ == "__main__":
    # _ = MockExternalPineconeServer()
    with MockExternalPineconeServer():
        print("MockExternalPineconeServer serving")
        while True:
            pass  # Serve forever
