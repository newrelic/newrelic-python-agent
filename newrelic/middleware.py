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

def _FileWrapper(context, generator):

    class _FileWrapper(type(generator)):

        def __init__(self, context, generator):
            super(_FileWrapper, self).__init__(generator.filelike,
                                               generator.blksize)
            self.__context = context
            self.__generator = generator

        def close(self):
            try:
                self.__generator.close()
            except:
                self.__context.__exit__(*sys.exc_info())
                raise
            else:
                self.__context.__exit__(None, None, None)

    return _FileWrapper(context, generator)

class _Generator:

    def __init__(self, context, generator):
        self.__context = context
        self.__generator = generator

    def __iter__(self):
        for item in self.__generator:
            yield item

    def close(self):
        try:
            if hasattr(self.__generator, 'close'):
                self.__generator.close()
        except:
            self.__context.__exit__(*sys.exc_info())
            raise
        else:
            self.__context.__exit__(None, None, None)

class _ContextManager:

    def __init__(self, transaction):
        self.__transaction = transaction

    def __enter__(self):
        _push_transaction(self.__transaction)
        self.__transaction.__enter__()

    def __exit__(self, *args):
        _pop_transaction(self.__transaction)
        self.__transaction.__exit(*args)

class WebTransaction:

    def __init__(self, application, callable):
        self.__application = application
        self.__callable = callable

    def __call__(self, environ, start_response):
        transaction = self.__application.web_transaction(environ)
        context = _ContextManager(transaction)

        context.__enter__()

        def _start_response(status, response_headers, exc_info=None):
            transaction.response_code = int(status.split(' ')[0])
            return start_response(status, response_headers, exc_info)

        try:
            result = self.__callable(environ, _start_response)
        except:
            context.__exit__(*sys.exc_info())
            raise

        file_wrapper = environ.get('wsgi.file_wrapper', None)
        if file_wrapper and isinstance(result, file_wrapper) and \
                hasattr(result, 'filelike') and hasattr(result, 'blksize'):
            return _FileWrapper(transaction, result)
        else:
            return _Generator(transaction, result)
