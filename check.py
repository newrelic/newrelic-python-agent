import os
import sys
import time

import logging

if len(sys.argv) != 2:
    print >> sys.stderr, 'Usage: python check.py newrelic.ini'

from newrelic.api.settings import *
from newrelic.api.function_trace import *
from newrelic.api.error_trace import *
from newrelic.api.web_transaction import *
from newrelic.api.background_task import *
from newrelic.api.application import *

from newrelic.config import *
from newrelic.agent import *

import newrelic.core.log_file

_settings = settings()

_settings.log_file = '/tmp/python-agent-test.log'
_settings.log_level = logging.DEBUG

try:
    os.unlink(_settings.log_file)
except:
    pass

newrelic.core.log_file.initialize()

_logger = logging.getLogger('newrelic')
_logger.debug('Starting agent validation.')

initialize(sys.argv[1], ignore_errors=False,
           log_file=_settings.log_file, log_level=_settings.log_level)

_settings.app_name = 'Python Agent Test'
_settings.transaction_tracer.transaction_threshold = 0

@function_trace()
def _function1():
    time.sleep(0.1)

@function_trace()
def _function2():
    for i in range(10):
        _function1()

@error_trace()
@function_trace()
def _function3():
    raise RuntimeError('error')
 
@wsgi_application()
def _wsgi_application(environ, start_response):
    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    for i in range(10):
        _function1()

    _function2()

    try:
        _function3()
    except:
        pass

    return [output]

@background_task()
def _background_task():
    for i in range(10):
        _function1()

    _function2()

    try:
        _function3()
    except:
        pass

def _start_response(*args):
    pass


print
print 'Running Python agent test.'
print
print 'Look for data in the New Relic UI under the application:'
print
print '  %s' % _settings.app_name
print
print 'If data is not getting through to the UI after 5 minutes'
print 'then check the log file:'
print
print '  %s' % _settings.log_file
print
print 'for debugging information. Supply the log file to New Relic'
print 'support if requesting help with resolving any issues with'
print 'the test not reporting data to the New Relic UI.'
print

_logger.debug('Register test application.')

_application = application()

#_status = _application.activate(wait=True)
_status = _application.activate()

"""
if not _application.running:
    raise RuntimeError('Unable to register application for test, '
                       'check that the local daemon process is running '
                       'and is configured properly.')
"""

_logger.debug('Run the validation test.')

_environ = { 'SCRIPT_NAME': '', 'PATH_INFO': '/test' }

_iterable = _wsgi_application(_environ, _start_response)
_iterable.close()

time.sleep(5.0)

_iterable = _wsgi_application(_environ, _start_response)
_iterable.close()

#_background_task()

