from collections import namedtuple


_Attribute = namedtuple('_Attribute',
        ['name', 'value', 'destinations'])

class Attribute(_Attribute):

    def __repr__(self):
        return "Attribute(name=%r, value=%r, destinations=%r)" % (
                self.name, self.value, bin(self.destinations))
