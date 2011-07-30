import os

import _newrelic

import newrelic.api.object_wrapper

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

WebTransaction = _newrelic.WebTransaction
WSGIApplicationWrapper = _newrelic.WSGIApplicationWrapper

def wsgi_application(application=None):
    def decorator(wrapped):
        return WSGIApplicationWrapper(wrapped, application)
    return decorator

def wrap_wsgi_application(module, object_path, application=None):
    newrelic.api.object_wrapper.wrap_object(module, object_path,
            WSGIApplicationWrapper, (application, ))

if not _agent_mode in ('ungud', 'julunggul'):
    wsgi_application = _newrelic.wsgi_application
    wrap_wsgi_application = _newrelic.wrap_wsgi_application
