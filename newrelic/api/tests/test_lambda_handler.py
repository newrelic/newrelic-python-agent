import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.lambda_handler as lambda_handler

settings = newrelic.api.settings.settings()
_application = newrelic.api.application.application_instance()


API_GATEWAY_EVENT = {
    'body': '{"test":"body"}',
    'headers': {'Accept': 'text/html',
                'Accept-Encoding': 'gzip, deflate, sdch',
                'Accept-Language': 'en-US,en;q=0.8',
                'Cache-Control': 'max-age=0',
                'CloudFront-Forwarded-Proto': 'https',
                'CloudFront-Is-Desktop-Viewer': 'true',
                'CloudFront-Is-Mobile-Viewer': 'false',
                'CloudFront-Is-SmartTV-Viewer': 'false',
                'CloudFront-Is-Tablet-Viewer': 'false',
                'CloudFront-Viewer-Country': 'US',
                'Host': '1234567890.execute-api.us-west-2.amazonaws.com',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Custom User Agent String',
                'Via': '1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net '
                       '(CloudFront)',
                'X-Amz-Cf-Id': 'foobar',
                'X-Forwarded-For': '127.0.0.1, 127.0.0.2',
                'X-Forwarded-Port': '443',
                'X-Forwarded-Proto': 'https'},
    'httpMethod': 'POST',
    'path': '/path/to/resource',
    'pathParameters': {'proxy': 'path/to/resource'},
    'queryStringParameters': {'foo': 'bar'},
    'requestContext': {'accountId': '123456789012',
                       'apiId': '1234567890',
                       'httpMethod': 'POST',
                       'identity': {'accountId': None,
                                    'apiKey': None,
                                    'caller': None,
                                    'cognitoAuthenticationProvider': None,
                                    'cognitoAuthenticationType': None,
                                    'cognitoIdentityId': None,
                                    'cognitoIdentityPoolId': None,
                                    'sourceIp': '127.0.0.1',
                                    'user': None,
                                    'userAgent': 'Custom User Agent String',
                                    'userArn': None},
                       'requestId': 'c6af9ac6-7b61-11e6-9a41-93e8deadbeef',
                       'resourceId': '123456',
                       'resourcePath': '/{proxy+}',
                       'stage': 'prod'},
    'resource': '/{proxy+}',
    'stageVariables': {'baz': 'qux'},
}


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
        handler(API_GATEWAY_EVENT, Context)

    def test_decorator_integer_event(self):
        handler(42, Context)

    def test_not_a_lambda(self):
        not_a_lambda(42)

    def test_already_running_transaction(self):
        nested_handler({}, Context)
