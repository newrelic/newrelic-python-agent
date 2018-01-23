import grpc
import pytest

from newrelic.packages import six

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.api.external_trace import ExternalTrace

from testing_support.fixtures import override_application_settings

ENCODING_KEY = '1234567890123456789012345678901234567890'


@pytest.fixture(scope='module')
def grpc_cat_app_server(grpc_app_server):
    from sample_application import CatApplicationServicer
    from sample_application.sample_application_pb2_grpc import (
            add_SampleApplicationServicer_to_server)
    server, port = grpc_app_server
    add_SampleApplicationServicer_to_server(
            CatApplicationServicer(), server)
    return port


def _create_stub(port):
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)
    channel = grpc.insecure_channel('localhost:%s' % port)
    stub = SampleApplicationStub(channel)
    return stub


def _create_request(streaming_request, count=1, timesout=False):
    from sample_application.sample_application_pb2 import Message

    def _message_stream():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    if streaming_request:
        request = _message_stream()
    else:
        request = Message(text='Hello World', count=count, timesout=timesout)

    return request


_test_matrix = [
        'service_method_type,'
        'service_method_method_name,'
        'cat_enabled,'
        'user_sets_cat_metadata,'
        'expect_cat', (

        ('unary_unary', '__call__', True, True, True),
        ('unary_unary', 'with_call', True, True, True),
        ('stream_unary', '__call__', True, True, True),
        ('stream_unary', 'with_call', True, True, True),
        ('unary_stream', '__call__', True, True, True),
        ('stream_stream', '__call__', True, True, True),

        # CAT was removed from these calls
        ('unary_unary', '__call__', True, False, False),
        ('unary_unary', 'with_call', True, False, False),
        ('stream_unary', '__call__', True, False, False),
        ('stream_unary', 'with_call', True, False, False),
        ('unary_stream', '__call__', True, False, False),
        ('stream_stream', '__call__', True, False, False),

        ('unary_unary', '__call__', False, False, True),
        ('unary_unary', 'with_call', False, False, True),
        ('stream_unary', '__call__', False, False, True),
        ('stream_unary', 'with_call', False, False, True),
        ('unary_stream', '__call__', False, False, True),
        ('stream_stream', '__call__', False, False, True),
)]


@pytest.mark.parametrize(*_test_matrix)
def test_grpc_cat(service_method_type, service_method_method_name,
        cat_enabled, user_sets_cat_metadata, expect_cat, grpc_cat_app_server):
    service_method_class_name = 'Do%s' % (
            service_method_type.title().replace('_', ''))
    streaming_request = service_method_type.split('_')[0] == 'stream'
    streaming_response = service_method_type.split('_')[1] == 'stream'

    _custom_settings = {
            'cross_process_id': '1#1',
            'encoding_key': ENCODING_KEY,
            'trusted_account_ids': [1],
            'cross_application_tracer.enabled': cat_enabled,
            'transaction_tracer.transaction_threshold': 0.0,
    }

    # CAT values are valid regardless of the order in which keys are received
    if six.PY3:
        expected_cat_value = (
                'eyJYLU5ld1JlbGljLUlEIjoiQUJFQyIsIlgtTmV3UmVsaWMtVHJhbnNhY3Rpb24iOiJhaEJuZkh4bGFHeDhZMlZ0ZW1kcVpYaG5mbVY0ZGhFWVUxZGJTMXdjRTJaN2ZXWnBZMzFxWkc1N1lHdG1lV2gvYkhsMUVCOFdWZ0lQQ3dBSEFRTVJhUT09In0=',  # NOQA
                'eyJYLU5ld1JlbGljLVRyYW5zYWN0aW9uIjoiYWhCbmZIeGxhR3g4WTJWdGVtZHFaWGhuZm1WNGRoRVlVMWRiUzF3Y0UyWjdmV1pwWTMxcVpHNTdZR3RtZVdoL2JIbDFFQjhXVmdJUEN3QUhBUU1SYVE9PSIsIlgtTmV3UmVsaWMtSUQiOiJBQkVDIn0=')  # NOQA
    else:
        expected_cat_value = (
                'eyJYLU5ld1JlbGljLUlEIjoiQUJFQyIsIlgtTmV3UmVsaWMtVHJhbnNhY3Rpb24iOiJhaEJuZkh4bGFHeDhZMlZ0ZW1kcVpYaG5mbVY0ZGhFWVUxZGJTMXdjRTJaN2ZXWnBZMzFxWkc1N1lHdG1lV2gvYkhsMUVCOFdWZ0VBQ0YwSkJ3SVJhUT09In0=',  # NOQA
                'eyJYLU5ld1JlbGljLVRyYW5zYWN0aW9uIjoiYWhCbmZIeGxhR3g4WTJWdGVtZHFaWGhuZm1WNGRoRVlVMWRiUzF3Y0UyWjdmV1pwWTMxcVpHNTdZR3RtZVdoL2JIbDFFQjhXVmdFQUNGMEpCd0lSYVE9PSIsIlgtTmV3UmVsaWMtSUQiOiJBQkVDIn0=')  # NOQA

    if user_sets_cat_metadata:
        expected_cat_value = ('IM_A_CAT', )

    @background_task()
    @override_application_settings(_custom_settings)
    def _test():
        txn = current_transaction()
        txn.guid = 'THIS_TEST_IS_SO_GUID'

        stub = _create_stub(grpc_cat_app_server)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        request = _create_request(streaming_request)

        if user_sets_cat_metadata:
            reply = service_method_method(request,
                    metadata=[(ExternalTrace.cat_metadata_key, 'IM_A_CAT')])
        else:
            reply = service_method_method(request)

        if isinstance(reply, tuple):
            reply, rendezvous = reply

        if streaming_response:
            for response in reply:
                # extract CAT value
                cat_value = response.text.split(' ')[-1]
                if cat_enabled and expect_cat:
                    assert cat_value in expected_cat_value, response.text
                else:
                    assert cat_value not in expected_cat_value, response.text
        else:
            cat_value = reply.text.split(' ')[-1]
            if cat_enabled and expect_cat:
                assert cat_value in expected_cat_value, reply.text
            else:
                assert cat_value not in expected_cat_value, reply.text

    _test()
