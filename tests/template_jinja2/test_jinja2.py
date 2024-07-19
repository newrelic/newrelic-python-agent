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

from jinja2 import Template
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task


@validate_transaction_metrics(
    "test_render",
    background_task=True,
    scoped_metrics=(
        ("Template/Render/<template>", 1),
        ("Template/Compile/<template>", 1),
    ),
)
@background_task(name="test_render")
def test_render():
    template_to_render = Template("hello, {{ name }}!")
    result = template_to_render.render(name="NR")
    assert result == "hello, NR!"


def test_render_outside_txn():
    template_to_render = Template("hello, {{ name }}!")
    result = template_to_render.render(name="NR")
    assert result == "hello, NR!"
