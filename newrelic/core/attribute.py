import logging

from collections import namedtuple

from ..packages import six

from .attribute_filter import (DST_ALL, DST_ERROR_COLLECTOR,
        DST_TRANSACTION_TRACER, DST_NONE, DST_TRANSACTION_EVENTS)


_logger = logging.getLogger(__name__)

_Attribute = namedtuple('_Attribute',
        ['name', 'value', 'destinations'])

# The following destinations are created here, never changed, and only used in
# create_agent_attributes. It is placed at the module level here as an optimization

# All agent attributes go to transaction traces and error traces by default

_DESTINATIONS = DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER
_DESTINATIONS_WITH_EVENTS = _DESTINATIONS | DST_TRANSACTION_EVENTS

# The following subset goes to transaction events by default

_TRANSACTION_EVENT_DEFAULT_ATTRIBUTES = [
        'request.method',
        'request.headers.content-type',
        'request.headers.content-length',
        'response.status',
        'response.content-length'
]

class TooManyAttributesException(Exception): pass
class IntTooLargeException(Exception): pass
class NameTooLongException(Exception): pass
class NameIsNotStringException(Exception): pass

class Attribute(_Attribute):

    def __repr__(self):
        return "Attribute(name=%r, value=%r, destinations=%r)" % (
                self.name, self.value, bin(self.destinations))

def create_attributes(attr_dict, destinations, attribute_filter):
    attributes = []

    for k, v in attr_dict.items():
        dest = attribute_filter.apply(k, destinations)
        attributes.append(Attribute(k, v, dest))

    return attributes

def create_agent_attributes(attr_dict, attribute_filter):
    attributes = []

    for k, v in attr_dict.items():
        if k in _TRANSACTION_EVENT_DEFAULT_ATTRIBUTES:
            dest = attribute_filter.apply(k, _DESTINATIONS_WITH_EVENTS)
        else:
            dest = attribute_filter.apply(k, _DESTINATIONS)

        attributes.append(Attribute(k, v, dest))

    return attributes

def create_user_attributes(attr_dict, attribute_filter):
    destinations = DST_ALL
    return create_attributes(attr_dict, destinations, attribute_filter)

def truncate(text, maxsize, encoding='utf-8'):

    # Truncate text so that it's byte representation
    # is no longer than maxsize bytes.

    # If text is unicode (Python 2 or 3), return unicode.
    # If text is a Python 2 string, return str.

    if isinstance(text, six.text_type):
        return _truncate_unicode(text, maxsize, encoding)
    else:
        return _truncate_bytes(text, maxsize)

def _truncate_unicode(u, maxsize, encoding='utf-8'):
    encoded = u.encode(encoding)[:maxsize]
    return encoded.decode(encoding, 'ignore')

def _truncate_bytes(s, maxsize):
    return s[:maxsize]

def user_attr_name_length_ok(name, value, maxsize=255):
    trunc_name = truncate(name, maxsize)
    if name != trunc_name:
        _logger.debug('Attribute name exceeds maximum length (%r bytes). '
                'Dropping attribute: %r=%r', maxsize, name, value)
        return False
    else:
        return True

def truncate_attribute_value(name, value, maxsize=255):
    trunc_value = truncate(value, maxsize)
    if value != trunc_value:
        _logger.debug('Attribute value exceeds maximum length '
                '(%r bytes). Truncating value: %r=%r.',
                maxsize, name, trunc_value)
    return (name, trunc_value)

def check_max_user_attributes(num_stored, max_count=64):
    if num_stored >= max_count:
        raise TooManyAttributesException()

def check_name_length(name, max_length=255, encoding='utf-8'):
    trunc_name = truncate(name, max_length, encoding)
    if name != trunc_name:
        raise NameTooLongException()

def check_name_is_string(name):
    if not isinstance(name, (six.text_type, six.binary_type)):
        raise NameIsNotStringException()
