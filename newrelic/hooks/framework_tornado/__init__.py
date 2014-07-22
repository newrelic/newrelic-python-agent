import logging
import sys
import weakref
import types
import itertools
import traceback

from newrelic.agent import (wrap_function_wrapper, current_transaction,
        FunctionTrace, wrap_function_trace, WebTransaction, callable_name,
        ObjectWrapper, application as application_instance)

_logger = logging.getLogger(__name__)

def record_exception(transaction, exc_info):
    import tornado.web

    exc = exc_info[0]
    value = exc_info[1]

    if exc is tornado.web.HTTPError:
        if value.status_code == 404:
            return

    transaction.record_exception(*exc_info)

def request_environment(application, request):
    # This creates a WSGI environ dictionary from a Tornado request.

    result = getattr(request, '_nr_request_environ', None)

    if result is not None:
        return result

    # We don't bother if the agent hasn't as yet been registered.

    settings = application.settings

    if not settings:
        return {}

    request._nr_request_environ = result = {}

    result['REQUEST_URI'] = request.uri
    result['QUERY_STRING'] = request.query

    value = request.headers.get('X-NewRelic-ID')
    if value:
        result['HTTP_X_NEWRELIC_ID'] = value

    value = request.headers.get('X-NewRelic-Transaction')
    if value:
        result['HTTP_X_NEWRELIC_TRANSACTION'] = value

    value = request.headers.get('X-Request-Start')
    if value:
        result['HTTP_X_REQUEST_START'] = value

    value = request.headers.get('X-Queue-Start')
    if value:
        result['HTTP_X_QUEUE_START'] = value

    for key in settings.include_environ:
        if key == 'REQUEST_METHOD':
            result[key] = request.method
        elif key == 'HTTP_USER_AGENT':
            value = request.headers.get('User-Agent')
            if value:
                result[key] = value
        elif key == 'HTTP_REFERER':
            value = request.headers.get('Referer')
            if value:
                result[key] = value
        elif key == 'CONTENT_TYPE':
            value = request.headers.get('Content-Type')
            if value:
                result[key] = value
        elif key == 'CONTENT_LENGTH':
            value = request.headers.get('Content-Length')
            if value:
                result[key] = value

    return result

def retrieve_transaction_request(transaction):
    # Retrieves any request already associated with the transaction.

    return getattr(transaction, '_nr_current_request', None)

def retrieve_request_transaction(request):
    # Retrieves any transaction already associated with the request.

    return getattr(request, '_nr_transaction', None)

def initiate_request_monitoring(request):
    # Creates a new transaction and associates it with the request.
    # We always use the default application specified in the agent
    # configuration.

    application = application_instance()

    # We need to fake up a WSGI like environ dictionary with the key
    # bits of information we need.

    environ = request_environment(application, request)

    # We now start recording the actual web transaction. Bail out though
    # if it turns out that recording of transactions is not enabled.

    transaction = WebTransaction(application, environ)

    if not transaction.enabled:
        return

    transaction.__enter__()

    request._nr_transaction = transaction

    request._nr_wait_function_trace = None
    request._nr_request_finished = False

    # We also need to add a reference to the request object in to the
    # transaction object so we can later access it in a deferred. We
    # need to use a weakref to avoid an object cycle which may prevent
    # cleanup of the transaction.

    transaction._nr_current_request = weakref.ref(request)

    return transaction

def suspend_request_monitoring(request, name, group='Python/Tornado',
        terminal=True, rollup='Async Wait'):

    # Suspend the monitoring of the transaction. We do this because
    # we can't rely on thread local data to separate transactions for
    # requests. We thus have to move it out of the way.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Suspending the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # Create a function trace to track the time while monitoring of
    # this transaction is suspended.

    request._nr_wait_function_trace = FunctionTrace(transaction,
            name=name, group=group, terminal=terminal, rollup=rollup)

    request._nr_wait_function_trace.__enter__()

    transaction.drop_transaction()

def resume_request_monitoring(request, required=False):
    # Resume the monitoring of the transaction. This is moving the
    # transaction stored against the request as the active one.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        if not required:
            return

        _logger.error('Runtime instrumentation error. Resuming the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # Now make the transaction stored against the request the current
    # transaction.

    transaction.save_transaction()

    # Close out any active function trace used to track the time while
    # monitoring of the transaction was suspended. Technically there
    # should always be an active function trace but check and ignore
    # it if there isn't for now.

    try:
        if request._nr_wait_function_trace:
            request._nr_wait_function_trace.__exit__(None, None, None)

    finally:
        request._nr_wait_function_trace = None

    return transaction

def finalize_request_monitoring(request, exc=None, value=None, tb=None):
    # Finalize monitoring of the transaction.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Finalizing the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # If all nodes hadn't been popped from the transaction stack then
    # error messages will be logged by the transaction. We therefore do
    # not need to check here.

    transaction.__exit__(exc, value, tb)

    request._nr_transaction = None
    request._nr_wait_function_trace = None
    request._nr_request_finished = True

def instrument_tornado_template(module):

    def template_generate_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with FunctionTrace(transaction, name=instance.name,
                group='Template/Render'):
            return wrapped(*args, **kwargs)

    module.Template.generate = ObjectWrapper(
            module.Template.generate, None, template_generate_wrapper)

    def template_generate_python_wrapper(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        if result is not None:
            return 'import newrelic.agent as _nr_newrelic_agent\n' + result

    module.Template._generate_python = ObjectWrapper(
            module.Template._generate_python, None,
            template_generate_python_wrapper)

    def block_generate_wrapper(wrapped, instance, args, kwargs):
        def execute(writer, *args, **kwargs):
            if not hasattr(instance, 'line'):
                return wrapped(writer, *args, **kwargs)
            writer.write_line('with _nr_newrelic_agent.FunctionTrace('
                    '_nr_newrelic_agent.current_transaction(), name=%r, '
                    'group="Template/Block"):' % instance.name, instance.line)
            with writer.indent():
                writer.write_line("pass", instance.line)
                return wrapped(writer, *args, **kwargs)
        return execute(*args, **kwargs)

    module._NamedBlock.generate = ObjectWrapper(
            module._NamedBlock.generate, None, block_generate_wrapper)

def instrument_tornado_gen(module):

    # The Return exception type does not exist in Tornado 2.X.
    # Create a dummy exception type as a placeholder.

    try:
        Return = module.Return
    except AttributeError:
        class Return(Exception): pass

    def coroutine_wrapper(wrapped, instance, args, kwargs):
        def _func(func, *args, **kwargs):
            return func

        func = _func(*args, **kwargs)

        name = callable_name(func)
        name = '%s (generator)' % name

        def func_wrapper(wrapped, instance, args, kwargs):
            try:
                result = wrapped(*args, **kwargs)

            except (Return, StopIteration):
                raise

            except Exception:
                raise

            else:
                if isinstance(result, types.GeneratorType):
                    def _generator(generator):
                        try:
                            value = None
                            exc = None

                            while True:
                                transaction = current_transaction()

                                params = {}

                                params['filename'] = \
                                        generator.gi_frame.f_code.co_filename
                                params['lineno'] = \
                                        generator.gi_frame.f_lineno

                                with FunctionTrace(transaction, name,
                                        params=params):
                                    try:
                                        if exc is not None:
                                            yielded = generator.throw(*exc)
                                            exc = None
                                        else:
                                            yielded = generator.send(value)

                                    except (Return, StopIteration):
                                        raise

                                    except Exception:
                                        if transaction:
                                            transaction.record_exception(
                                                    *sys.exc_info())
                                        raise

                                try:
                                    value = yield yielded

                                except Exception:
                                    exc = sys.exc_info()

                        finally:
                            generator.close()

                    result = _generator(result)

                return result

            finally:
                pass

        func = ObjectWrapper(func, None, func_wrapper)

        return wrapped(func)

    if hasattr(module, 'coroutine'):
        module.coroutine = ObjectWrapper(module.coroutine, None,
                coroutine_wrapper)

    if hasattr(module, 'engine'):
        module.engine = ObjectWrapper(module.engine, None,
                coroutine_wrapper)
