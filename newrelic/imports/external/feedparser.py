import sys
import types

from newrelic.agent import (transaction, wrap_object, ExternalTrace)

class capture_external_trace(object):
    def __init__(self, wrapped):
        self.__wrapped__ = wrapped
    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)
    def __call__(self, url):
        if url.split(':')[0].lower() in ['http', 'https', 'ftp']:
            current_transaction = transaction()
            if current_transaction:
                trace = ExternalTrace(current_transaction, 'feedparser', url)
                try:
                    context_manager = trace.__enter__()
                    return self.__wrapped__(url)
                except:
                    context_manager.__exit__(*sys.exc_info())
                    raise
                finally:
                    context_manager.__exit__(None, None, None)
            else:
                return self.__wrapped__(url)
        else:
            return self.__wrapped__(url)

def instrument(module):
    wrap_object(module, 'parse', capture_external_trace)
