S3_EVENT = {
    "Records": [
        {
            "eventVersion": "2.0",
            "eventTime": "1970-01-01T00:00:00.000Z",
            "requestParameters": {
                "sourceIPAddress": "127.0.0.1"
            },
            "s3": {
                "configurationId": "testConfigRule",
                "object": {
                    "eTag": "0123456789abcdef0123456789abcdef",
                    "sequencer": "0A1B2C3D4E5F678901",
                    "key": "HappyFace.jpg",
                    "size": 1024
                },
                "bucket": {
                    "arn": "arn:aws:s3:::mybucket",
                    "name": "sourcebucket",
                    "ownerIdentity": {
                        "principalId": "EXAMPLE"
                    }
                },
                "s3SchemaVersion": "1.0"
            },
            "responseElements": {
                "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisaw"
                              "esome/mnopqrstuvwxyzABCDEFGH",
                "x-amz-request-id": "EXAMPLE123456789"
            },
            "awsRegion": "us-west-2",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {
                "principalId": "EXAMPLE"
            },
            "eventSource": "aws:s3"
        }
    ]
}

SNS_EVENT = {
    "Records": [
        {
            "EventVersion": "1.0",
            "EventSubscriptionArn": "arn:aws:sns:EXAMPLE",
            "EventSource": "aws:sns",
            "Sns": {
                "SignatureVersion": "1",
                "Timestamp": "1970-01-01T00:00:00.000Z",
                "Signature": "EXAMPLE",
                "SigningCertUrl": "EXAMPLE",
                "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                "Message": "Hello from SNS!",
                "MessageAttributes": {
                    "Test": {
                        "Type": "String",
                        "Value": "TestString"
                    },
                    "TestBinary": {
                        "Type": "Binary",
                        "Value": "TestBinary"
                    }
                },
                "Type": "Notification",
                "UnsubscribeUrl": "EXAMPLE",
                "TopicArn": "arn:aws:sns:EXAMPLE",
                "Subject": "TestInvoke"
            }
        }
    ]
}

SQS_EVENT = {
    "Records": [
        {
            "body": "Hello from SQS!",
            "receiptHandle": "MessageReceiptHandle",
            "md5OfBody": "7b270e59b47ff90a553787216d55d91d",
            "eventSourceARN": "arn:aws:sqs:us-west-2:123456789012:MyQueue",
            "eventSource": "aws:sqs",
            "awsRegion": "us-west-2",
            "messageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
            "attributes": {
                "ApproximateFirstReceiveTimestamp": "1523232000001",
                "SenderId": "123456789012",
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1523232000000"
            },
            "messageAttributes": {}
        }
    ]
}

KINESIS_ANALYTICS_EVENT = {
    "records": [
        {
            "recordId": "123456",
            "data": "VGhpcyBpcyBhIHRlc3QgZnJvbSBraW5lc2lzIGFuYWx5dGljcw=="
        }
    ],
    "streamArn": "arn:aws:kinesis::Streamsexample",
    "invocationId": "invocationIdExample",
    "applicationArn": "arn:aws:kinesisanalytics:exampleApplication"
}

KINESIS_FIREHOSE_EVENT = {
    "records": [
        {
            "recordId": "495787340864422590374",
            "approximateArrivalTimestamp": 1510254469498,
            "data": ""
        },
        {
            "recordId": "495787340864422590374",
            "approximateArrivalTimestamp": 1510254473773,
            "data": ""
        },
        {
            "recordId": "495787340864422590374",
            "approximateArrivalTimestamp": 1510254474027,
            "data": ""
        },
        {
            "recordId": "495787340864422590374",
            "approximateArrivalTimestamp": 1510254474388,
            "data": ""
        }
    ],
    "region": "us-west-2",
    "deliveryStreamArn": "arn:aws:firehose:us-west-2:123456789012:THESTREAM",
    "invocationId": "a7234216-12b6-4bc0-96d7-82606c0e80cf"
}

LONG_ARN_EVENT = {
    "records": [
        {
            "recordId": "123456",
            "data": "VGhpcyBpcyBhIHRlc3QgZnJvbSBraW5lc2lzIGFuYWx5dGljcw=="
        }
    ],
    "streamArn": "arn:aws:kinesis::" + "StreamsExample" * 20,
    "invocationId": "invocationIdExample",
    "applicationArn": "arn:aws:kinesisanalytics:exampleApplication"
}

GARBAGE_EVENT = {
    "Records": [{
        "eventSourceArn": "eventSourceARN has the wrong capitalization!",
        "deliveryStreamArn": "deliveryStreamArn is in records, not Records!"
    }],
    "streamArn": ["this shouldn't be a list!"]
}

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
