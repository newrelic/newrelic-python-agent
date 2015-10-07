import pytest
import logging
import os
import sys
import pwd
import threading
import time
import json

from newrelic.packages import six

from newrelic.agent import (initialize, register_application,
        global_settings, shutdown_agent, application as application_instance,
        transient_function_wrapper, function_wrapper, application_settings,
        wrap_function_wrapper, ObjectProxy, application, callable_name,
        get_browser_timing_footer)

from newrelic.common.encoding_utils import (unpack_field, json_encode,
        deobfuscate, json_decode)

from newrelic.core.config import (apply_config_setting, flatten_settings)
from newrelic.core.database_utils import SQLConnections

from newrelic.network.addresses import proxy_details
from newrelic.packages import requests

from newrelic.core.agent import agent_instance
from newrelic.core.attribute_filter import AttributeFilter

_logger = logging.getLogger('newrelic.tests')

def _environ_as_bool(name, default=False):
    flag = os.environ.get(name, default)
    if default is None or default:
        try:
            flag = not flag.lower() in ['off', 'false', '0']
        except AttributeError:
            pass
    else:
        try:
            flag = flag.lower() in ['on', 'true', '1']
        except AttributeError:
            pass
    return flag

_fake_collector_responses = {
    'get_redirect_host': u'fake-collector.newrelic.com',

    'connect': {
        u'js_agent_loader': u'<!-- NREUM HEADER -->',
        u'js_agent_file': u'js-agent.newrelic.com/nr-0.min.js',
        u'browser_key': u'1234567890',
        u'browser_monitoring.loader_version': u'0',
        u'beacon': u'fake-beacon.newrelic.com',
        u'error_beacon': u'fake-jserror.newrelic.com',
        u'apdex_t': 0.5,
        u'encoding_key': u'd67afc830dab717fd163bfcb0b8b88423e9a1a3b',
        u'agent_run_id': 1234567,
        u'product_level': 50,
        u'trusted_account_ids': [12345],
        u'url_rules': [],
        u'collect_errors': True,
        u'cross_process_id': u'12345#67890',
        u'messages': [{u'message': u'Reporting to fake collector',
            u'level': u'INFO' }],
        u'sampling_rate': 0,
        u'collect_traces': True,
        u'data_report_period': 60
    },

    'metric_data': [],

    'get_agent_commands': [],

    'error_data': None,

    'transaction_sample_data': None,

    'sql_trace_data': None,

    'analytic_event_data': None,

    'agent_settings': None,

    'shutdown': None,
}

if _environ_as_bool('NEW_RELIC_HIGH_SECURITY'):
    _fake_collector_responses['connect']['high_security'] = True

def fake_collector_wrapper(wrapped, instance, args, kwargs):
    def _bind_params(session, url, method, license_key, agent_run_id=None,
            payload=()):
        return session, url, method, license_key, agent_run_id, payload

    session, url, method, license_key, agent_run_id, payload = _bind_params(
            *args, **kwargs)

    if method in _fake_collector_responses:
        return _fake_collector_responses[method]

    return wrapped(*args, **kwargs)

def collector_agent_registration_fixture(app_name=None, default_settings={},
        linked_applications=[]):
    @pytest.fixture(scope='session')
    def _collector_agent_registration_fixture(request):
        settings = global_settings()

        settings.app_name = 'Python Agent Test'

        settings.api_key = os.environ.get('NEW_RELIC_API_KEY',
                'acb213ed488e0e4b623c005a9811a5113c916c4f983d501')
        settings.license_key = os.environ.get('NEW_RELIC_LICENSE_KEY',
                '84325f47e9dec80613e262be4236088a9983d501')

        settings.host = os.environ.get('NEW_RELIC_HOST',
                'staging-collector.newrelic.com')
        settings.port = int(os.environ.get('NEW_RELIC_PORT', '0'))

        if settings.host == 'localhost':
            settings.license_key = 'bootstrap_newrelic_admin_license_key_000'
            if settings.port == 0:
                settings.port = 8081
            settings.ssl = False

        settings.startup_timeout = float(os.environ.get(
                'NEW_RELIC_STARTUP_TIMEOUT', 20.0))
        settings.shutdown_timeout = float(os.environ.get(
                'NEW_RELIC_SHUTDOWN_TIMEOUT', 20.0))

        if app_name is not None:
            settings.app_name = app_name

        for name, value in default_settings.items():
            apply_config_setting(settings, name, value)

        env_directory = os.environ.get('TOX_ENVDIR', None)

        if env_directory is not None:
            log_directory = os.path.join(env_directory, 'log')
        else:
            log_directory = '.'

        log_file = os.path.join(log_directory, 'python-agent-test.log')
        log_level = logging.DEBUG

        try:
            os.unlink(log_file)
        except OSError:
            pass

        class FilteredStreamHandler(logging.StreamHandler):
            def emit(self, record):
                if len(logging.root.handlers) != 0:
                    return

                if record.name.startswith('newrelic.packages'):
                    return

                if record.levelno < logging.WARNING:
                    return

                return logging.StreamHandler.emit(self, record)

        _stdout_logger = logging.getLogger('newrelic')
        _stdout_handler = FilteredStreamHandler(sys.stderr)
        _stdout_format = '%(levelname)s - %(message)s'
        _stdout_formatter = logging.Formatter(_stdout_format)
        _stdout_handler.setFormatter(_stdout_formatter)
        _stdout_logger.addHandler(_stdout_handler)

        initialize(log_file=log_file, log_level=log_level, ignore_errors=False)

        # Determine if should be using an internal fake local
        # collector for the test.

        use_fake_collector = _environ_as_bool(
                'NEW_RELIC_FAKE_COLLECTOR', False)
        use_developer_mode = _environ_as_bool(
                'NEW_RELIC_DEVELOPER_MODE', False)

        if use_fake_collector:
            wrap_function_wrapper('newrelic.core.data_collector',
                    'send_request', fake_collector_wrapper)

        # Attempt to record deployment marker for test. We don't
        # care if it fails.

        api_host = settings.host

        if api_host is None:
            api_host = 'api.newrelic.com'
        elif api_host == 'staging-collector.newrelic.com':
            api_host = 'staging-api.newrelic.com'

        url = '%s://%s/deployments.xml'

        scheme = settings.ssl and 'https' or 'http'
        server = settings.port and '%s:%d' % (api_host,
                settings.port) or api_host

        url = url % (scheme, server)

        proxy_host = settings.proxy_host
        proxy_port = settings.proxy_port
        proxy_user = settings.proxy_user
        proxy_pass = settings.proxy_pass

        timeout = settings.agent_limits.data_collector_timeout

        proxies = proxy_details(None, proxy_host, proxy_port, proxy_user,
                proxy_pass)

        user = pwd.getpwuid(os.getuid()).pw_gecos

        data = {}

        data['deployment[app_name]'] = settings.app_name
        data['deployment[description]'] = os.path.basename(
                os.path.normpath(sys.prefix))
        data['deployment[user]'] = user

        headers = {}

        headers['X-API-Key'] = settings.api_key

        if not use_fake_collector and not use_developer_mode:
            try:
                _logger.debug("Record deployment marker at %s" % url)
                r = requests.post(url, proxies=proxies, headers=headers,
                        timeout=timeout, data=data)
            except Exception:
                _logger.exception("Unable to record deployment marker.")
                pass

        # Associate linked applications.

        application = application_instance()

        for name in linked_applications:
            application.link_to_application(name)

        # Force registration of the application.

        application = register_application()

        def finalize():
            shutdown_agent()

        request.addfinalizer(finalize)

        return application

    return _collector_agent_registration_fixture

@pytest.fixture(scope='function')
def collector_available_fixture(request):
    application = application_instance()
    active = application.active
    assert active

def raise_background_exceptions(timeout=5.0):
    @function_wrapper
    def _raise_background_exceptions(wrapped, instance, args, kwargs):
        if getattr(raise_background_exceptions, 'enabled', None) is None:
            raise_background_exceptions.event = threading.Event()
        else:
            assert raise_background_exceptions.count == 0

        raise_background_exceptions.enabled = True
        raise_background_exceptions.count = 0
        raise_background_exceptions.exception = None
        raise_background_exceptions.event.clear()

        try:
            result = wrapped(*args, **kwargs)

        except:
            # There was an exception in the immediate decorators.
            # Raise it rather than those from background threads.

            raise_background_exceptions.event.clear()
            raise_background_exceptions.exception = None
            raise

        else:
            # Immediate decorators completed normally. We need
            # though to make sure that background threads
            # completed within the timeout period and that no
            # exception occurred in the background threads.

            raise_background_exceptions.enabled = False

            done = raise_background_exceptions.event.is_set()
            raise_background_exceptions.event.clear()

            exc_info = raise_background_exceptions.exception
            raise_background_exceptions.exception = None

            assert done, 'Timeout waiting for background task to finish.'

            if exc_info is not None:
                six.reraise(*exc_info)

        return result

    return _raise_background_exceptions

def wait_for_background_threads(timeout=5.0):
    @function_wrapper
    def _wait_for_background_threads(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        finally:
            raise_background_exceptions.event.wait(timeout)

    return _wait_for_background_threads

@function_wrapper
def catch_background_exceptions(wrapped, instance, args, kwargs):
    if not getattr(raise_background_exceptions, 'enabled', False):
        return wrapped(*args, **kwargs)

    raise_background_exceptions.count += 1

    try:
        return wrapped(*args, **kwargs)
    except:
        raise_background_exceptions.exception = sys.exc_info()
        raise
    finally:
        raise_background_exceptions.count -= 1
        if raise_background_exceptions.count == 0:
            raise_background_exceptions.event.set()

def validate_transaction_metrics(name, group='Function',
        background_task=False, scoped_metrics=[], rollup_metrics=[],
        custom_metrics=[]):

    if background_task:
        rollup_metric = 'OtherTransaction/all'
        transaction_metric = 'OtherTransaction/%s/%s' % (group, name)
    else:
        rollup_metric = 'WebTransaction'
        transaction_metric = 'WebTransaction/%s/%s' % (group, name)

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    @catch_background_exceptions
    def _validate_transaction_metrics(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            metrics = instance.stats_table

            def _validate(name, scope, count):
                key = (name, scope)
                metric = metrics.get(key)

                def _metrics_table():
                    return 'metric=%r, metrics=%r' % (key, metrics)

                def _metric_details():
                    return 'metric=%r, count=%r' % (key, metric.call_count)

                if count is not None:
                    assert metric is not None, _metrics_table()
                    assert metric.call_count == count, _metric_details()
                else:
                    assert metric is None, _metrics_table()

            _validate(rollup_metric, '', 1)
            _validate(transaction_metric, '', 1)

            for scoped_name, scoped_count in scoped_metrics:
                _validate(scoped_name, transaction_metric, scoped_count)

            for rollup_name, rollup_count in rollup_metrics:
                _validate(rollup_name, '', rollup_count)

            for custom_name, custom_count in custom_metrics:
                _validate(custom_name, '', custom_count)

        return result

    return _validate_transaction_metrics

def validate_transaction_errors(errors=[], required_params=[],
        forgone_params=[]):

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    @catch_background_exceptions
    def _validate_transaction_errors(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        if errors and isinstance(errors[0], (tuple, list)):
            expected = sorted(errors)
            captured = sorted([(e.type, e.message) for e in transaction.errors])

        else:
            expected = sorted(errors)
            captured = sorted([e.type for e in transaction.errors])

        assert expected == captured, 'expected=%r, captured=%r, errors=%r' % (
                expected, captured, transaction.errors)

        for e in transaction.errors:
            for name, value in required_params:
                assert name in e.custom_params, ('name=%r, '
                        'params=%r' % (name, e.custom_params))
                assert e.custom_params[name] == value, ('name=%r, value=%r, '
                        'params=%r' % (name, value, e.custom_params))

            for name, value in forgone_params:
                assert name not in e.custom_params, ('name=%r, '
                        'params=%r' % (name, e.custom_params))

        return wrapped(*args, **kwargs)

    return _validate_transaction_errors

def validate_custom_parameters(required_params=[], forgone_params=[]):

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    @catch_background_exceptions
    def _validate_custom_parameters(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        # these are pre-destination applied attributes, so they may not
        # actually end up in a transaction/error trace, we are merely testing
        # for presence on the TransactionNode

        attrs = {}
        for attr in transaction.user_attributes:
            attrs[attr.name] = attr.value

        for name, value in required_params:
            assert name in attrs, ('name=%r, '
                    'params=%r' % (name, attrs))
            assert attrs[name] == value, (
                    'name=%r, value=%r, params=%r' % (name, value,
                    attrs))

        for name, value in forgone_params:
            assert name not in attrs, ('name=%r, '
                    'params=%r' % (name, attrs))

        return wrapped(*args, **kwargs)

    return _validate_custom_parameters

def validate_synthetics_event(required_attrs=[], forgone_attrs=[],
        should_exist=True):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_synthetics_event(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            if not should_exist:
                assert instance.synthetics_events == []
            else:
                assert len(instance.synthetics_events) == 1
                event = instance.synthetics_events[0]
                assert event is not None
                assert len(event) == 3

                def _flatten(event):
                    result = {}
                    for elem in event:
                        for k, v in elem.items():
                            result[k] = v
                    return result

                flat_event = _flatten(event)

                assert 'nr.guid' in flat_event, ('name=%r, event=%r' %
                            (name, flat_event))

                for name, value in required_attrs:
                    assert name in flat_event, ('name=%r, event=%r' %
                            (name, flat_event))
                    assert flat_event[name] == value, ('name=%r, value=%r,'
                            'event=%r' % (name, value, flat_event))

                for name, value in forgone_attrs:
                    assert name not in flat_event, ('name=%r, value=%r,'
                        ' event=%r' % (name, value, flat_event))

        return result

    return _validate_synthetics_event

def validate_database_duration():
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_database_duration(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            metrics = instance.stats_table
            sampled_data_set = instance.sampled_data_set

            assert sampled_data_set.count == 1

            event = sampled_data_set.samples[0]
            intrinsics = event[0]

            # As long as we are sending 'Database' metrics, then
            # 'databaseDuration' and 'databaseCallCount' will be
            # the sum both 'Database' and 'Datastore' values.

            try:
                database_all = metrics[('Database/all', '')]
            except KeyError:
                database_all_duration = 0.0
                database_all_call_count = 0
            else:
                database_all_duration = database_all.total_call_time
                database_all_call_count = database_all.call_count

            try:
                datastore_all = metrics[('Datastore/all', '')]
            except KeyError:
                datastore_all_duration = 0.0
                datastore_all_call_count = 0
            else:
                datastore_all_duration = datastore_all.total_call_time
                datastore_all_call_count = datastore_all.call_count

            assert 'databaseDuration' in intrinsics
            assert 'databaseCallCount' in intrinsics

            assert intrinsics['databaseDuration'] == (database_all_duration +
                    datastore_all_duration)
            assert intrinsics['databaseCallCount'] == (database_all_call_count +
                    datastore_all_call_count)

        return result

    return _validate_database_duration

def validate_transaction_event_attributes(required_params={},
        forgone_params={}):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_event_attributes(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            event_data = instance.sampled_data_set
            # grab first transaction event in data set
            intrinsics, user_attributes, agent_attributes = event_data.samples[0]

            if required_params:
                for param in required_params['agent']:
                    assert param in agent_attributes
                for param in required_params['user']:
                    assert param in user_attributes
                for param in required_params['intrinsic']:
                    assert param in intrinsics

            if forgone_params:
                for param in forgone_params['agent']:
                    assert param not in agent_attributes
                for param in forgone_params['user']:
                    assert param not in user_attributes

        return result

    return _validate_transaction_event_attributes

def validate_non_transaction_error_event(required_intrinsics):
    """Validate error event data for a single error occuring outside of a
    transaction.
    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_exception')
    def _validate_non_transaction_error_event(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            event = instance._error_event_cache

            assert len(event) == 3 # [intrinsic, user, agent attributes]

            intrinsics = event[0]

            # The following attributes are all required, and also the only
            # intrinsic attributes that can be included in an error event
            # recorded outside of a transaction

            assert intrinsics['type'] == 'TransactionError'
            assert intrinsics['transactionName'] == None
            assert intrinsics['error.class'] == required_intrinsics['error.class']
            assert intrinsics['error.message'] == required_intrinsics['error.message']
            assert intrinsics['timestamp'] < time.time()

        return result

    return _validate_non_transaction_error_event

def validate_synthetics_transaction_trace(required_params={},
        forgone_params={}, should_exist=True):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_synthetics_transaction_trace(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)

            # Check that synthetics resource id is in TT header

            header = trace_data[0]
            header_key = 'synthetics_resource_id'

            if should_exist:
                assert header_key in required_params
                assert header[9] == required_params[header_key], ('name=%r, '
                            'header=%r' % (header_key, header))
            else:
                assert header[9] is None

            # Check that synthetics ids are in TT custom params

            pack_data = unpack_field(trace_data[0][4])
            tt_intrinsics = pack_data[0][4]['intrinsics']

            for name in required_params:
                assert name in tt_intrinsics, ('name=%r, '
                        'intrinsics=%r' % (name, tt_intrinsics))
                assert tt_intrinsics[name] == required_params[name], (
                        'name=%r, value=%r, intrinsics=%r' %
                        (name, required_params[name], intrinsics))

            for name in forgone_params:
                assert name not in tt_intrinsics, ('name=%r, '
                        'intrinsics=%r' % (name, tt_intrinsics))

        return result

    return _validate_synthetics_transaction_trace

def validate_tt_collector_json(required_params={},
        forgone_params={}, should_exist=True):
    '''make assertions based off the cross-agent spec on transaction traces'''

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_tt_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)

            trace = trace_data[0] #1st trace
            assert isinstance(trace[0], (int, float)) # start time (ms)
            assert isinstance(trace[1], (int, float)) # duration (ms)
            assert isinstance(trace[2], six.string_types) # transaction name
            assert isinstance(trace[3], six.string_types) # request url

            # trace details -- python agent always uses condensed trace array

            trace_details, string_table = unpack_field(trace[4])
            assert len(trace_details) == 5
            assert isinstance(trace_details[0], (int,float)) # start time (s)

            # the next two items should be empty dicts, old parameters stuff,
            # placeholders for now

            assert isinstance(trace_details[1], dict)
            assert len(trace_details[1]) == 0
            assert isinstance(trace_details[2], dict)
            assert len(trace_details[2]) == 0

            # root node in slot 3

            root_node = trace_details[3]
            assert isinstance(root_node[0], (int, float)) # entry timestamp
            assert isinstance(root_node[1], (int, float)) # exit timestamp
            assert root_node[2] == 'ROOT'
            assert isinstance(root_node[3], dict)
            assert len(root_node[3]) == 0 # spec shows empty (for root)
            children = root_node[4]
            assert isinstance(children, list)

            # there are two optional items at the end of trace segments,
            # class name that segment is in, and method name function is in;
            # Python agent does not use these (only Java does)

            # let's just test the first child
            trace_segment = children[0]
            assert isinstance(trace_segment[0], (int, float)) # entry timestamp
            assert isinstance(trace_segment[1], (int, float)) # exit timestamp
            assert isinstance(trace_segment[2], six.string_types) # scope
            assert isinstance(trace_segment[3], dict) # request params
            assert isinstance(trace_segment[4], list) # children

            attributes = trace_details[4]

            assert 'intrinsics' in attributes
            assert 'userAttributes' in attributes
            assert 'agentAttributes' in attributes

            assert isinstance(trace[5], six.string_types) #GUID
            assert trace[6] is None # reserved for future use
            assert trace[7] is False # deprecated force persist flag

             # x-ray session ID

            assert trace[8] is None or isinstance(trace[8], six.string_types)

            # Synthetics ID

            assert trace[9] is None or isinstance(trace[9], six.string_types)

            assert isinstance(string_table, list)
            for name in string_table:
                assert isinstance(name, six.string_types) # metric name

        return result

    return _validate_tt_collector_json

def validate_transaction_trace_attributes(required_params={},
        forgone_params={}, should_exist=True):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_trace_attributes(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)

            pack_data = unpack_field(trace_data[0][4])
            assert len(pack_data) == 2
            assert len(pack_data[0]) == 5
            parameters = pack_data[0][4]

            assert 'intrinsics' in parameters
            assert 'userAttributes' in parameters
            assert 'agentAttributes' in parameters

            check_attributes(parameters, required_params, forgone_params)

        return result

    return _validate_transaction_trace_attributes

def validate_transaction_error_trace_attributes(required_params={},
        forgone_params={}):
    """Check the error trace for attributes, expect only one error to be
    present in the transaction.
    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_error_trace(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            error_data = instance.error_data()

            # there should be only one error
            assert len(error_data) == 1
            traced_error = error_data[0]

            check_error_attributes(traced_error.parameters, required_params,
                    forgone_params, is_transaction=True)

        return result

    return _validate_transaction_error_trace

def check_error_attributes(parameters, required_params={}, forgone_params={},
        is_transaction=True):

    parameter_fields = ['userAttributes']
    if is_transaction:
        parameter_fields.extend(['stack_trace', 'agentAttributes',
                'intrinsics', 'request_uri'])

    for field in parameter_fields:
        assert field in parameters

    # we can remove this after agent attributes transition is all over
    assert 'parameter_groups' not in parameters
    assert 'custom_params' not in parameters
    assert 'request_params' not in parameters

    check_attributes(parameters, required_params, forgone_params)

def check_attributes(parameters, required_params={}, forgone_params={}):
    if required_params:
        for param in required_params['agent']:
            assert param in parameters['agentAttributes']

        for param in required_params['user']:
            assert param in parameters['userAttributes']

        for param in required_params['intrinsic']:
            assert param in parameters['intrinsics']

    if forgone_params:
        for param in forgone_params['agent']:
            assert param not in parameters['agentAttributes']

        for param in forgone_params['user']:
            assert param not in parameters['userAttributes']

def validate_error_trace_collector_json():
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_error_trace_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            errors = instance.error_data()

            # recreate what happens right before data is sent to the collector
            # in data_collector.py via ApplicationSession.send_errors
            agent_run_id = 666
            payload = (agent_run_id, errors)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            assert decoded_json[0] == agent_run_id
            err = decoded_json[1][0]
            assert len(err) == 5
            assert isinstance(err[0], (int, float))
            assert isinstance(err[1], six.string_types) # path
            assert isinstance(err[2], six.string_types) # error message
            assert isinstance(err[3], six.string_types) # exception name
            parameters = err[4]

            parameter_fields = ['userAttributes', 'stack_trace',
                    'agentAttributes', 'intrinsics', 'request_uri']

            for field in parameter_fields:
                assert field in parameters

    return _validate_error_trace_collector_json

def validate_transaction_event_collector_json():
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_event_collector_json(wrapped, instance, args,
            kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            samples = instance.sampled_data_set.samples

            # recreate what happens right before data is sent to the collector
            # in data_collector.py during the harvest via analytic_event_data
            agent_run_id = 666
            payload = (agent_run_id, samples)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            assert decoded_json[0] == agent_run_id

            # list of events

            events = decoded_json[1]

            for event in events:

                # event is an array containing intrinsics, user-attributes,
                # and agent-attributes

                assert len(event) == 3
                for d in event:
                    assert isinstance(d, dict)

        return result

    return _validate_transaction_event_collector_json


def validate_tt_parameters(required_params={}, forgone_params={}):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_tt_parameters(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)
            pack_data = unpack_field(trace_data[0][4])
            tt_intrinsics = pack_data[0][4]['intrinsics']

            for name in required_params:
                assert name in tt_intrinsics, ('name=%r, '
                        'intrinsics=%r' % (name, tt_intrinsics))
                assert tt_intrinsics[name] == required_params[name], (
                        'name=%r, value=%r, intrinsics=%r' %
                        (name, required_params[name], tt_intrinsics))

            for name in forgone_params:
                assert name not in tt_intrinsics, ('name=%r, '
                        'intrinsics=%r' % (name, tt_intrinsics))

        return result

    return _validate_tt_parameters

def validate_browser_attributes(required_params={}, forgone_params={}):
    @transient_function_wrapper('newrelic.api.web_transaction',
            'WebTransaction.browser_timing_footer')
    def _validate_browser_attributes(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise

        # pick out attributes from footer string_types

        footer_data = result.split('NREUM.info=')[1]
        footer_data = footer_data.split('</script>')[0]
        footer_data = json.loads(footer_data)

        if 'intrinsic' in required_params:
            for attr in required_params['intrinsic']:
                assert attr in footer_data

        if 'atts' in footer_data:
            obfuscation_key = instance._settings.license_key[:13]
            attributes = json_decode(deobfuscate(footer_data['atts'],
                    obfuscation_key))
        else:

            # if there are no user or agent attributes, there will be no dict
            # for them in the browser data

            attributes = None

        if 'user' in required_params:
            for attr in required_params['user']:
                assert attr in attributes['u']

        if 'agent' in required_params:
            for attr in required_params['agent']:
                assert attr in attributes['a']

        if 'user' in forgone_params:
            if attributes:
                if 'u' in attributes:
                    for attr in forgone_params['user']:
                        assert attr not in attributes['u']

        if 'agent' in forgone_params:
            if attributes:
                if 'a' in attributes:
                    for attr in forgone_params['agent']:
                        assert attr not in attributes['a']

        return result

    return _validate_browser_attributes

def validate_request_params_omitted():
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_request_params(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for attr in transaction.agent_attributes:
            assert not attr.name.startswith('request.parameters')

        return wrapped(*args, **kwargs)

    return _validate_request_params

def validate_attributes(attr_type, required_attr_names=[],
        forgone_attr_names=[]):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_attributes(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        if attr_type == 'intrinsic':
            attributes = transaction.trace_intrinsics
            attribute_names = attributes.keys()
        elif attr_type == 'agent':
            attributes = transaction.agent_attributes
            attribute_names = [a.name for a in attributes]
        elif attr_type == 'user':
            attributes = transaction.user_attributes
            attribute_names = [a.name for a in attributes]

        for name in required_attr_names:
            assert name in attribute_names, ('name=%r,'
                    'attributes=%r' % (name, attributes))

        for name in forgone_attr_names:
            assert name not in attribute_names, ('name=%r,'
                    ' attributes=%r' % (name, attributes))

        return wrapped(*args, **kwargs)

    return _validate_attributes

def validate_attributes_complete(attr_type, required_attrs=[],
        forgone_attrs=[]):

    # This differs from `validate_attributes` in that all fields of
    # Attribute must match (name, value, and destinations), not just
    # name. It's a more thorough test, but it's more of a pain to set
    # up, since you have to pass lists of Attributes to required_attrs
    # and forgone_attrs. For required destinations, the attribute will
    # match if at least the required destinations are present. For
    # forgone attributes the test will fail if any of the destinations
    # provided in the forgone attribute are found.
    #
    # Args:
    #
    #       attr_type: 'intrinsic' or 'agent' or 'user'
    #       required_attrs: List of Attributes that must be present.
    #       forgone_attrs: List of Attributes that must NOT be present.
    #
    # Note:
    #
    # The 'intrinsics' come from `transaction.trace_intrinsics`.

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_attributes_complete(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        attribute_filter = transaction.settings.attribute_filter

        if attr_type == 'intrinsic':

            # Intrinsics are stored as a dict, so for consistency's sake
            # in this test, we convert them to Attributes.

            items = transaction.trace_intrinsics
            attributes = create_attributes(items,
                    DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER,
                    attribute_filter)

        elif attr_type == 'agent':
            attributes = transaction.agent_attributes

        elif attr_type == 'user':
            attributes = transaction.user_attributes

        def _find_match(a, attributes):
            # Match by name and value. Ignore destination.
            return next((match for match in attributes if
                    match.name == a.name and
                    match.value == a.value), None)

        # Check that there is a name/value match, and that the destinations
        # for the matched attribute include the ones in required.

        for required in required_attrs:
            match = _find_match(required, attributes)
            assert match, ('required=%r, attributes=%r' % (required,
                    attributes))

            result_dest = required.destinations & match.destinations
            assert result_dest == required.destinations, ('required=%r, '
                    'attributes=%r' % (required, attributes))

        # Check that the name and value are NOT going to ANY of the
        # destinations provided as forgone, either because there is no
        # name/value match, or because there is a name/value match, but
        # the destinations do not include the ones in forgone.

        for forgone in forgone_attrs:
            match = _find_match(forgone, attributes)

            if match:
                result_dest = forgone.destinations & match.destinations
                assert result_dest == 0, ('forgone=%r, attributes=%r' %
                        (forgone, attributes))

        return wrapped(*args, **kwargs)

    return _validate_attributes_complete

def validate_database_trace_inputs(sql_parameters_type):

    @transient_function_wrapper('newrelic.api.database_trace',
            'DatabaseTrace.__init__')
    @catch_background_exceptions
    def _validate_database_trace_inputs(wrapped, instance, args, kwargs):
        def _bind_params(transaction, sql, dbapi2_module=None,
                connect_params=None, cursor_params=None, sql_parameters=None,
                execute_params=None):
            return (transaction, sql, dbapi2_module, connect_params,
                    cursor_params, sql_parameters, execute_params)

        (transaction, sql, dbapi2_module, connect_params, cursor_params,
                sql_parameters, execute_params) = _bind_params(*args, **kwargs)

        assert hasattr(dbapi2_module, 'connect')

        assert connect_params is None or isinstance(connect_params, tuple)

        if connect_params is not None:
            assert len(connect_params) == 2
            assert isinstance(connect_params[0], tuple)
            assert isinstance(connect_params[1], dict)

        assert cursor_params is None or isinstance(cursor_params, tuple)

        if cursor_params is not None:
            assert len(cursor_params) == 2
            assert isinstance(cursor_params[0], tuple)
            assert isinstance(cursor_params[1], dict)

        assert sql_parameters is None or isinstance(
                sql_parameters, sql_parameters_type)

        if execute_params is not None:
            assert len(execute_params) == 2
            assert isinstance(execute_params[0], tuple)
            assert isinstance(execute_params[1], dict)

        return wrapped(*args, **kwargs)

    return _validate_database_trace_inputs

def validate_transaction_event_sample_data(name, capture_attributes={},
        database_call_count=0, external_call_count=0, queue_duration=False):
    """This test depends on values in the test application from
    agent_features/test_analytics.py, and is only meant to be run as a
    validation with those tests.
    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'SampledDataSet.add')
    def _validate_transaction_event_sample_data(wrapped, instance, args, kwargs):
        def _bind_params(sample, *args, **kwargs):
            return sample

        sample = _bind_params(*args, **kwargs)

        assert isinstance(sample, list)
        assert len(sample) == 3

        intrinsics, user_attributes, agent_attributes = sample

        assert intrinsics['type'] == 'Transaction'
        assert intrinsics['name'] == name

        _validate_event_attributes(intrinsics,
                                   user_attributes,
                                   agent_attributes,
                                   capture_attributes,
                                   database_call_count,
                                   external_call_count,
                                   queue_duration)

        return wrapped(*args, **kwargs)

    return _validate_transaction_event_sample_data

def validate_error_event_sample_data(required_attrs, capture_attributes={},
        database_call_count=0, external_call_count=0, queue_duration=False):
    """This test depends on values in the test application from
    agent_features/test_analytics.py, and is only meant to be run as a
    validation with those tests.
    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_error_event_sample_data(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            def _bind_params(transaction, *args, **kwargs):
                return transaction

            transaction = _bind_params(*args, **kwargs)

            error_events = transaction.error_events(instance.stats_table)
            sample = error_events[0]

            assert isinstance(sample, list)
            assert len(sample) == 3

            intrinsics, user_attributes, agent_attributes = sample

            # These intrinsics should always be present

            assert intrinsics['type'] == 'TransactionError'
            assert intrinsics['transactionName'] == required_attrs['transactionName']
            assert intrinsics['error.class'] == required_attrs['error.class']
            assert intrinsics['error.message'] == required_attrs['error.message']

            _validate_event_attributes(intrinsics,
                                       user_attributes,
                                       agent_attributes,
                                       capture_attributes,
                                       database_call_count,
                                       external_call_count,
                                       queue_duration)

        return wrapped(*args, **kwargs)

    return _validate_error_event_sample_data

def _validate_event_attributes(intrinsics, user_attributes, agent_attributes,
            capture_attributes, database_call_count, external_call_count,
            queue_duration):

    assert intrinsics['timestamp'] >= 0.0
    assert intrinsics['duration'] >= 0.0

    assert 'memcacheDuration' not in intrinsics

    if capture_attributes:
        for attr, value in capture_attributes.items():
            assert user_attributes[attr] == value
    else:
        assert user_attributes == {}

    if database_call_count:
        assert intrinsics['databaseDuration'] > 0
        assert intrinsics['databaseCallCount'] == database_call_count
    else:
        assert 'databaseDuration' not in intrinsics
        assert 'databaseCallCount' not in intrinsics

    if external_call_count:
        assert intrinsics['externalDuration'] > 0
        assert intrinsics['externalCallCount'] == external_call_count
    else:
        assert 'externalDuration' not in intrinsics
        assert 'externalCallCount' not in intrinsics

    if queue_duration:
        assert intrinsics['queueDuration'] > 0
    else:
        assert 'queueDuration' not in intrinsics


def override_application_name(app_name):
    # The argument here cannot be named 'name', or else it triggers
    # a PyPy bug. Hence, we use 'app_name' instead.

    class Application(ObjectProxy):
        @property
        def name(self):
            return app_name

    @transient_function_wrapper('newrelic.api.transaction',
            'Transaction.__init__')
    def _override_application_name(wrapped, instance, args, kwargs):
        def _bind_params(application, *args, **kwargs):
            return application, args, kwargs

        application, _args, _kwargs = _bind_params(*args, **kwargs)

        application = Application(application)

        return wrapped(application, *_args, **_kwargs)

    return _override_application_name

def override_application_settings(overrides):
    @function_wrapper
    def _override_application_settings(wrapped, instance, args, kwargs):
        try:
            # This is a bit horrible as the one settings object, has
            # references from a number of different places. We have to
            # create a copy, overlay the temporary settings and then
            # when done clear the top level settings object and rebuild
            # it when done.

            original_settings = application_settings()
            backup = dict(original_settings)
            for name, value in overrides.items():
                apply_config_setting(original_settings, name, value)

            # should also update the attribute filter since it is affected
            # by application settings

            original_filter = original_settings.attribute_filter
            flat_settings = flatten_settings(original_settings)
            original_settings.attribute_filter = AttributeFilter(flat_settings)

            return wrapped(*args, **kwargs)
        finally:
            original_settings.__dict__.clear()
            for name, value in backup.items():
                apply_config_setting(original_settings, name, value)
            original_settings.attribute_filter = original_filter

    return _override_application_settings

def override_generic_settings(settings_object, overrides):
    @function_wrapper
    def _override_generic_settings(wrapped, instance, args, kwargs):
        try:
            # This is a bit horrible as in some cases a settings object may
            # have references from a number of different places. We have
            # to create a copy, overlay the temporary settings and then
            # when done clear the top level settings object and rebuild
            # it when done.

            original = settings_object

            backup = dict(original)
            for name, value in overrides.items():
                apply_config_setting(original, name, value)
            return wrapped(*args, **kwargs)
        finally:
            original.__dict__.clear()
            for name, value in backup.items():
                apply_config_setting(original, name, value)

    return _override_generic_settings

def override_ignore_status_codes(status_codes):
    @function_wrapper
    def _override_ignore_status_codes(wrapped, instance, args, kwargs):
        try:
            # This is a bit horrible as ignore_status_codes is only
            # used direct from the global settings and not the
            # application settings. We therefore need to patch the
            # global settings directly.

            settings = global_settings()
            original = settings.error_collector.ignore_status_codes
            settings.error_collector.ignore_status_codes = status_codes
            return wrapped(*args, **kwargs)
        finally:
            settings.error_collector.ignore_status_codes = original

    return _override_ignore_status_codes

def code_coverage_fixture(source=['newrelic']):
    @pytest.fixture(scope='session')
    def _code_coverage_fixture(request):
        if not source:
            return

        if os.environ.get('TDDIUM') is not None:
            return

        from coverage import coverage

        env_directory = os.environ.get('TOX_ENVDIR', None)

        if env_directory is not None:
            coverage_directory = os.path.join(env_directory, 'htmlcov')
        else:
            coverage_directory = 'htmlcov'

        def finalize():
            cov.stop()
            cov.html_report(directory=coverage_directory)

        request.addfinalizer(finalize)

        cov = coverage(source=source)
        cov.start()

    return _code_coverage_fixture

def core_application_stats_engine(app_name=None):
    """Return the StatsEngine object from the core application object.

    Useful when validating items added outside of a transaction, since
    monkey-patching StatsEngine.record_transaction() doesn't work in
    those situations.

    """

    api_application = application(app_name)
    api_name = api_application.name
    core_application = api_application._agent.application(api_name)
    return core_application._stats_engine

def core_application_stats_engine_error(error_type, app_name=None):
    """Return a single error with the type of error_type, or None.

    In the core application StatsEngine, look in StatsEngine.error_data()
    and return the first error with the type of error_type. If none found,
    return None.

    Useful for verifying that application.record_exception() works, since
    the error is saved outside of a transaction. Must use a unique error
    type per test in a single test file, so that it returns the error you
    expect. (If you have 2 tests that record the same type of exception, then
    StatsEngine.error_data() will contain 2 errors with the same type, but
    this function will always return the first one it finds.)

    """

    stats = core_application_stats_engine(app_name)
    errors = stats.error_data()
    return next((e for e in errors if e.type == error_type), None)

def error_is_saved(error, app_name=None):
    """Return True, if an error of a particular type has already been saved.

    Before calling application.record_exception() in a test, it's good to
    check if that type of error has already been saved, so you know that
    there will only be a single example of a type of Error in error_data()
    when you verify that the exception was recorded correctly.

    Example usage:

        try:
            assert not error_is_saved(ErrorOne)
            raise ErrorOne('error one message')
        except ErrorOne:
            application_instance = application()
            application_instance.record_exception()

        my_error = core_application_stats_engine_error(_error_one_name)
        assert my_error.message == 'error one message'

    """

    error_name = callable_name(error)
    stats = core_application_stats_engine(app_name)
    errors = stats.error_data()
    return error_name in [e.type for e in errors if e.type == error_name]
