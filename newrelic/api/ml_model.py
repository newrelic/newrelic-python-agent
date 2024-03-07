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
import uuid
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


def record_llm_feedback_event(
    message_id, rating, conversation_id=None, request_id=None, category=None, message=None, metadata=None
):
    transaction = current_transaction()
    if not transaction:
        warnings.warn(
            "No message feedback events will be recorded. record_llm_feedback_event must be called within the "
            "scope of a transaction."
        )
        return

    feedback_message_id = str(uuid.uuid4())
    feedback_message_event = metadata.copy() if metadata else {}
    feedback_message_event.update(
        {
            "id": feedback_message_id,
            "message_id": message_id,
            "rating": rating,
            "conversation_id": conversation_id or "",
            "request_id": request_id or "",
            "category": category or "",
            "message": message or "",
            "ingest_source": "Python",
        }
    )

    transaction.record_custom_event("LlmFeedbackMessage", feedback_message_event)
