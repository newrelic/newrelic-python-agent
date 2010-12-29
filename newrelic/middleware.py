# vi: set sw=4 expandtab :

import threading
import sys

# Use thread local storage to track the current transaction for
# the executing thread. Storage is implemented as a stack just
# in case some valid reason arises for nesting transactions.

_context = threading.local()

def current_transaction():
    try:
        return _context.transactions[-1]
    except IndexError:
        raise RuntimeError('no active transaction')

def _push_transaction(transaction):
    try:
        _context.transactions.append(transaction)
    except AttributeError:
        _context.transactions = [transaction]

def _pop_transaction(transaction=None):
    current = _context.transactions.pop()
    if not transaction and transaction != current:
        raise RuntimeError('not the current transaction')

# Provide a WSGI middleware wrapper for initiating a web
# transaction for each request and ensuring that timing is
# started and stopped appropriately. For WSGI compliant case the
# latter is quite tricky as need to attach it to when the
# 'close()' method of any generator returned by a WSGI
# application is called. Only way to do this is to wrap response
# from the WSGI application with a generator with it having a
# 'close()' method which in turn executes the wrapped generators
# 'close()' method when it exists and then executing and
# finalisation. Doing this defeats any optimisations possible
# through using 'wsgi.file_wrapper'. For mod_wsgi case rely on a
# specific back door in mod_wsgi which allows extraction of file
# object from 'wsgi.file_wrapper' instance. We then rewrap the
# file object using new custom derived instance of the type
# 'wsgi.file_wrapper'. The 'close()' method of derived file
# wrapper the performs the required cleanup. This optimisation
# will only work for mod_wsgi 4.0+. Technically though it could
# work for any WSGI hosting system that satisfies criteria of
# 'wsgi.file_wrapper' being the type object for the wrapper and
# and instance of the type having attributes 'filelike' and
# 'blksize'.

def _ExitFileWrapper(transaction, generator):

    class _ExitFileWrapper(type(generator)):
        def close(self):
            try:
                super(_ExitFileWrapper, self).close()
            except:
                transaction.__exit__(*sys.exc_info())
                raise
            else:
                transaction.__exit__(None, None, None)
            finally:
                _context.transactions.pop()

    return _ExitFileWrapper(generator.filelike, generator.blksize)

class _ExitGenerator:

    def __init__(self, transaction, generator):
        self.__transaction = transaction
        self.__generator = generator

    def __iter__(self):
        for item in self.__generator:
            yield item

    def close(self):
        try:
            if hasattr(self.__generator, 'close'):
                self.__generator.close()
        except:
            self.__transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.__transaction.__exit__(None, None, None)
        finally:
            _context.transactions.pop()

class WebTransaction:

    def __init__(self, application, callable):
        self.__application = application
        self.__callable = callable

    def __call__(self, environ, start_response):
        transaction = self.__application.web_transaction(environ)

        _push_transaction(transaction)
        transaction.__enter__()

        def _start_response(status, response_headers, exc_info=None):
            transaction.response_code = int(status.split(' ')[0])
            return start_response(status, response_headers, exc_info)

        try:
            result = self.__callable(environ, _start_response)
        except:
            transaction.__exit__(*sys.exc_info())
            _pop_transaction(transaction)
            raise

        if type(result) == environ.get('wsgi.file_wrapper', None) and \
                hasattr(result, 'filelike') and hasattr(result, 'blksize'):
            return _ExitFileWrapper(transaction, result)
        else:
            return _ExitGenerator(transaction, result)
