import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.lambda_handler as lambda_handler
import newrelic.api.tests._test_lambda_event_sources as events

settings = newrelic.api.settings.settings()
_application = newrelic.api.application.application_instance()


@lambda_handler.lambda_handler()
def handler(event, context):
    pass


@lambda_handler.lambda_handler(name='foobar')
def named_handler(event, context):
    pass


@lambda_handler.lambda_handler()
def not_a_lambda(foo):
    pass


@lambda_handler.lambda_handler()
def nested_handler(event, context):
    return handler(event, context)


class EmptyContext(object):
    pass


class Context(object):
    aws_request_id = 'cookies'
    invoked_function_arn = 'arn'
    function_name = 'cats'
    function_version = '$LATEST'
    memory_limit_in_mb = 128


class TestCase(newrelic.tests.test_cases.TestCase):
    def test_decorator_empty_context(self):
        handler({}, EmptyContext)

    def test_decorator_realistic_context(self):
        handler({}, Context)

    def test_decorator_named(self):
        named_handler({}, Context)

    def test_decorator_api_gateway(self):
        handler(events.API_GATEWAY_EVENT, Context)

    def test_decorator_integer_event(self):
        handler(42, Context)

    def test_not_a_lambda(self):
        not_a_lambda(42)

    def test_already_running_transaction(self):
        nested_handler({}, Context)

    def test_none_type_event(self):
        handler(None, Context)

    def test_str_type_event(self):
        handler('this is a string', Context)

    def test_float_type_event(self):
        handler(123.4, Context)

    def test_list_type_event(self):
        handler(['this', 'is', 'a', 'list'], Context)


class TestLambdaEventSource(newrelic.tests.test_cases.TestCase):
    def test_s3_lookup(self):
        arn = lambda_handler.extract_event_source_arn(events.S3_EVENT)
        self.assertEqual(arn, 'arn:aws:s3:::mybucket')

    def test_sns_lookup(self):
        arn = lambda_handler.extract_event_source_arn(events.SNS_EVENT)
        self.assertEqual(arn, 'arn:aws:sns:EXAMPLE')

    def test_sqs_lookup(self):
        arn = lambda_handler.extract_event_source_arn(events.SQS_EVENT)
        self.assertEqual(arn, 'arn:aws:sqs:us-west-2:123456789012:MyQueue')

    def test_kinesis_analytics_lookup(self):
        arn = lambda_handler.extract_event_source_arn(
                events.KINESIS_ANALYTICS_EVENT)
        self.assertEqual(arn, 'arn:aws:kinesis::Streamsexample')

    def test_kinesis_firehose_lookup(self):
        arn = lambda_handler.extract_event_source_arn(
                events.KINESIS_FIREHOSE_EVENT)
        expected_arn = "arn:aws:firehose:us-west-2:123456789012:THESTREAM"
        self.assertEqual(arn, expected_arn)

    def test_long_lookup(self):
        long_arn = 'arn:aws:kinesis::' + 'StreamsExample' * 17
        arn = lambda_handler.extract_event_source_arn(events.LONG_ARN_EVENT)
        self.assertEqual(arn, long_arn)

    def test_failed_arn_lookup(self):
        arn = lambda_handler.extract_event_source_arn(events.GARBAGE_EVENT)
        self.assertEqual(type(arn), str)
