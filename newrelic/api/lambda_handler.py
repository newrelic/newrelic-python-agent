import functools
from newrelic.common.object_wrapper import FunctionWrapper
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.application import application_instance
from newrelic.core.attribute import truncate
from newrelic.core.config import global_settings


COLD_START_RECORDED = False
MEGABYTE_IN_BYTES = 2**20

# We're using JSON syntax here to maximize cross-agent consistency.
EVENT_TYPE_INFO = {
    "alb": {
        "name": "alb",
        "required_keys": [
            ["httpMethod"],
            ["requestContext", "elb"]]
    },
    "apiGateway": {
        "name": "apiGateway",
        "required_keys": [
            ["headers"],
            ["httpMethod"],
            ["path"],
            ["requestContext"],
            ["resource"]]
    },
    "cloudFront": {
        "name": "cloudFront",
        "required_keys": [["Records", 0, "cf"]]
    },
    "cloudWatch_scheduled": {
        "name": "cloudWatch_scheduled",
        "required_keys": [
            ["source"],
            ["detail-type"]]
    },
    "dynamo_streams": {
        "name": "dynamo_streams",
        "required_keys": [["Records", 0, "dynamodb"]]
    },
    "firehose": {
        "name": "firehose",
        "required_keys": [
            ["deliveryStreamArn"],
            ["records", 0, "kinesisRecordMetadata"]]
    },
    "kinesis": {
        "name": "kinesis",
        "required_keys": [["Records", 0, "kinesis"]]
    },
    "s3": {
        "name": "s3",
        "required_keys": [["Records", 0, "s3"]]
    },
    "ses": {
        "name": "ses",
        "required_keys": [["Records", 0, "ses"]]
    },
    "sns": {
        "name": "sns",
        "required_keys": [["Records", 0, "Sns"]]
    },
    "sqs": {
        "name": "sqs",
        "required_keys": [["Records", 0, "receiptHandle"]]
    }
}


def path_match(path, obj):
    return path_get(path, obj) is not None


def path_get(path, obj):
    pos = obj
    for segment in path:
        try:
            pos = pos[segment]
        except IndexError:
            return None
        except KeyError:
            return None
    return pos


def extract_event_source_arn(event):
    try:
        # Firehose
        arn = event.get('streamArn') or \
              event.get('deliveryStreamArn')

        if not arn:
            # Dynamo, Kinesis, S3, SNS, SQS
            record = path_get(('Records', 0), event)
            if record:
                arn = record.get('eventSourceARN') or \
                      record.get('EventSubscriptionArn') or \
                      path_get(('s3', 'bucket', 'arn'), record)
        # ALB
        if not arn:
            arn = path_get(('requestContext', 'elb', 'targetGroupArn'), event)
        # CloudWatch events
        if not arn:
            arn = path_get(('resources', 0), event)

        if arn:
            return truncate(str(arn))
        return None
    except Exception:
        pass


def detect_event_type(event):
    if isinstance(event, dict):
        for k, type_info in EVENT_TYPE_INFO.items():
            if all(path_match(path, event)
                   for path in type_info['required_keys']):
                return type_info
    return None


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

        try:
            request_method = event['httpMethod']
            request_path = event['path']
            headers = event['headers']
            query_params = event.get('multiValueQueryStringParameters')
            background_task = False
        except Exception:
            request_method = None
            request_path = None
            headers = None
            query_params = None
            background_task = True

        transaction_name = name or getattr(context, 'function_name', None)

        transaction = WebTransaction(
                target_application,
                transaction_name,
                group=group,
                request_method=request_method,
                request_path=request_path,
                headers=headers)

        transaction.background_task = background_task

        request_id = getattr(context, 'aws_request_id', None)
        aws_arn = getattr(context, 'invoked_function_arn', None)
        event_source = extract_event_source_arn(event)
        event_type = detect_event_type(event)

        if request_id:
            transaction._add_agent_attribute('aws.requestId', request_id)
        if aws_arn:
            transaction._add_agent_attribute('aws.lambda.arn', aws_arn)
        if event_source:
            transaction._add_agent_attribute(
                    'aws.lambda.eventSource.arn', event_source)
        if event_type:
            transaction._add_agent_attribute(
                'aws.lambda.eventSource.eventType', event_type['name'])

        # COLD_START_RECORDED is initialized to "False" when the container
        # first starts up, and will remain that way until the below lines
        # of code are encountered during the first transaction after the cold
        # start. We record this occurence on the transaction so that an
        # attribute is created, and then set COLD_START_RECORDED to False so
        # that the attribute is not created again during future invocations of
        # this container.

        global COLD_START_RECORDED
        if COLD_START_RECORDED is False:
            transaction._add_agent_attribute('aws.lambda.coldStart', True)
            COLD_START_RECORDED = True

        settings = global_settings()
        if query_params and not settings.high_security:
            try:
                transaction._request_params.update(query_params)
            except:
                pass

        if not settings.aws_arn and aws_arn:
            settings.aws_arn = aws_arn

        with transaction:
            result = wrapped(*args, **kwargs)

            if not background_task:
                try:
                    status_code = result.get('statusCode')
                    response_headers = result.get('headers')

                    try:
                        response_headers = response_headers.items()
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
