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

import logging
import sys
import uuid
import warnings

from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.core.config import global_settings
from newrelic.hooks.mlmodel_sklearn import _nr_instrument_model

_logger = logging.getLogger(__name__)


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


def record_llm_feedback_event(trace_id, rating, category=None, message=None, metadata=None):
    transaction = current_transaction()
    if not transaction:
        warnings.warn(
            "No message feedback events will be recorded. record_llm_feedback_event must be called within the "
            "scope of a transaction.",
            stacklevel=2,
        )
        return

    feedback_event_id = str(uuid.uuid4())
    feedback_event = metadata.copy() if metadata else {}
    feedback_event.update(
        {
            "id": feedback_event_id,
            "trace_id": trace_id,
            "rating": rating,
            "category": category,
            "message": message,
            "ingest_source": "Python",
        }
    )

    transaction.record_custom_event("LlmFeedbackMessage", feedback_event)


def set_llm_token_count_callback(callback, application=None):
    """
    Set the current callback to be used to calculate LLM token counts.

    Arguments:
    callback -- the user-defined callback that will calculate and return the total token count as an integer or None if it does not know
    application -- optional application object to associate call with
    """
    if callback and not callable(callback):
        _logger.error(
            "callback passed to set_llm_token_count_callback must be a Callable type or None to unset the callback."
        )
        return

    from newrelic.api.application import application_instance

    # Check for activated application if it exists and was not given.
    application = application or application_instance(activate=False)

    # Get application settings if it exists, or fallback to global settings object.
    settings = application.settings if application else global_settings()

    if not settings:
        _logger.error(
            "Failed to set llm_token_count_callback. Settings not found on application or in global_settings."
        )
        return

    if not callback:
        settings.ai_monitoring._llm_token_count_callback = None
        return

    def _wrap_callback(model, content):
        if model is None:
            _logger.debug(
                "The model argument passed to the user-defined token calculation callback is None. The callback will not be run."
            )
            return None

        if content is None:
            _logger.debug(
                "The content argument passed to the user-defined token calculation callback is None. The callback will not be run."
            )
            return None

        token_count_val = callback(model, content)

        if not isinstance(token_count_val, int) or token_count_val < 0:
            _logger.warning(
                "llm_token_count_callback returned an invalid value of %s. This value must be a positive integer and will not be recorded for the token_count.",
                token_count_val,
            )
            return None

        return token_count_val

    settings.ai_monitoring._llm_token_count_callback = _wrap_callback
