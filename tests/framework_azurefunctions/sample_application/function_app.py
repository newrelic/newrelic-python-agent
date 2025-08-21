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

import azure.functions

app = azure.functions.FunctionApp(http_auth_level=azure.functions.AuthLevel.ANONYMOUS)


@app.function_name(name="HttpTriggerSync")
@app.route(route="sync")
def sync_func(req):
    user = req.params.get("user")
    if user.lower() != "reli":
        raise NotReliError

    response = azure.functions.HttpResponse(f"Hello, {user}!", status_code=200, headers={"Content-Type": "text/plain"})
    return response


@app.function_name(name="HttpTriggerAsync")
@app.route(route="async")
async def async_func(req):
    user = req.params.get("user")
    if user.lower() != "reli":
        raise NotReliError

    response = azure.functions.HttpResponse(f"Hello, {user}!", status_code=200, headers={"Content-Type": "text/plain"})
    return response


class NotReliError(RuntimeError):
    """Custom error to raise when the user is not Reli."""

    def __init__(self, message="This function is only for Reli!"):
        super().__init__(message)
