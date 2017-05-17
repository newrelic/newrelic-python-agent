import pytest
import json
import os

from contextlib import contextmanager

from newrelic.api.application import (application_instance as
        current_application)
from newrelic.api.background_task import BackgroundTask
from newrelic.core.rules_engine import SegmentCollapseEngine
from newrelic.core.agent import agent_instance

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
    engine = SegmentCollapseEngine(transaction_segment_terms)
    for test in tests:
        assert engine.normalize(test['input'])[0] == test['expected']

@contextmanager
def segment_rules(name, rules):
    application = agent_instance().application(name)
    old_rules = application._rules_engine['segment']
    new_rules = SegmentCollapseEngine(rules) 
    application._rules_engine['segment'] = new_rules
    yield
    application._rules_engine['segment'] = old_rules

@pytest.mark.parametrize(_parameters, load_tests())
def test_transaction_freeze_path_segments(testname, transaction_segment_terms,
        tests):

    application = current_application()

    # We can't check all possibilites by doing things via the transaction
    # as it not possible to set up a metric path of only one segment.

    with segment_rules(application.name, transaction_segment_terms):
        for test in tests:
            segments = test['input'].split()
            if len(segments) < 2:
                continue

            ttype = segments[0]
            group = '/'.join(segments[1:2])
            name = '/'.join(segments[2:])

            with BackgroundTask(application, name, group) as transaction:
                transaction.background_task = (ttype == 'OtherTransaction')

            assert transaction.path == test['expected']
