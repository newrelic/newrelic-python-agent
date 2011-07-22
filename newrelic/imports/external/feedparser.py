import sys
import types

from newrelic.agent import (transaction, wrap_object, ExternalTrace,
        ObjectWrapper)

class capture_external_trace(ObjectWrapper):
    def __call__(self, url):
        if url.split(':')[0].lower() in ['http', 'https', 'ftp']:
            current_transaction = transaction()
            if current_transaction:
                trace = ExternalTrace(current_transaction, 'feedparser', url)
                try:
                    context_manager = trace.__enter__()
                    return self.__next_object__(url)
                except:
                    context_manager.__exit__(*sys.exc_info())
                    raise
                else:
                    context_manager.__exit__(None, None, None)
            else:
                return self.__next_object__(url)
        else:
            return self.__next_object__(url)

def instrument(module):
    wrap_object(module, 'parse', capture_external_trace)
