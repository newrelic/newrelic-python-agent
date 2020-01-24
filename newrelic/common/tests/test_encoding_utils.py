import unittest
import pytest
import newrelic.packages.six as six

from newrelic.common.encoding_utils import (decode_newrelic_header, obfuscate,
        json_encode, ensure_str, W3CTraceParent, W3CTraceState, NrTraceState)


ENCODING_KEY = '1234567890123456789012345678901234567890'


class EncodingUtilsTests(unittest.TestCase):

    def test_decode_newrelic_header_invalid(self):
        decoded = decode_newrelic_header('oopsie', ENCODING_KEY)
        assert decoded is None

    def test_decode_newrelic_header_valid(self):
        payload = ['9323dc260548ed0e', False, '9323dc260548ed0e', '3b0939af']
        header = obfuscate(json_encode(payload), ENCODING_KEY)
        assert decode_newrelic_header(header, ENCODING_KEY) == payload

    def test_decode_newrelic_header_none(self):
        assert decode_newrelic_header(None, ENCODING_KEY) is None

    def test_decode_newrelic_header_encoding_key_none(self):
        payload = ['9323dc260548ed0e', False, '9323dc260548ed0e', '3b0939af']
        header = obfuscate(json_encode(payload), ENCODING_KEY)
        assert decode_newrelic_header(header, None) is None

    def test_ensure_str_unicode(self):
        unicode_input = u'test_input'

        result = ensure_str(unicode_input)
        self.assertEqual(result, unicode_input)

    def test_ensure_str_bytes(self):
        bytes_input = b'test_input'
        output = bytes_input.decode('utf-8')

        result = ensure_str(bytes_input)
        self.assertEqual(result, output)

    def test_ensure_str_bytearray(self):
        bytes_input = bytearray('test_input', 'utf-8')
        output = bytes_input.decode('utf-8')

        result = ensure_str(bytes_input)
        self.assertEqual(result, output)

    @pytest.mark.skipif(six.PY2,
            reason='cp424 is bytes in PY3 but str in PY2, so skip')
    def test_ensure_str_cp424(self):
        assert ensure_str('test'.encode('cp424')) is None

    def test_ensure_str_string(self):
        str_input = 'test_input'

        result = ensure_str(str_input)
        self.assertEqual(result, str_input)

    def test_ensure_str_none(self):
        assert ensure_str(None) is None


@pytest.mark.parametrize('payload,valid', (
    ('00-11111111111111111111111111111111-2222222222222222-1', False),
    ('000-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-111111111111111111111111111111111-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-22222222222222222-01', False),
    ('00-11111111111111111111111111111111-2222222222222222-001', False),
    ('00-11111111111111111111111111111111-0000000000000000-01', False),
    ('00-00000000000000000000000000000000-1111111111111111-01', False),
    ('ff-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-CCCCCCCCCCCCCCCC-01', False),
    ('00-11111111111111111111111111111111-2222222222222222-CC', False),
    ('CC-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-2222222222222222101', False),
    ('00-11111111111111111111111111111111-2222222222222222-01-1', False),
    ('00-11111111111111111111111111111111-2222222222222222-01', True),
    ('cc-11111111111111111111111111111111-2222222222222222-01', True),
    ('01-11111111111111111111111111111111-2222222222222222-01-1', True),
))
def test_traceparent_decode(payload, valid):
    if valid:
        expected = {
            'tr': '11111111111111111111111111111111',
            'id': '2222222222222222',
        }
    else:
        expected = None

    assert W3CTraceParent.decode(payload) == expected


@pytest.mark.parametrize('span_id,sampled', (
    ('2222222222222222', True),
    (None, True),
    (None, None),
    (None, False),
))
def test_traceparent_text(span_id, sampled):
    trace_id = '1111111111111111'
    data = {'tr': trace_id}
    expected_trace_id = '00000000000000001111111111111111'

    if span_id:
        data['id'] = span_id

    if sampled is not None:
        data['sa'] = sampled

    text = W3CTraceParent(data).text()
    assert len(text) == 55

    fields = text.split('-')
    assert len(fields) == 4

    assert fields[1] == expected_trace_id
    if span_id:
        assert fields[2] == span_id
    else:
        assert len(fields[2]) == 16

    if sampled:
        assert fields[3] == '01'
    else:
        assert fields[3] == '00'


@pytest.mark.parametrize('payload,expected', (
    ('', {}),
    ('rojo=00f067aa0ba902b7,congo=t61rcWkgMzE',
            {'rojo': '00f067aa0ba902b7', 'congo': 't61rcWkgMzE'}),
    ('x=,y=', {'x': '', 'y': ''}),
    ('=foo', {'': 'foo'}),
    ('=', {'': ''}),
))
def test_w3c_tracestate_decode(payload, expected):
    vendors = W3CTraceState.decode(payload)
    assert vendors == expected


def test_w3c_tracestate_text():
    tracestate = W3CTraceState()
    tracestate['x'] = '123'
    tracestate['y'] = '456'
    tracestate['z'] = '789'

    # Test that truncation is done in the proper order
    assert tracestate.text(limit=2) == 'x=123,y=456'


@pytest.mark.parametrize('payload,expected', (
    ('0-0-709288-8599547-spanid-txid-1-0.789-1563574856827',
            {'ty': 'App',
             'ac': '709288',
             'ap': '8599547',
             'id': 'spanid',
             'tx': 'txid',
             'sa': True,
             'pr': 0.789,
             'ti': 1563574856827}),
    ('0-0-709288-8599547-spanid-txid-1-0.789-1563574856827-extra-field',
            {'ty': 'App',
             'ac': '709288',
             'ap': '8599547',
             'id': 'spanid',
             'tx': 'txid',
             'sa': True,
             'pr': 0.789,
             'ti': 1563574856827}),
    ('0-0-1349956-41346604--b28be285632bbc0a-1-1.1273-1569367663277',
            {'ty': 'App',
             'ac': '1349956',
             'ap': '41346604',
             'tx': 'b28be285632bbc0a',
             'sa': True,
             'pr': 1.1273,
             'ti': 1569367663277}),
    ('0-0-1349956-41346604-27ddd2d8890283b4--1-1.1273-1569367663277',
            {'ty': 'App',
             'ac': '1349956',
             'ap': '41346604',
             'id': '27ddd2d8890283b4',
             'sa': True,
             'pr': 1.1273,
             'ti': 1569367663277}),
    ('0-2-332029-2827902-5f474d64b9cc9b2a-7d3efb1b173fecfa---1518469636035',
            {'ty': 'Mobile',
             'ac': '332029',
             'ap': '2827902',
             'id': '5f474d64b9cc9b2a',
             'tx': '7d3efb1b173fecfa',
             'ti': 1518469636035}),
    ('0-0-1349956-41346604-27ddd2d8890283b4--0-oops-1569367663277',
            {'ty': 'App',
             'ac': '1349956',
             'ap': '41346604',
             'id': '27ddd2d8890283b4',
             'sa': False,
             'pr': None,
             'ti': 1569367663277}),
    ('0-0-1349956-41346604-27ddd2d8890283b4--oops-0.1-1569367663277',
            {'ty': 'App',
             'ac': '1349956',
             'ap': '41346604',
             'id': '27ddd2d8890283b4',
             'sa': None,
             'pr': 0.1,
             'ti': 1569367663277}),
    ('0-8-1349956-41346604-27ddd2d8890283b4--1-1.1273-1569367663277',
            None),
))
def test_nr_tracestate_entry_decode(payload, expected):
    decoded = NrTraceState.decode(payload, '1')
    if decoded is not None:
        assert decoded.pop('tk') == '1'

    assert decoded == expected


@pytest.mark.parametrize('data,expected', (
    ({'ty': 'App',
      'ac': '709288',
      'ap': '8599547',
      'id': 'spanid',
      'tx': 'txid',
      'sa': True,
      'pr': 0.789,
      'ti': 1563574856827},
            '709288@nr=0-0-709288-8599547-spanid-txid-1-0.789-1563574856827'),
    ({'tk': '1',
      'ty': 'App',
      'ac': '709288',
      'ap': '8599547',
      'id': 'spanid',
      'tx': 'txid',
      'sa': False,
      'pr': 0.789,
      'ti': 1563574856827},
            '1@nr=0-0-709288-8599547-spanid-txid-0-0.789-1563574856827'),
    ({'tk': '1',
      'ty': 'App',
      'ac': '709288',
      'ap': '8599547',
      'tx': 'txid',
      'sa': True,
      'pr': 0.789,
      'ti': 1563574856827},
            '1@nr=0-0-709288-8599547--txid-1-0.789-1563574856827'),
    ({'tk': '1',
      'ty': 'App',
      'ac': '709288',
      'ap': '8599547',
      'id': 'spanid',
      'sa': True,
      'pr': 0.789,
      'ti': 1563574856827},
            '1@nr=0-0-709288-8599547-spanid--1-0.789-1563574856827'),
    ({'tk': '1',
      'ty': 'App',
      'ac': '709288',
      'ap': '8599547',
      'id': 'spanid',
      'tx': 'txid',
      'sa': True,
      'pr': 0.0078125,
      'ti': 1563574856827},
            '1@nr=0-0-709288-8599547-spanid-txid-1-0.007812-1563574856827'),
))
def test_nr_tracestate_entry_text(data, expected):
    assert NrTraceState(data).text() == expected


if __name__ == '__main__':
    unittest.main()
