import pytest
import logging
import os
import sys

from newrelic.agent import (initialize, register_application,
        global_settings, shutdown_agent, application as application_instance,
        transient_function_wrapper)

from newrelic.core.config import (apply_config_setting,
        create_settings_snapshot)

def collector_agent_registration_fixture(app_name=None, default_settings={}):
    @pytest.fixture(scope='session')
    def _collector_agent_registration_fixture(request):
        settings = global_settings()

        settings.app_name = 'Python Agent Test'

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

        settings.startup_timeout = 20.0
        settings.shutdown_timeout = 20.0

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

        application = register_application()

        def finalize():
            shutdown_agent()

        request.addfinalizer(finalize)

        return application

    return _collector_agent_registration_fixture

@pytest.fixture(scope='function')
def collector_available_fixture(request):
    application = application_instance()
    assert application.active

def validate_transaction_metrics(name, group='Function',
        background_task=False, scoped_metrics=[], rollup_metrics=[]):

    if background_task:
        transaction_metric = 'OtherTransaction/%s/%s' % (group, name)
    else:
        transaction_metric = 'WebTransaction/%s/%s' % (group, name)

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_metrics(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            metrics = instance.stats_table

            assert metrics[(transaction_metric, '')].call_count == 1

            for scoped_name, scoped_count in scoped_metrics:
                assert metrics[(scoped_name,
                    transaction_metric)].call_count == scoped_count

            for rollup_name, rollup_count in rollup_metrics:
                assert metrics[(rollup_name, '')].call_count == rollup_count

        return result

    return _validate_transaction_metrics

def validate_custom_parameters(custom_params=[]):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_custom_parameters(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for name, value in custom_params:
            assert transaction.custom_params[name] == value

        return wrapped(*args, **kwargs)

    return _validate_custom_parameters

def validate_database_trace_inputs(execute_params_type):
    @transient_function_wrapper('newrelic.api.database_trace',
            'DatabaseTrace.__init__')
    def _validate_database_trace_inputs(wrapped, instance, args, kwargs):
        def _bind_params(transaction, sql, dbapi2_module=None,
                connect_params=None, cursor_params=None, execute_params=None):
            return (transaction, sql, dbapi2_module, connect_params,
                    cursor_params, execute_params)

        (transaction, sql, dbapi2_module, connect_params,
                cursor_params, execute_params) = _bind_params(*args, **kwargs)

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

        assert execute_params is None or isinstance(
                execute_params, execute_params_type)

        return wrapped(*args, **kwargs)

    return _validate_database_trace_inputs

def override_application_settings(settings):
    @transient_function_wrapper('newrelic.core.agent',
            'Agent.application_settings')
    def _override_application_settings(wrapped, instance, args, kwargs):
        return create_settings_snapshot(settings, wrapped(*args, **kwargs))

    return _override_application_settings

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
