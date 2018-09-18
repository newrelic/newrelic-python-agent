import os
import time
import functools
from newrelic.common.object_wrapper import FunctionWrapper
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.application import application_instance
from newrelic.core.config import global_settings


START_TIME = time.time()
COLD_START_TIME = None


def process_event(event):
    try:
        if ('headers' in event and
                'httpMethod' in event and
                'path' in event):
            environ = {
                'REQUEST_METHOD': event['httpMethod'],
                'REQUEST_URI': event['path'],
            }
            for k, v in event['headers'].items():
                normalized_key = k.replace('-', '_').upper()
                http_key = 'HTTP_%s' % normalized_key
                environ[http_key] = v

            return environ, False, event.get('queryStringParameters')
    except Exception:
        pass

    return {}, True, None


def LambdaHandlerWrapper(wrapped, application=None, name=None,
        group=None):

    def _nr_lambda_handler_wrapper_(wrapped, instance, args, kwargs):
        # Check to see if any transaction is present, even an inactive
        # one which has been marked to be ignored or which has been
        # stopped already.

        transaction = current_transaction(active_only=False)

        if transaction:
            return wrapped(*args, **kwargs)

        try:
            event, context = args[:2]
        except Exception:
            return wrapped(*args, **kwargs)

        target_application = application

        # If application has an activate() method we assume it is an
        # actual application. Do this rather than check type so that
        # can easily mock it for testing.

        # FIXME Should this allow for multiple apps if a string.

        if not hasattr(application, 'activate'):
            target_application = application_instance(application)

        # Extract the environment from the event
        environ, background_task, query_params = process_event(event)

        # Now start recording the actual web transaction.
        transaction = WebTransaction(target_application, environ)
        transaction.background_task = background_task

        transaction._aws_request_id = getattr(context, 'aws_request_id', None)
        transaction._aws_arn = getattr(context, 'invoked_function_arn', None)
        transaction._aws_function_name = getattr(
                context, 'function_name', None)
        transaction._aws_function_version = getattr(
                context, 'function_version', None)
        try:
            transaction._memory_limit = int(getattr(
                    context, 'memory_limit_in_mb', None))
        except Exception:
            pass

        transaction._aws_region = os.environ.get('AWS_REGION', None)

        global COLD_START_TIME
        if COLD_START_TIME is None:
            COLD_START_TIME = time.time() - START_TIME
            transaction._cold_start_time = COLD_START_TIME

        settings = global_settings()
        if query_params and not settings.high_security:
            transaction._request_params.update(query_params)

        # Override the initial transaction name.

        if name is None:
            if transaction._aws_function_name:
                transaction.set_transaction_name(
                        transaction._aws_function_name, group, priority=1)

        elif name:
            transaction.set_transaction_name(name, group, priority=1)

        with transaction:
            result = wrapped(*args, **kwargs)
            try:
                if not background_task:
                    status_code = result.get('statusCode', None)
                    try:
                        status_code = str(status_code)
                    except Exception:
                        status_code = None

                    response_headers = result.get('headers', None)
                    try:
                        response_headers = list(response_headers.items())
                    except Exception:
                        response_headers = None

                    transaction.process_response(status_code, response_headers)
            except Exception:
                pass

            return result

    return FunctionWrapper(wrapped, _nr_lambda_handler_wrapper_)


def lambda_handler(application=None, name=None, group=None):
    return functools.partial(LambdaHandlerWrapper, application=application,
            name=name, group=group)
