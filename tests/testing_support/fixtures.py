import pytest
import logging
import os
import sys
import pwd
import threading
import time

from newrelic.packages import six

from newrelic.agent import (initialize, register_application,
        global_settings, shutdown_agent, application as application_instance,
        transient_function_wrapper, function_wrapper, application_settings,
        wrap_function_wrapper)

from newrelic.common.encoding_utils import unpack_field

from newrelic.core.config import (apply_config_setting,
        create_settings_snapshot)
from newrelic.core.database_utils import SQLConnections

from newrelic.network.addresses import proxy_details
from newrelic.packages import requests

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

def collector_agent_registration_fixture(app_name=None, default_settings={}):
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

        if not use_fake_collector:
            try:
                _logger.debug("Record deployment marker at %s" % url)
                r = requests.post(url, proxies=proxies, headers=headers,
                        timeout=timeout, data=data)
            except Exception:
                _logger.exception("Unable to record deployment marker.")
                pass

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

        for name, value in required_params:
            assert name in transaction.custom_params, ('name=%r, '
                    'params=%r' % (name, transaction.custom_params))
            assert transaction.custom_params[name] == value, (
                    'name=%r, value=%r, params=%r' % (name, value,
                    transaction.custom_params))

        for name, value in forgone_params:
            assert name not in transaction.custom_params, ('name=%r, '
                    'params=%r' % (name, transaction.custom_params))

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
                assert len(event) == 2

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
            header_key = 'nr.synthetics_resource_id'

            if should_exist:
                assert header_key in required_params
                assert header[9] == required_params[header_key], ('name=%r, '
                            'header=%r' % (header_key, header))
            else:
                assert header[9] is None

            # Check that synthetics ids are in TT custom params

            pack_data = unpack_field(trace_data[0][4])
            tt_custom_params = pack_data[0][2]

            for name in required_params:
                assert name in tt_custom_params, ('name=%r, '
                        'custom_params=%r' % (name, tt_custom_params))
                assert tt_custom_params[name] == required_params[name], (
                        'name=%r, value=%r, custom_params=%r' %
                        (name, required_params[name], custom_params))

            for name in forgone_params:
                assert name not in tt_custom_params, ('name=%r, '
                        'custom_params=%r' % (name, tt_custom_params))

        return result

    return _validate_synthetics_transaction_trace

def validate_request_params(required_params=[], forgone_params=[]):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_request_params(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for name, value in required_params:
            assert name in transaction.request_params, ('name=%r, '
                    'params=%r' % (name, transaction.request_params))
            assert transaction.request_params[name] == value, (
                    'name=%r, value=%r, params=%r' % (name, value,
                    transaction.request_params))

        for name, value in forgone_params:
            assert name not in transaction.request_params, ('name=%r, '
                    'params=%r' % (name, transaction.request_params))

        return wrapped(*args, **kwargs)

    return _validate_request_params

def validate_parameter_groups(group, required_params=[], forgone_params=[]):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_parameter_groups(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for name, value in required_params:
            assert name in transaction.parameter_groups[group], ('name=%r, '
                    'params=%r' % (name, transaction.parameter_groups[group]))
            assert transaction.parameter_groups[group][name] == value, (
                    'name=%r, value=%r, params=%r' % (name, value,
                    transaction.parameter_groups[group]))

        for name, value in forgone_params:
            assert name not in transaction.parameter_groups[group], ('name=%r,'
                    ' params=%r' % (name, transaction.parameter_groups[group]))

        return wrapped(*args, **kwargs)

    return _validate_parameter_groups

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

def override_application_settings(overrides):
    @function_wrapper
    def _override_application_settings(wrapped, instance, args, kwargs):
        try:
            # This is a bit horrible as the one settings object, has
            # references from a number of different places. We have to
            # create a copy, overlay the temporary settings and then
            # when done clear the top level settings object and rebuild
            # it when done.

            original = application_settings()
            backup = dict(original)
            for name, value in overrides.items():
                apply_config_setting(original, name, value)
            return wrapped(*args, **kwargs)
        finally:
            original.__dict__.clear()
            for name, value in backup.items():
                apply_config_setting(original, name, value)

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
