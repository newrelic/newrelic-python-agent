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
import re
import time

from newrelic.core.attribute import (
    MAX_64_BIT_INT,
    MAX_ML_ATTRIBUTE_LENGTH,
    MAX_NUM_ML_USER_ATTRIBUTES,
    MAX_NUM_USER_ATTRIBUTES,
    NameIsNotStringException,
    NameTooLongException,
    check_name_is_string,
    check_name_length,
    process_user_attribute,
)
from newrelic.core.config import global_settings

_logger = logging.getLogger(__name__)

EVENT_TYPE_VALID_CHARS_REGEX = re.compile(r"^[a-zA-Z0-9:_ ]+$")
NO_LIMIT_LLM_EVENT_TYPE = {"LlmChatCompletionMessage": "content", "LlmEmbedding": "input"}


class NameInvalidCharactersException(Exception):
    pass


def check_event_type_valid_chars(name):
    regex = EVENT_TYPE_VALID_CHARS_REGEX
    if not regex.match(name):
        raise NameInvalidCharactersException


def process_event_type(name):
    """Perform all necessary validation on a potential event type.

    If any of the validation checks fail, they will raise an exception
    which we catch, so we can log a message, and return None.

    Args:
        name (str): The type (name) of the custom event.

    Returns:
          name, if name is OK.
          NONE, if name isn't.

    """

    FAILED_RESULT = None

    try:
        check_name_is_string(name)
        check_name_length(name)
        check_event_type_valid_chars(name)

    except NameIsNotStringException:
        _logger.debug("Event type must be a string. Dropping event: %r", name)
        return FAILED_RESULT

    except NameTooLongException:
        _logger.debug("Event type exceeds maximum length. Dropping event: %r", name)
        return FAILED_RESULT

    except NameInvalidCharactersException:
        _logger.debug("Event type has invalid characters. Dropping event: %r", name)
        return FAILED_RESULT

    else:
        return name


def process_event_timestamp(name, timestamp):
    """Validate timestamp for a custom event.

    Ensures each custom event has a valid timestamp to prevent the server
    from discarding the event completely. If the timestamp is missing or
    invalid, we log a message and fall back to the current time instead.

    Args:
        name (str): The type (name) of the custom event.
        timestamp: The supplied timestamp, if any.

    Returns:
        The timestamp as an int, or the current time in milliseconds if
        the timestamp is missing or invalid.

    """
    if not timestamp:
        return int(1000.0 * time.time())

    # Some numpy types, such as numpy.int64, do not inherit from int
    # so convert them before validating
    if hasattr(timestamp, "item"):
        try:
            timestamp = timestamp.item()
        except Exception:
            pass

    # bool is a subclass of int, but not a valid timestamp
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        reason = "must be an int or float"
    elif timestamp < 0:
        reason = "must be positive"
    elif timestamp > MAX_64_BIT_INT:
        reason = "must fit in a 64 bit integer"
    else:
        try:
            return int(timestamp)
        except Exception:
            reason = "could not be converted to an int"

    _logger.debug(
        "Custom event timestamp %s. Using current time for event %r. Invalid timestamp: %r", reason, name, timestamp
    )
    return int(1000.0 * time.time())


def create_custom_event(event_type, params, settings=None, is_ml_event=False):
    """Creates a valid custom event.

    Ensures that the custom event has a valid name, and also checks
    the format and number of attributes. No event is created, if the
    name is invalid. An event is created, if any of the attributes are
    invalid, but the invalid attributes are dropped.

    Args:
        event_type (str): The type (name) of the custom event.
        params (dict): Attributes to add to the event.
        settings: Optional config settings.
        is_ml_event (bool): Boolean indicating whether create_custom_event was called from
        record_ml_event for truncation purposes

    Returns:
        Custom event (list of 2 dicts), if successful.
        None, if not successful.

    """
    settings = settings or global_settings()

    name = process_event_type(event_type)

    if name is None:
        return None

    attributes = {}

    try:
        for k, v in params.items():
            if is_ml_event:
                max_length = MAX_ML_ATTRIBUTE_LENGTH
                max_num_attrs = MAX_NUM_ML_USER_ATTRIBUTES
            else:
                max_length = (
                    settings.custom_insights_events.max_attribute_value
                    if not (NO_LIMIT_LLM_EVENT_TYPE.get(name) == k)
                    else None
                )
                max_num_attrs = MAX_NUM_USER_ATTRIBUTES
            key, value = process_user_attribute(k, v, max_length=max_length)
            if key:
                if len(attributes) >= max_num_attrs:
                    _logger.debug(
                        "Maximum number of attributes already added to event %r. Dropping attribute: %r=%r",
                        name,
                        key,
                        value,
                    )
                else:
                    attributes[key] = value
    except Exception:
        _logger.debug(
            "Attributes failed to validate for unknown reason. Check traceback for clues. Dropping event: %r.",
            name,
            exc_info=True,
        )
        return None

    intrinsics = {"type": name, "timestamp": process_event_timestamp(name, params.get("timestamp"))}

    event = [intrinsics, attributes]
    return event
