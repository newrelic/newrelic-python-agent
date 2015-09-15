from collections import namedtuple, defaultdict

from .attribute_filter import (DST_ALL, DST_ERROR_COLLECTOR,
        DST_TRANSACTION_TRACER, DST_NONE, DST_TRANSACTION_EVENTS)

_Attribute = namedtuple('_Attribute',
        ['name', 'value', 'destinations'])

# The following defaults map, _DEFAULT_DESTINATIONS is created here, never
# changed, and only used in create_agent_attributes. It is placed at the module
# level here as an optimization

# All agent attributes go to transaction traces and error traces by default

_DEFAULT_DESTINATIONS = defaultdict(lambda:
        DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER)

# The following subset goes to transaction events by default

trans_event_default = [
        'request.method',
        'request.headers.content-type',
        'request.headers.content-length',
        'response.status',
        'response.content-length'
]
for attr in trans_event_default:
    _DEFAULT_DESTINATIONS[attr] |= DST_TRANSACTION_EVENTS

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
        dest = attribute_filter.apply(k, _DEFAULT_DESTINATIONS[k])
        attributes.append(Attribute(k, v, dest))

    return attributes

def create_user_attributes(attr_dict, attribute_filter):
    destinations = DST_ALL
    return create_attributes(attr_dict, destinations, attribute_filter)
