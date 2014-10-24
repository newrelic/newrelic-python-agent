import json
import os
import pytest
import webtest

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures'))

_parameters_list = ["name", "appName", "transactionName", "transactionGuid",
        "inboundPayload", "outboundRequests", "expectedIntrinsicFields",
        "nonExpectedIntrinsicFields"]

def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'cat_map.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result

_parameters = ",".join(_parameters_list)

@pytest.mark.parametrize(_parameters, load_tests())
def test_cat_map(name, appName, transactionName, transactionGuid,
        inboundPayload, outboundRequests, expectedIntrinsicFields,
        nonExpectedIntrinsicFields):
    print "***"
    print name
    print appName
    print transactionName
    print transactionGuid
    print inboundPayload
    print outboundRequests
    print expectedIntrinsicFields
    print nonExpectedIntrinsicFields
    print "***"
    assert False

    # @validate_cat_transaction()
    # @override_settings(_settings)
    def run_cat_test():
        assert True

    run_cat_test()
