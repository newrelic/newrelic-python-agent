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
import re

from testing_support.mock_external_http_server import MockExternalHTTPServer

# This defines an external server test apps can make requests to instead of
# the real Bedrock backend. This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.

RESPONSES = {
    "amazon.titan-text-express-v1::Write me a blog about making strong business decisions as a leader.": [
        {"content-type": "application/json", "x-amzn-requestid": "754408e9-672c-43e9-a62f-25d51596be42"},
        {
            "inputTextTokenCount": 19,
            "results": [
                {
                    "tokenCount": 20,
                    "outputText": " Making strong business decisions as a leader requires a combination of strategic thinking, careful analysis, and insight into",
                    "completionReason": "LENGTH",
                }
            ],
        },
    ],
    "anthropic.claude-instant-v1::Human: Write me a blog about making strong business decisions as a leader.": [
        {"content-type": "application/json", "x-amzn-requestid": "754408e9-672c-43e9-a62f-25d51596be42"},
        {
            "completion": " Here is a draft blog post on making strong business decisions as a leader:\n\nTitle: 5 Tips for Making Strong Business Decisions as a Leader\n\nBeing a leader means that tough business decisions will inevitably land on your desk. How you handle those decisions can have a huge impact on your company's success. Here are some tips to help you make strong, informed choices that move your business in the right direction.\n\n1. Gather all relevant data. Don't make a call until you've examined the issue from every angle. Seek out useful metrics, get feedback from various stakeholders, and look at historical trends and precedents. The more data you have, the clearer the right path will become. \n\n2. Consider both short and long-term implications. While it's important to address immediate needs, don't lose sight of how a decision may impact the future. Will your choice simply solve today's problem or help build sustainable growth? Carefully weigh short-term gains against potential long-term consequences.\n\n3. Trust your instincts but don't decide alone. Your gut feelings are valuable, but they shouldn't be the sole basis for a leadership decision. Consult with your management team and get differing perspectives. Encourage respectful debate to surface any risks or uncertainties that need discussion. \n\n4. Be willing todelaya decisionif youneed moretime.There'snobenefittomakingarushjudgement beforeallfactorshavebeenweighed.It'sbettertoletyourdecision\"bake\"athirdopinionormoredataratherthanpotentiallyregrettingahastycalllater.\n\n5. Follow through on the outcome. A good decision means little without effective implementation. Clearly communicate the rationale for your choice and gain organizational buy-in. Then follow up to ensure your solution is executed properly and intended goals are achieved. Are any adjustments needed along the way? \n\nLeaders are entrusted to make the calls that steer a business. With care, research and an open yet discerning approach, you can make decisions that propel your company confidently into the future.",
            "stop_reason": "stop_sequence",
        },
    ],
}

MODEL_PATH_RE = re.compile(r"/model/([^/]+)/invoke")


def simple_get(self):
    content_len = int(self.headers.get("content-length"))
    content = json.loads(self.rfile.read(content_len).decode("utf-8"))

    model = MODEL_PATH_RE.match(self.path).group(1)
    prompt = extract_shortened_prompt(content, model)
    if not prompt:
        self.send_response(500)
        self.end_headers()
        self.wfile.write("Could not parse prompt.".encode("utf-8"))
        return

    headers, response = ({}, "")
    for k, v in RESPONSES.items():
        if prompt.startswith(k):
            headers, response = v
            break
    else:  # If no matches found
        self.send_response(500)
        self.end_headers()
        self.wfile.write(("Unknown Prompt:\n%s" % prompt).encode("utf-8"))
        return

    # Send response code
    self.send_response(200)

    # Send headers
    for k, v in headers.items():
        self.send_header(k, v)
    self.end_headers()

    # Send response body
    self.wfile.write(json.dumps(response).encode("utf-8"))
    return


def extract_shortened_prompt(content, model):
    prompt = content.get("inputText", None) or content.get("prompt", None)
    prompt = "::".join((model, prompt))  # Prepend model name to prompt key to keep separate copies
    return prompt.lstrip().split("\n")[0]


class MockExternalBedrockServer(MockExternalHTTPServer):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls.

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super(MockExternalBedrockServer, self).__init__(handler=handler, port=port, *args, **kwargs)


if __name__ == "__main__":
    with MockExternalBedrockServer() as server:
        print("MockExternalBedrockServer serving on port %s" % str(server.port))
        while True:
            pass  # Serve forever
