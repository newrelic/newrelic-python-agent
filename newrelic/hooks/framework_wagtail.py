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
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper


def _nr_wrapper_route_for_request(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    route_result = wrapped(*args, **kwargs)
    if route_result:
        page, args, kwargs = route_result
        name = callable_name(page.route)
        transaction.set_transaction_name(name, priority=6)

    return route_result


def instrument_wagtail_models_pages(module):
    if hasattr(module, "Page"):
        if hasattr(module.Page, "route_for_request"):
            wrap_function_wrapper(module, "Page.route_for_request", _nr_wrapper_route_for_request)
