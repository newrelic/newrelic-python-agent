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
    "GET /indexes": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        {
            "indexes": [
                {
                    "name": "games",
                    "dimension": 1536,
                    "metric": "cosine",
                    "host": "games-0c55f2e.svc.us-east-1-aws.pinecone.io",
                    "spec": {
                        "pod": {
                            "environment": "us-east-1-aws",
                            "replicas": 1,
                            "shards": 1,
                            "pod_type": "s1.x1",
                            "pods": 1,
                            "source_collection": "",
                        }
                    },
                    "status": {"ready": True, "state": "Ready"},
                }
            ]
        },
    ],
    "POST /indexes": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {
            "name": "python-test",
            "dimension": 4,
            "metric": "cosine",
            "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
            "spec": {
                "pod": {"environment": "us-east-1-aws", "replicas": 1, "shards": 1, "pod_type": "p1.x1", "pods": 1}
            },
            "status": {"ready": True, "state": "Ready"},
        },
    ],
    "GET /indexes/{index_name}": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        {
            "name": "python-test",
            "dimension": 4,
            "metric": "cosine",
            "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
            "spec": {
                "pod": {"environment": "us-east-1-aws", "replicas": 1, "shards": 1, "pod_type": "p1.x1", "pods": 1}
            },
            "status": {"ready": True, "state": "Ready"},
        },
    ],
    "POST /vectors/upsert": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {"upserted_count": 1},
    ],
    "POST /query": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {"results": [], "matches": [{"id": "id-1", "score": 1.0, "values": []}], "namespace": "python-namespace"},
    ],
    "POST /vectors/update": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        "{}",
    ],
    "GET /vectors/fetch": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        {"vectors": {"id-1": {"id": "id-1", "values": [0.5, 0.6, 0.7, 0.8]}}, "namespace": "python-namespace"},
    ],
    "POST /describe_index_stats": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {
            "namespaces": {"python-namespace": {"vector_count": 1}},
            "dimension": 4,
            "index_fullness": 0.0,
            "total_vector_count": 1,
        },
    ],
    "POST /collections": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {"name": "python-collection", "status": "Initializing", "environment": "us-east-1-aws", "dimension": 4},
    ],
    "GET /collections": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        {"collections": [{"name": "python-collection", "status": "Initializing", "environment": "us-east-1-aws"}]},
    ],
    "GET /collections/{collection_name}": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        {
            "name": "python-collection",
            "status": "Ready",
            "environment": "us-east-1-aws",
            "size": 3080763,
            "vector_count": 1,
            "dimension": 4,
        },
    ],
    "DELETE /collections/{collection_name}": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        "",
    ],
    "PATCH /indexes/{index_name}": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        {
            "name": "python-test",
            "dimension": 4,
            "metric": "cosine",
            "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
            "spec": {
                "pod": {"environment": "us-east-1-aws", "replicas": 1, "shards": 1, "pod_type": "p1.x2", "pods": 1}
            },
            "status": {"ready": True, "state": "Ready"},
        },
    ],
    "POST /vectors/delete": [
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)",
        },
        "{}",
    ],
    "DELETE /indexes/{index_name}": [
        {"Accept": "application/json", "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"},
        "None",
    ],
}

# {
#     "IndexList:GET/indexes/{}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "indexes": [
#                 {
#                     "name": "games",
#                     "dimension": 1536,
#                     "metric": "cosine",
#                     "host": "games-0c55f2e.svc.us-east-1-aws.pinecone.io",
#                     "spec": {
#                         "pod": {
#                             "environment": "us-east-1-aws",
#                             "replicas": 1,
#                             "shards": 1,
#                             "pod_type": "s1.x1",
#                             "pods": 1,
#                             "source_collection": ""
#                         }
#                     },
#                     "status": {
#                         "ready": True,
#                         "state": "Ready"
#                     }
#                 }
#             ]
#         }
#     ],
#     "IndexModel:POST/indexes/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "name": "python-test",
#             "dimension": 4,
#             "metric": "cosine",
#             "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
#             "spec": {
#                 "pod": {
#                     "environment": "us-east-1-aws",
#                     "replicas": 1,
#                     "shards": 1,
#                     "pod_type": "p1.x1",
#                     "pods": 1
#                 }
#             },
#             "status": {
#                 "ready": False,
#                 "state": "Initializing"
#             }
#         }
#     ],
#     "IndexModel:GET/indexes/{index_name}/{'index_name': 'python-test'}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "name": "python-test",
#             "dimension": 4,
#             "metric": "cosine",
#             "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
#             "spec": {
#                 "pod": {
#                     "environment": "us-east-1-aws",
#                     "replicas": 1,
#                     "shards": 1,
#                     "pod_type": "p1.x1",
#                     "pods": 1
#                 }
#             },
#             "status": {
#                 "ready": True,
#                 "state": "Ready"
#             }
#         }
#     ],
#     "UpsertResponse:POST/vectors/upsert/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "upserted_count": 1
#         }
#     ],
#     "QueryResponse:POST/query/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "results": [],
#             "matches": [
#                 {
#                     "id": "id-1",
#                     "score": 1.0,
#                     "values": []
#                 }
#             ],
#             "namespace": "python-namespace"
#         }
#     ],
#     "None:POST/vectors/update/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         "{}"
#     ],
#     "FetchResponse:GET/vectors/fetch/{}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "vectors": {
#                 "id-1": {
#                     "id": "id-1",
#                     "values": [
#                         0.5,
#                         0.6,
#                         0.7,
#                         0.8
#                     ]
#                 }
#             },
#             "namespace": "python-namespace"
#         }
#     ],
#     "DescribeIndexStatsResponse:POST/describe_index_stats/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "namespaces": {
#                 "python-namespace": {
#                     "vector_count": 1
#                 }
#             },
#             "dimension": 4,
#             "index_fullness": 0.0,
#             "total_vector_count": 1
#         }
#     ],
#     "CollectionModel:POST/collections/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "name": "python-collection",
#             "status": "Initializing",
#             "environment": "us-east-1-aws",
#             "dimension": 4
#         }
#     ],
#     "CollectionList:GET/collections/{}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "collections": [
#                 {
#                     "name": "python-collection",
#                     "status": "Initializing",
#                     "environment": "us-east-1-aws"
#                 }
#             ]
#         }
#     ],
#     "CollectionModel:GET/collections/{collection_name}/{'collection_name': 'python-collection'}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "name": "python-collection",
#             "status": "Ready",
#             "environment": "us-east-1-aws",
#             "size": 3066961,
#             "vector_count": 1,
#             "dimension": 4
#         }
#     ],
#     "None:DELETE/collections/{collection_name}/{'collection_name': 'python-collection'}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         ""
#     ],
#     "IndexModel:PATCH/indexes/{index_name}/{'index_name': 'python-test'}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         {
#             "name": "python-test",
#             "dimension": 4,
#             "metric": "cosine",
#             "host": "python-test-0c55f2e.svc.us-east-1-aws.pinecone.io",
#             "spec": {
#                 "pod": {
#                     "environment": "us-east-1-aws",
#                     "replicas": 1,
#                     "shards": 1,
#                     "pod_type": "p1.x2",
#                     "pods": 1
#                 }
#             },
#             "status": {
#                 "ready": True,
#                 "state": "Ready"
#             }
#         }
#     ],
#     "None:POST/vectors/delete/{}": [
#         {
#             "Accept": "application/json",
#             "Content-Type": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         "{}"
#     ],
#     "None:DELETE/indexes/{index_name}/{'index_name': 'python-test'}": [
#         {
#             "Accept": "application/json",
#             "User-Agent": "python-client-3.1.0 (urllib3:2.2.1)"
#         },
#         "None"
#     ]
# }


@pytest.fixture(scope="session")
def simple_get(extract_shortened_prompt):
    def _simple_get(self):
        content = self.requestline

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

        # Send headers
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        # breakpoint()
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
        return content.replace(" HTTP/1.1", "")

    return _extract_shortened_prompt


if __name__ == "__main__":
    with MockExternalPineconeServer() as server:
        print("MockExternalPineconeServer serving port %d" % server.port)
        while True:
            pass  # Serve forever
