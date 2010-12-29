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
    if not _transaction and _transaction != current:
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
# object from 'wsgi.file_wrapper' instance as we rewrap the file
# object and create new 'wsgi.file_wrapper'. The 'close()' of
# the wrapped file object is then replaced rather than needing a
# new generator be created that stops 'wsgi.file_wrapper' from
# working.

class _ExitCallbackFile:

    def __init__(self, transaction, file):
        self.__transaction = transaction
        self.__file = file

        if hasattr(self.__file, 'fileno'):
            self.fileno = self.__file.fileno
        if hasattr(self.__file, 'read'):
            self.read = self.__file.read
        if hasattr(self.__file, 'tell'):
            self.tell = self.__file.tell

    def close(self):
        try:
            if hasattr(self.__file, 'close'):
                self.__file.close()
        except:
            self.__transaction.__exit__(*sys.exc_info())
            raise
        else:
            self.__transaction.__exit__(None, None, None)
        finally:
            _context.transactions.pop()

class _ExitCallbackGenerator:

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
            _pop_transaction(transactions)
            raise

        if str(type(result)).find("'mod_wsgi.Stream'") != -1 and \
                hasattr(result, 'file'):
            return environ['wsgi.file_wrapper'](
                    _ExitCallbackFile(transaction, result.file()))
        else:
            return _ExitCallbackGenerator(transaction, result)
