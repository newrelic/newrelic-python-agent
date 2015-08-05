from collections import namedtuple

from .attribute_filter import DST_ERROR_COLLECTOR, DST_TRANSACTION_TRACER


INTRINSIC_DEFAULT_DST = DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER
AGENT_DEFAULT_DST = DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER

_Attribute = namedtuple('_Attribute',
        ['name', 'value', 'destinations'])

class Attribute(_Attribute):

    def __repr__(self):
        return "Attribute(name=%r, value=%r, destinations=%r)" % (
                self.name, self.value, bin(self.destinations))

def create_intrinsic_attributes(attr_dict):

    # Intrinsic attributes don't go through the Attribute Filter

    destinations = INTRINSIC_DEFAULT_DST
    return [Attribute(k, v, destinations) for k, v in attr_dict.items()]

def create_attributes(attr_dict, destinations, attribute_filter):
    attributes = []

    for k, v in attr_dict.items():
        dest = attribute_filter.apply(k, destinations)
        attributes.append(Attribute(k, v, dest))

    return attributes

def create_agent_attributes(attr_dict, attribute_filter):
    destinations = AGENT_DEFAULT_DST
    return create_attributes(attr_dict, destinations, attribute_filter)
