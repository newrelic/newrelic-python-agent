from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper
from newrelic.api.function_trace import FunctionTrace


def _bind_get_response(request, *args, **kwargs):
    return request


async def _nr_wrapper_BaseHandler_get_response_async_(
        wrapped, instance, args, kwargs):
    response = await wrapped(*args, **kwargs)

    if current_transaction() is None:
        return response

    request = _bind_get_response(*args, **kwargs)

    if hasattr(request, '_nr_exc_info'):
        notice_error(error=request._nr_exc_info, status_code=response.status_code)
        delattr(request, '_nr_exc_info')

    return response


def _nr_wrap_converted_middleware_async_(middleware, name):

    @function_wrapper
    async def _wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return await wrapped(*args, **kwargs)

        transaction.set_transaction_name(name, priority=2)

        with FunctionTrace(name=name):
            return await wrapped(*args, **kwargs)

    return _wrapper(middleware)
