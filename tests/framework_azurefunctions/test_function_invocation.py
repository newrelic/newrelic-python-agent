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

from testing_support.fixtures import validate_attributes
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


def test_invocation(send_invocation, is_async):
    transaction_name = "HttpTriggerAsync" if is_async else "HttpTriggerSync"

    # Only the first invocation of the function will have the cold start attribute.
    sync_intrinsic_attributes = ["faas.name", "faas.trigger", "faas.invocation_id", "faas.coldStart"]
    async_intrinsic_attributes = ["faas.name", "faas.trigger", "faas.invocation_id"]
    sync_forgone_attributes = []
    async_forgone_attributes = ["faas.coldStart"]

    intrinsic_attributes = async_intrinsic_attributes if is_async else sync_intrinsic_attributes
    forgone_attributes = async_forgone_attributes if is_async else sync_forgone_attributes

    @validate_attributes("agent", intrinsic_attributes, forgone_attributes)
    @validate_transaction_metrics(group="AzureFunction", name=transaction_name)
    def _test_invocation():
        response = send_invocation()

        assert response.invocation_response.result.status == 1, "Function invocation failed."
        assert response.invocation_response.return_value.http.status_code == "200", (
            "Function returned non-200 status code."
        )
        assert response.invocation_response.return_value.http.body.bytes == b"Hello, Reli!", "Body is incorrect."

    _test_invocation()


def test_invocation_error(send_invocation, is_async):
    transaction_name = "HttpTriggerAsync" if is_async else "HttpTriggerSync"

    @validate_transaction_metrics(group="AzureFunction", name=transaction_name)
    @validate_transaction_errors(["function_app:NotReliError"])
    def _test_invocation():
        response = send_invocation(user="NotReli")

        assert response.invocation_response.result.status != 1, "Function failed to raise an error."
        assert response.invocation_response.result.exception.message == "NotReliError: This function is only for Reli!"

    _test_invocation()
