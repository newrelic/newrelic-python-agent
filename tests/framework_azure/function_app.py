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

# import newrelic.agent
import azure.functions as func

# newrelic.agent.initialize() # Initialize the New Relic agent

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="HttpTriggerBasic")
@app.route(route="basic")
def basic_page(req):
    user = req.params.get("user")
    return func.HttpResponse(f"Hello, {user}!", status_code=200, headers={"Content-Type": "text/plain"})


# mock_http_request = func.HttpRequest(
#     method="GET",
#     url=f"http://127.0.0.1:{PORT}/basic",
#     body=None,
#     headers={"Content-Type": "text/plain"},
#     params={"user": "Reli"},
# )
