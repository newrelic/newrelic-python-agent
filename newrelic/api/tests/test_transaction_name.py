import unittest
import time

import newrelic.tests.test_cases

import newrelic.api.web_transaction
import newrelic.api.transaction_name

@newrelic.api.transaction_name.transaction_name()
def function_1():
    pass

@newrelic.api.transaction_name.transaction_name(
        name='literal:function_2', group='literal:group_2')
def function_2():
    pass

@newrelic.api.transaction_name.transaction_name(
        name=lambda: 'dynamic:function_3', group=lambda: 'dynamic:group_3')
def function_3():
    pass

@newrelic.api.transaction_name.transaction_name(priority=1)
def function_4():
    pass

@newrelic.api.transaction_name.transaction_name(priority=3)
def function_5():
    pass

@newrelic.api.transaction_name.transaction_name(priority=2)
def function_6():
    pass

def function_7():
    pass

newrelic.api.transaction_name.wrap_transaction_name(__name__, 'function_7')

@newrelic.api.web_transaction.wsgi_application()
def handler(environ, start_response):
    status = '200 OK'
    output = 'Hello World!'

    names = environ['FUNCTIONS'].split(',')
    for name in names:
        globals()[name]()

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

def start_response(status, headers): pass

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_transaction_name_defaults(self):
        environ = {}
        environ['REQUEST_URI'] = '/test_transaction_name_defaults'
        environ['FUNCTIONS'] = 'function_1'
        handler(environ, start_response).close()

    def test_transaction_name_strings(self):
        environ = {}
        environ['REQUEST_URI'] = '/test_transaction_name_strings'
        environ['FUNCTIONS'] = 'function_2'
        handler(environ, start_response).close()

    def test_transaction_name_lambdas(self):
        environ = {}
        environ['REQUEST_URI'] = '/test_transaction_name_lambdas'
        environ['FUNCTIONS'] = 'function_3'
        handler(environ, start_response).close()

    def test_transaction_name_priority(self):
        environ = {}
        environ['REQUEST_URI'] = '/test_transaction_name_priority'
        environ['FUNCTIONS'] = 'function_4,function_5,function_6'
        handler(environ, start_response).close()

    def test_transaction_name_wrap(self):
        environ = {}
        environ['REQUEST_URI'] = '/test_transaction_name_wrap'
        environ['FUNCTIONS'] = 'function_7'
        handler(environ, start_response).close()

if __name__ == '__main__':
    unittest.main()
