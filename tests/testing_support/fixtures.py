import pytest
import logging
import os
import sys

from newrelic.agent import (initialize, register_application,
        global_settings, shutdown_agent, application as application_instance)

from newrelic.core.config import apply_config_setting

def collector_agent_registration_fixture(app_name=None, default_settings={}):
    @pytest.fixture(scope='session')
    def _collector_agent_registration_fixture(request):
        settings = global_settings()

        settings.app_name = 'Python Agent Test'
        settings.license_key = '84325f47e9dec80613e262be4236088a9983d501'
        settings.host = 'staging-collector.newrelic.com'

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

def code_coverage_fixture(source=['newrelic']):
    @pytest.fixture(scope='session')
    def _code_coverage_fixture(request):
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
