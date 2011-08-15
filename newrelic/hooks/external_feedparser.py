import sys
import types

import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.external_trace

class capture_external_trace(object):
    def __init__(self, wrapped):
        self.__wrapped = wrapped
    def __call__(self, url):
        if url.split(':')[0].lower() in ['http', 'https', 'ftp']:
            current_transaction = newrelic.api.transaction.transaction()
            if current_transaction:
                trace = newrelic.api.external_trace.ExternalTrace(
                        current_transaction, 'feedparser', url)
                context_manager = trace.__enter__()
                try:
                    result = self.__wrapped(url)
                except:
                    context_manager.__exit__(*sys.exc_info())
                    raise
                context_manager.__exit__(None, None, None)
                return result
            else:
                return self.__wrapped(url)
        else:
            return self.__wrapped(url)
    def __getattr__(self, name):
       return getattr(self.__wrapped, name)

def instrument(module):
    newrelic.api.object_wrapper.wrap_object(
            module, 'parse', capture_external_trace)
