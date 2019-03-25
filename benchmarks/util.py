from newrelic.common.object_wrapper import FunctionWrapper
from newrelic.api.transaction import Sentinel, Transaction
from newrelic.api.web_transaction import WSGIWebTransaction
from newrelic.common.encoding_utils import json_encode, obfuscate
from newrelic.core.config import finalize_application_settings


try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock


def make_cross_agent_headers(payload, encoding_key, cat_id):
    value = obfuscate(json_encode(payload), encoding_key)
    id_value = obfuscate(cat_id, encoding_key)
    return {'X-NewRelic-Transaction': value, 'X-NewRelic-ID': id_value}


def make_synthetics_header(account_id, resource_id, job_id, monitor_id,
            encoding_key, version=1):
    value = [version, account_id, resource_id, job_id, monitor_id]
    value = obfuscate(json_encode(value), encoding_key)
    return {'X-NewRelic-Synthetics': value}


def make_incoming_headers(transaction):
    settings = transaction.settings
    encoding_key = settings.encoding_key

    headers = []

    cross_process_id = '1#2'
    path = 'test'
    queue_time = 1.0
    duration = 2.0
    read_length = 1024
    guid = '0123456789012345'
    record_tt = False

    payload = (cross_process_id, path, queue_time, duration, read_length,
            guid, record_tt)
    app_data = json_encode(payload)

    value = obfuscate(app_data, encoding_key)

    headers.append(('X-NewRelic-App-Data', value))

    return headers


class MockApplication(object):
    def __init__(self, name='Python Application', settings=None):
        settings = settings or {}
        final_settings = finalize_application_settings(settings)
        self.global_settings = final_settings
        self.global_settings.enabled = True
        self.settings = final_settings
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None
        self.nodes = []

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        self.nodes.append(data)
        return None

    def compute_sampled(self):
        return True


class MockTrace(object):
    def __init__(*args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass


class MockTransaction(WSGIWebTransaction):
    def __init__(self, application, *args, **kwargs):
        self._state = WSGIWebTransaction.STATE_STOPPED
        self.stopped = False
        self.enabled = True
        self.current_node = None
        self.client_cross_process_id = None
        self._frameworks = set()
        self._name_priority = 0
        self._settings = application.settings
        self._trace_node_count = 0
        self.current_node = Sentinel()
        self._string_cache = {}
        self._stack_trace_count = 0
        self._explain_plan_count = 0
        self._response_headers = {}
        self._request_headers = {}

        self.autorum_disabled = False
        self.rum_header_generated = False

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        pass

    def _push_current(self, *args, **kwargs):
        pass

    def _pop_current(self, *args, **kwargs):
        pass


class MockTransactionCache(object):
    def save_transaction(*args, **kwargs):
        pass

    def drop_transaction(*args, **kwargs):
        pass

    def current_thread_id(*args, **kwargs):
        pass


class MockTransactionCAT(MockTransaction):
    def __init__(self, *args, **kwargs):
        super(MockTransactionCAT, self).__init__(*args, **kwargs)
        self.client_cross_process_id = '1#1'
        self.queue_start = 0.0
        self.start_time = 0.0
        self.end_time = 0.0
        self._frozen_path = 'foobar'
        self._read_length = None
        self.guid = 'GUID'
        self.record_tt = False


class VeryMagicMock(MagicMock):
    def __setattr__(self, attrname, value):
        if attrname == '__init__':
            object.__setattr__(self, attrname, value)
        else:
            super(VeryMagicMock, self).__setattr__(attrname, value)


def BenchInstrumentBase(module):
    """
    Base class for benchmark suite for instrumentaiton points. Takes one
    argument, a module object, and returns a benchmark suite class. Will
    auto-discover instrumentation points by searching for methods in the module
    starting with `instrument_`.

    Example usage:
        from benchmarks.util import TimeInstrumentBase
        import newrelic.hooks.framework_django as framework_django

        class TimeDjangoInstrument(TimeInstrumentBase(framework_django)):
            pass
    """

    class _TimeInstrumentBase(object):
        params = []
        param_names = ['instrumentation point']

        def setup(self, param):
            self.function = getattr(self.module, param)

        def time_instrument(self, param):
            self.function(VeryMagicMock())

    for attribute in dir(module):
        if attribute.startswith('instrument_'):
            _TimeInstrumentBase.params.append(attribute)

    _TimeInstrumentBase.module = module
    return _TimeInstrumentBase


class _BenchWrapsBase(object):
    """
    Base class for benchmarking hook points. Takes two arguments. The first is
    the module object. The second is a list of "specs".

    Each spec has the form of: (name, [optional_params])
    optional_params is a dict with the following keys:

    extra_attr:
        list; default is [].
        sometimes the wrapping function will expect the instrance to have some
        other attributes, so figure out what they are and list them here.

    wrapped_params:
        int; default is 1.
        this is the number of params the wrapped function expects when called.

    returned_values:
        int; default is 1.
        sometimes the wrapper needs to call the wrapped function for some
        reason; this is the number of values it will return.

    returns_iterable:
        bool; default is False.
        set to True if this function yields a series of wrappers instead of
        just the wrapped function.

    via_wrap_function_wrapper:
        bool; default is False.
        set to True if this function is directly wrapped via FunctionWrapper
        or wrap_function_wrapper instead of with a custom wrapper.

    Example usage:
        from benchmarks.util import BenchWrapBase, BenchWrappedBase
        import newrelic.hooks.framework_django as framework_django

        specs = [
            ('wrap_view_handler'),
            ('wrap_url_resolver_nnn', {
                'extra_attr': ['name'],
                'returned_values': 2
            }),
            # ...
        ]

        class BenchDjangoWrap(BenchWrapping(framework_django, *specs)):
            pass

        class BenchDjangoExec(BenchWrappedExecution(framework_django, *specs)):
            pass
    """

    spec_param_defaults = {
        'extra_attr': [],
        'wrapped_params': 1,
        'returned_values': 1,
        'returns_iterable': False,
        'via_wrap_function_wrapper': False
    }

    def setup(self, name):
        spec = self.spec_index[name]
        self.setup_wrap(spec)

        self.transaction = Transaction(MockApplication())
        self.transaction.__enter__()

    def teardown(self, name):
        self.transaction.__exit__(None, None, None)

    def dummy(self, *args, **kwargs):
        pass

    def setup_wrap(self, spec):
        self.to_test = spec['to_test']

    @classmethod
    def build_suite(cls, module, *spec_list):
        cls.spec_index = {}
        cls.params = []
        cls.param_names = [cls.__name__.replace('_Bench', '').lower()]

        for spec in spec_list:
            name, options = (spec if isinstance(spec, tuple) else (spec, {}))

            spec = cls.spec_param_defaults.copy()
            spec.update(options)
            spec['to_test'] = getattr(module, name)

            for extra_attr_name in spec['extra_attr']:
                setattr(cls, extra_attr_name, VeryMagicMock())

            cls.spec_index[name] = spec
            cls.params.append(name)

        return cls


def BenchWrappingBase(module, *spec):
    class BenchWrapping(_BenchWrapsBase):
        def time_wrap(self, name):
            self.to_test(self.dummy)

    return BenchWrapping.build_suite(module, *spec)


def BenchWrappedExecutionBase(module, *spec):
    class BenchWrappedExecution(_BenchWrapsBase):
        def setup(self, name):
            super(BenchWrappedExecution, self).setup(name)
            spec = self.spec_index[name]

            self.dummy_args = [VeryMagicMock()] * spec['wrapped_params']
            self.dummy_ret = (
                [VeryMagicMock()] * spec['returned_values']
                if spec['returned_values'] > 1 else VeryMagicMock())

        def setup_wrap(self, spec):
            super(BenchWrappedExecution, self).setup_wrap(spec)

            if spec['via_wrap_function_wrapper']:
                self.wrapped_dummy = FunctionWrapper(self.dummy, self.to_test)

            elif spec['returns_iterable']:
                self.wrapped_dummy = self.to_test([self.dummy])

            else:
                self.wrapped_dummy = self.to_test(self.dummy)

            if '__iter__' in dir(self.wrapped_dummy):
                self.wrapped_dummy = next(self.wrapped_dummy)

        def time_execute_wrap(self, name):
            return (self.wrapped_dummy)(*self.dummy_args)

        def dummy(self, *args, **kwargs):
            return self.dummy_ret

    return BenchWrappedExecution.build_suite(module, *spec)
