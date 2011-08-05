import os
import sys
import unittest
import time

# Need to enable code into full on pure Python mode. Need this for now
# as by default runs in C code module. The code name is 'julunggul'
# which is Australia aboriginal word for rainbow snake goddess. :-)

os.environ['NEWRELIC_AGENT_MODE'] = 'julunggul'

import newrelic.core.agent

import newrelic.api.settings
import newrelic.api.log_file

import newrelic.api.transaction

import newrelic.api.web_transaction

import newrelic.api.database_trace
import newrelic.api.external_trace
import newrelic.api.function_trace
import newrelic.api.memcache_trace

import newrelic.api.error_trace
import newrelic.api.name_transaction

import newrelic.agent

# Hardwire settings for test script rather than agent configuration file
# as is easier then work with. We override transaction and database
# trace thresholds so everything is collected. To that the extent that
# old logging system is still used in the code, possibly nothing at this
# point, anything will end up in log file in same directory as this
# script where name is the files name with '.log' appended.

settings = newrelic.api.settings.settings()

settings.host = 'staging-collector.newrelic.com'
settings.port = 80
settings.license_key = 'd67afc830dab717fd163bfcb0b8b88423e9a1a3b'

settings.app_name = 'Python Unit Test1'

settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG

settings.transaction_tracer.transaction_threshold = 0
settings.transaction_tracer.stack_trace_threshold = 0

# The WSGI application and test functions. Just use decorators to apply
# wrappers as easier than trying to use automated instrumentation.

@newrelic.api.error_trace.error_trace()
def my_error():
    raise RuntimeError('error-1')

@newrelic.api.database_trace.database_trace(sql='select * from cat')
def my_database():
    time.sleep(0.1)

@newrelic.api.external_trace.external_trace(library='test', url='http://x/y')
def my_external():
    time.sleep(0.1)

@newrelic.api.memcache_trace.memcache_trace(command='get')
def my_memcache():
    time.sleep(0.1)

@newrelic.api.function_trace.function_trace()
def my_function_1():
    time.sleep(0.1)
    try:
        my_error()
    except:
        pass
    time.sleep(0.1)

@newrelic.api.function_trace.function_trace()
def my_function_2():
    time.sleep(0.1)
    my_database()
    my_external()
    my_memcache()
    time.sleep(0.1)

@newrelic.api.function_trace.function_trace()
def my_function_3():
    time.sleep(0.1)
    transaction = newrelic.api.transaction.transaction()
    if transaction and transaction.active:
        transaction.application.record_metric('metric-int', 1)
        transaction.application.record_metric('metric-float', 1.0)
        transaction.custom_parameters['custom-string'] = '1'
        transaction.custom_parameters['custom-int'] = 1
        transaction.custom_parameters['custom-float'] = 1.0
        transaction.custom_parameters['custom-list'] = [1.0]
        try:
            raise RuntimeError('error-2')
        except:
            params = {}
            params['error-string'] = '1'
            params['error-int'] = 1
            params['error-float'] = 1.0
            params['error-list'] = [1.0]
            transaction.notice_error(*sys.exc_info(), params=params)
    time.sleep(0.1)

@newrelic.api.function_trace.function_trace()
def my_function():
    my_function_1()
    for i in range(4):
      my_function_2()
    my_function_3()

@newrelic.api.web_transaction.wsgi_application()
def application(environ, start_response):

    my_function()

    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

class TransactionTests(unittest.TestCase):

    # Note that you can only have a single test in this file
    # as code makes assumption that test is first to run and
    # nothing has been run before.

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

    def test_transaction(self):

        # Initialise higher level instrumentation layers. Not
        # that they will be use in this test for now.

        newrelic.agent.initialize()

	# Want to force agent initialisation and connection so
	# we know that data will actually get through to core
	# and not lost because application not activated. We
        # really need a way of saying to the agent that want to
        # wait, either indefinitely or for a set period, when
        # activating the application. Will make this easier.

        agent = newrelic.core.agent.agent()

        name = settings.app_name
        application_settings = agent.application_settings(name)
        self.assertEqual(application_settings, None)

        agent.activate_application(name)

        for i in range(10):
            application_settings = agent.application_settings(name)
            if application_settings:
                break
            time.sleep(0.5)

        # If this fails it means we weren't able to establish
        # a connection and activate the named application.

        self.assertNotEqual(application_settings, None)

        print 'SETTINGS', application_settings

        def start_response(status, headers): pass

        environ = { "REQUEST_URI": "/request_uri?key=value" }
        application(environ, start_response).close()

if __name__ == '__main__':
    unittest.main()
