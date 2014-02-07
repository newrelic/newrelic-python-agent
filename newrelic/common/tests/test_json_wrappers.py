import unittest

from collections import namedtuple

from newrelic.common.encoding_utils import json_encode, json_decode

class JSONWrapperTests(unittest.TestCase):

    def test_json_encode_objects(self):
        result = json_encode((1, 2.0, '3', u'4', (1,), [2], {3: 4}))
        self.assertEqual(result, '[1,2.0,"3","4",[1],[2],{"3":4}]')

    def test_json_encode_invalid_utf8_byte_string(self):
        result = json_encode(b'\xe2')
        self.assertEqual(result, u'"\\u00e2"')

    def test_json_encode_namedtuple(self):
        NamedTuple = namedtuple('NamedTuple', 'a b c d')

        result = json_encode(NamedTuple(a=1, b=2, c=3, d=4))
        self.assertEqual(result, '[1,2,3,4]')

    def test_json_encode_generator(self):
        def items():
            yield 1
            yield 2
            yield 3
            yield 4

        result = json_encode(items())
        self.assertEqual(result, '[1,2,3,4]')

    def test_json_encode_iterable(self):
        class Items(object):
            def __iter__(self):
                return iter((1, 2, 3, 4))

        result = json_encode(Items())
        self.assertEqual(result, '[1,2,3,4]')

    def test_json_encode_override_separators(self):
        result = json_encode((1, 2.0, '3', u'4', (1,), [2], {'3': 4}),
                separators=None)
        self.assertEqual(result, '[1, 2.0, "3", "4", [1], [2], {"3": 4}]')

    def test_json_encode_override_default_encoder(self):
        class Item(object):
            pass

        def _encode(o):
            if isinstance(o, Item):
                return 'ITEM'
            raise TypeError(repr(o) + ' is not JSON serializable')

        result = json_encode(Item(), default=_encode)
        self.assertEqual(result, '"ITEM"')

    def test_json_decode_string(self):
        result = json_decode('[1,2.0,"3","4",[1],[2],{"3":4}]')
        self.assertEqual(result, [1, 2.0, u'3', u'4', [1], [2], {u'3': 4}])

if __name__ == '__main__':
    unittest.main()
