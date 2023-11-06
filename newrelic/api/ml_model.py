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

import sys
import warnings

from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.hooks.mlmodel_sklearn import _nr_instrument_model


def wrap_mlmodel(model, name=None, version=None, feature_names=None, label_names=None, metadata=None):
    model_callable_name = callable_name(model)
    _class = model.__class__.__name__
    module = sys.modules[model_callable_name.split(":")[0]]
    _nr_instrument_model(module, _class)
    if name:
        model._nr_wrapped_name = name
    if version:
        model._nr_wrapped_version = version
    if feature_names:
        model._nr_wrapped_feature_names = feature_names
    if label_names:
        model._nr_wrapped_label_names = label_names
    if metadata:
        model._nr_wrapped_metadata = metadata


def get_ai_message_ids(response_id=None):
    transaction = current_transaction()
    # Open AI or Bedrock with response_id:
    if response_id and transaction:
        nr_message_ids = getattr(transaction, "_nr_message_ids", {})
        message_id_info = nr_message_ids.pop(response_id, ())

        if not message_id_info:
            warnings.warn("No message ids found for %s" % response_id)
            return []

        conversation_id, request_id, ids = message_id_info

        return [{"conversation_id": conversation_id, "request_id": request_id, "message_id": _id} for _id in ids]
    # Bedrock with no response_id:
    elif transaction:
        nr_message_ids = getattr(transaction, "_nr_message_ids", {})
        message_id_info = nr_message_ids.pop("bedrock_key", ())  # dict not necessary but will use to remain consistent

        if not message_id_info:
            warnings.warn("No message ids found.")
            return []

        conversation_id, ids = message_id_info

        return [{"conversation_id": conversation_id, "message_id": _id} for _id in ids]
    warnings.warn("No message ids found. get_ai_message_ids must be called within the scope of a transaction.")
    return []
