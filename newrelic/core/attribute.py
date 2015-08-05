from collections import namedtuple

from .attribute_filter import DST_ERROR_COLLECTOR, DST_TRANSACTION_TRACER


INTRINSIC_DEFAULT_DST = DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER

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
