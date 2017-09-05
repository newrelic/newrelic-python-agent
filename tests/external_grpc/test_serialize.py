import six
from newrelic.api.background_task import background_task

from testing_support.fixtures import validate_transaction_metrics


_metric_cpp_from_string_py2_py3 = (
        ('Function/google.protobuf.pyext.cpp_message:'
        'Message.FromString'), 1)
_metric_python_from_string_py2 = (
        ('Function/google.protobuf.internal.python_message:'
        'FromString'), 1)
_metric_python_from_string_py3 = (
        ('Function/google.protobuf.internal.python_message:'
        '_AddStaticMethods.<locals>.FromString'), 1)


def _get_impl_type():
    # the particular return value of this function determines which classes
    # google uses to implement serialize and deserialze functions
    # https://github.com/google/protobuf/blob/c7457ef65a7a8584b1e3bd396c401ccf8e275ffa/python/google/protobuf/reflection.py#L55-L58
    from google.protobuf.internal import api_implementation
    return api_implementation.Type()


def _deserialize_metrics():
    _test_scoped_metrics, _test_rollup_metrics = [], []
    implementation_type = _get_impl_type()
    if implementation_type == 'cpp':
        _test_scoped_metrics.append(_metric_cpp_from_string_py2_py3)
        _test_rollup_metrics.append(_metric_cpp_from_string_py2_py3)
    else:
        if six.PY2:
            _test_scoped_metrics.append(_metric_python_from_string_py2)
            _test_rollup_metrics.append(_metric_python_from_string_py2)
        else:
            _test_scoped_metrics.append(_metric_python_from_string_py3)
            _test_rollup_metrics.append(_metric_python_from_string_py3)

    return _test_scoped_metrics, _test_rollup_metrics


def test_serialize_methods():
    from sample_application.sample_application_pb2 import Message
    m = Message(text='Hello World', count=1, timesout=False)

    scoped, rollup = (
        [('Function/sample_application_pb2:Message.SerializeToString', 1)],
        [('Function/sample_application_pb2:Message.SerializeToString', 1)],
    )

    if six.PY2:
        _test_transaction_name = 'test_serialize:_test'
    else:
        _test_transaction_name = (
                'test_serialize:test_serialize_methods.<locals>._test')

    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task()
    def _test():
        assert m.SerializeToString()

    _test()


def test_deserialize_methods():
    from sample_application.sample_application_pb2 import Message
    m = Message(text='Hello World', count=1, timesout=False)

    if six.PY2:
        _test_transaction_name = 'test_serialize:_test'
    else:
        _test_transaction_name = (
                'test_serialize:test_deserialize_methods.<locals>._test')

    scoped, rollup = _deserialize_metrics()

    s = m.SerializeToString()

    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=scoped,
            rollup_metrics=rollup,
            background_task=True)
    @background_task()
    def _test():
        assert Message.FromString(s)

    _test()
