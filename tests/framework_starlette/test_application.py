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

import starlette
import pytest
from testing_support.fixtures import (
    validate_transaction_metrics,
    validate_transaction_errors,
)


FRAMEWORK_METRIC = ("Python/Framework/Starlette/%s" % starlette.__version__, 1)


@validate_transaction_metrics(
    "_target_application:index", rollup_metrics=[FRAMEWORK_METRIC]
)
def test_application_index(target_application):
    response = target_application.get("/index")
    assert response.status == 200


@validate_transaction_metrics(
    "_target_application:non_async", rollup_metrics=[FRAMEWORK_METRIC]
)
def test_application_non_async(target_application):
    response = target_application.get("/non_async")
    assert response.status == 200


@validate_transaction_errors(errors=["builtins:RuntimeError"])
@validate_transaction_metrics(
    "_target_application:runtime_error", rollup_metrics=[FRAMEWORK_METRIC]
)
def test_application_generic_error(target_application):
    # When the generic exception handler is used, the error is reraised
    with pytest.raises(RuntimeError):
        target_application.get("/runtime_error")


@pytest.mark.xfail(
    reason="Handled errors aren't captured yet. See PYTHON-3730",
    strict=True,
)
@validate_transaction_errors(errors=["_target_application:HandledError"])
@validate_transaction_metrics(
    "_target_application:handled_error", rollup_metrics=[FRAMEWORK_METRIC]
)
def test_application_handled_error(target_application):
    response = target_application.get("/handled_error")
    assert response.status == 500
