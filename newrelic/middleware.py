# vi: set sw=4 expandtab :

__all__ = [ 'WSGIApplication', 'wsgi_application' ]

import sys
import types

import _newrelic

# Provide a WSGI application middleware wrapper for initiating a
# web transaction for each request and ensuring that timing is
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

def _FileWrapper(transaction, generator):

    class _FileWrapper(type(generator)):

        def __init__(self, transaction, generator):
            super(_FileWrapper, self).__init__(generator.filelike,
                                               generator.blksize)
            self.__transaction = transaction
            self.__generator = generator

        def close(self):
            try:
                self.__generator.close()
            except:
                self.__transaction.__exit__(*sys.exc_info())
                raise
            else:
                self.__transaction.__exit__(None, None, None)

    return _FileWrapper(transaction, generator)

class _Generator(object):

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

class WSGIApplication(object):

    def __init__(self, application, callable):
        self.__application = application
        self.__callable = callable

    def __get__(self, obj, objtype=None):
        return types.MethodType(self, obj, objtype)

    def __call__(self, *args):
        environ = args[-2]
        start_response = args[-1]

        transaction = _newrelic.WebTransaction(self.__application, environ)
        transaction.__enter__()

        def _start_response(status, response_headers, exc_info=None):
            transaction.response_code = int(status.split(' ')[0])
            return start_response(status, response_headers, exc_info)

        try:
            result = self.__callable(*args)
        except:
            transaction.__exit__(*sys.exc_info())
            raise

        file_wrapper = environ.get('wsgi.file_wrapper', None)
        if file_wrapper and isinstance(result, file_wrapper) and \
                hasattr(result, 'filelike') and hasattr(result, 'blksize'):
            return _FileWrapper(transaction, result)
        else:
            return _Generator(transaction, result)

# Provide decorator for WSGI application. With this decorator
# the WSGI application middleware wrapper is used so that the
# end of the corresponding web transaction is recorded as being
# when all response content is written back to the HTTP client.

def wsgi_application(name):
    application = _newrelic.application(name)

    def decorator(callable):
        return WSGIApplication(application, callable)

    return decorator
