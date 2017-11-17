import logging
import traceback

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.agent import remove_thread_utilization

_logger = logging.getLogger(__name__)
_VERSION = None


def _store_version_info():
    import tornado
    global _VERSION

    try:
        _VERSION = '.'.join(map(str, tornado.version_info))
    except:
        pass


def _nr_request_handler_init(wrapped, instance, args, kwargs):
    if current_transaction() is not None:
        _logger.error('Attempting to make a request (new transaction) when a '
                'transaction is already running. Please report this issue to '
                'New Relic support.\n%s',
                ''.join(traceback.format_stack()[:-1]))
        return wrapped(*args, **kwargs)

    def _bind_params(application, request, *args, **kwargs):
        return request

    request = _bind_params(*args, **kwargs)

    if request.method not in instance.SUPPORTED_METHODS:
        # If the method isn't one of the supported ones, then we expect the
        # wrapped method to raise an exception for HTTPError(405). In this case
        # we name the transaction after the wrapped method.
        name = callable_name(instance)
    else:
        # Otherwise we name the transaction after the handler function that
        # should end up being executed for the request.
        method = getattr(instance, request.method.lower())
        name = callable_name(method)

    app = application_instance()
    txn = WebTransaction(app, {})
    txn.__enter__()

    if txn.enabled:
        txn.drop_transaction()
        instance._nr_transaction = txn

    txn.set_transaction_name(name)

    # Record framework information for generation of framework metrics.
    txn.add_framework_info('Tornado/ASYNC', _VERSION)

    return wrapped(*args, **kwargs)


def instrument_tornado_web(module):

    # Thread utilization data is meaningless in a tornado app. Remove it here,
    # once, since we know that tornado has been imported now. The following
    # call to agent_instance will initialize data sources, if they have not
    # been already. Thus, we know that this is a single place that we can
    # remove the thread utilization, regardless of the order of imports/agent
    # registration.

    remove_thread_utilization()

    wrap_function_wrapper(module, 'RequestHandler.__init__',
            _nr_request_handler_init)

    _store_version_info()
