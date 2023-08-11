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

from newrelic.api.background_task import background_task
from newrelic.api.transaction import set_transaction_name, set_background_task

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


# test
@validate_transaction_metrics(
        'test_transaction_name:test_transaction_name_default_bt',
        group='Function', background_task=True)
@background_task()
def test_transaction_name_default_bt():
    pass


@validate_transaction_metrics(
        'test_transaction_name:test_transaction_name_default_wt',
        group='Function', background_task=False)
@background_task()
def test_transaction_name_default_wt():
    set_background_task(False)


@validate_transaction_metrics('Transaction', group='Custom',
        background_task=True)
@background_task()
def test_transaction_name_valid_override_bt():
    set_transaction_name('Transaction', group='Custom')


@validate_transaction_metrics('Transaction', group='Function',
        background_task=True)
@background_task()
def test_transaction_name_empty_group_bt():
    set_transaction_name('Transaction', group='')


@validate_transaction_metrics('Transaction', group='Function/Group',
        background_task=True)
@background_task()
def test_transaction_name_leading_slash_on_group_bt():
    set_transaction_name('Transaction', group='/Group')
