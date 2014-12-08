import pytest
import json
import os

from newrelic.core.rules_engine import SegmentCollapseEngine

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures'))
OUTBOUD_REQUESTS = {}

_parameters_list = ['testname', 'transaction_segment_terms', 'tests']

def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'transaction_segment_terms.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result

_parameters = ",".join(_parameters_list)

@pytest.mark.parametrize(_parameters, load_tests())
def test_transaction_segments(testname, transaction_segment_terms, tests):
    print testname
    print transaction_segment_terms
    print tests
    engine = SegmentCollapseEngine(transaction_segment_terms)
    for test in tests:
        assert engine.normalize(test['input']) == test['expected']
