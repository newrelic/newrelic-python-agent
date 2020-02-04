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

KINESIS_RECORD_EVENT = {
    "Records": [
        {
            "kinesis": {
                "kinesisSchemaVersion": "1.0",
                "partitionKey": "1",
                "sequenceNumber": "49590338271490256608559692538361571095921575989136588898",
                "data": "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0Lg==",
                "approximateArrivalTimestamp": 1545084650.987
            },
            "eventSource": "aws:kinesis",
            "eventVersion": "1.0",
            "eventID": "shardId-000000000006:49590338271490256608559692538361571095921575989136588898",
            "eventName": "aws:kinesis:record",
            "invokeIdentityArn": "arn:aws:iam::123456789012:role/lambda-role",
            "awsRegion": "us-east-2",
            "eventSourceARN": "arn:aws:kinesis:us-east-2:123456789012:stream/lambda-stream"
        }
    ]
}

KINESIS_FIREHOSE_EVENT = {
    "records": [
        {
            "recordId": "495787340864422590374",
            "approximateArrivalTimestamp": 1510254469498,
            "data": "",
            "kinesisRecordMetadata": {
                "shardId": "shardId-000000000000",
                "partitionKey": "4d1ad2b9-24f8-4b9d-a088-76e9947c317a",
                "approximateArrivalTimestamp": "2012-04-23T18:25:43.511Z",
                "sequenceNumber": "49546986683135544286507457936321625675700192471156785154",
                "subsequenceNumber": ""
            }
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

ALB_EVENT = {
    "requestContext": {
        "elb": {
            "targetGroupArn": "arn:aws:elasticloadbalancing:us-east-2:123456789012:targetgroup/lambda-279XGJDqGZ5rsrHC2Fjr/49e9d65c45c6791a"
        }
    },
    "httpMethod": "GET",
    "path": "/lambda",
    "queryStringParameters": {
        "query": "1234ABCD"
    },
    "headers": {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-encoding": "gzip",
        "accept-language": "en-US,en;q=0.9",
        "connection": "keep-alive",
        "host": "lambda-alb-123578498.us-east-2.elb.amazonaws.com",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
        "x-amzn-trace-id": "Root=1-5c536348-3d683b8b04734faae651f476",
        "x-forwarded-for": "72.12.164.125",
        "x-forwarded-port": "80",
        "x-forwarded-proto": "http",
        "x-imforwards": "20"
    },
    "body": "",
    "isBase64Encoded": False
}

CLOUDFRONT_EVENT = {
    "Records": [
        {
            "cf": {
                "config": {
                    "distributionId": "EXAMPLE"
                },
                "request": {
                    "uri": "/test",
                    "method": "GET",
                    "clientIp": "2001:cdba::3257:9652",
                    "headers": {
                        "host": [
                            {
                                "key": "Host",
                                "value": "d123.cf.net"
                            }
                        ],
                        "user-agent": [
                            {
                                "key": "User-Agent",
                                "value": "Test Agent"
                            }
                        ],
                        "user-name": [
                            {
                                "key": "User-Name",
                                "value": "aws-cloudfront"
                            }
                        ]
                    }
                }
            }
        }
    ]
}

CLOUDWATCH_SCHEDULED = {
    "id": "cdc73f9d-aea9-11e3-9d5a-835b769c0d9c",
    "detail-type": "Scheduled Event",
    "source": "aws.events",
    "account": "{{{account-id}}}",
    "time": "1970-01-01T00:00:00Z",
    "region": "us-west-2",
    "resources": [
        "arn:aws:events:us-west-2:123456789012:rule/ExampleRule"
    ],
    "detail": {}
}

DYNAMO_STREAMS = {
    "Records": [
        {
            "eventID": "c4ca4238a0b923820dcc509a6f75849b",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-west-2",
            "dynamodb": {
                "Keys": {
                    "Id": {
                        "N": "101"
                    }
                },
                "NewImage": {
                    "Message": {
                        "S": "New item!"
                    },
                    "Id": {
                        "N": "101"
                    }
                },
                "ApproximateCreationDateTime": 1428537600,
                "SequenceNumber": "4421584500000000017450439091",
                "SizeBytes": 26,
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            },
            "eventSourceARN": "arn:aws:dynamodb:us-west-2:123456789012:table/ExampleTableWithStream/stream/2015-06-27T00:48:05.899"
        },
        {
            "eventID": "c81e728d9d4c2f636f067f89cc14862c",
            "eventName": "MODIFY",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-west-2",
            "dynamodb": {
                "Keys": {
                    "Id": {
                        "N": "101"
                    }
                },
                "NewImage": {
                    "Message": {
                        "S": "This item has changed"
                    },
                    "Id": {
                        "N": "101"
                    }
                },
                "OldImage": {
                    "Message": {
                        "S": "New item!"
                    },
                    "Id": {
                        "N": "101"
                    }
                },
                "ApproximateCreationDateTime": 1428537600,
                "SequenceNumber": "4421584500000000017450439092",
                "SizeBytes": 59,
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            },
            "eventSourceARN": "arn:aws:dynamodb:us-west-2:123456789012:table/ExampleTableWithStream/stream/2015-06-27T00:48:05.899"
        },
        {
            "eventID": "eccbc87e4b5ce2fe28308fd9f2a7baf3",
            "eventName": "REMOVE",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-west-2",
            "dynamodb": {
                "Keys": {
                    "Id": {
                        "N": "101"
                    }
                },
                "OldImage": {
                    "Message": {
                        "S": "This item has changed"
                    },
                    "Id": {
                        "N": "101"
                    }
                },
                "ApproximateCreationDateTime": 1428537600,
                "SequenceNumber": "4421584500000000017450439093",
                "SizeBytes": 38,
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            },
            "eventSourceARN": "arn:aws:dynamodb:us-west-2:123456789012:table/ExampleTableWithStream/stream/2015-06-27T00:48:05.899"
        }
    ]
}

SES_EVENT = {
    "Records": [
        {
            "eventSource": "aws:ses",
            "eventVersion": "1.0",
            "ses": {
                "mail": {
                    "commonHeaders": {
                        "date": "Wed, 7 Oct 2015 12:34:56 -0700",
                        "from": [
                            "Jane Doe <janedoe@example.com>"
                        ],
                        "messageId": "<0123456789example.com>",
                        "returnPath": "janedoe@example.com",
                        "subject": "Test Subject",
                        "to": [
                            "johndoe@example.com"
                        ]
                    },
                    "destination": [
                        "johndoe@example.com"
                    ],
                    "headers": [
                        {
                            "name": "Return-Path",
                            "value": "<janedoe@example.com>"
                        },
                        {
                            "name": "Received",
                            "value": "from mailer.example.com (mailer.example.com [203.0.113.1]) by inbound-smtp.us-west-2.amazonaws.com with SMTP id o3vrnil0e2ic28trm7dfhrc2v0cnbeccl4nbp0g1 for johndoe@example.com; Wed, 07 Oct 2015 12:34:56 +0000 (UTC)"
                        },
                        {
                            "name": "DKIM-Signature",
                            "value": "v=1; a=rsa-sha256; c=relaxed/relaxed; d=example.com; s=example; h=mime-version:from:date:message-id:subject:to:content-type; bh=jX3F0bCAI7sIbkHyy3mLYO28ieDQz2R0P8HwQkklFj4=; b=sQwJ+LMe9RjkesGu+vqU56asvMhrLRRYrWCbVt6WJulueecwfEwRf9JVWgkBTKiL6m2hr70xDbPWDhtLdLO+jB3hzjVnXwK3pYIOHw3vxG6NtJ6o61XSUwjEsp9tdyxQjZf2HNYee873832l3K1EeSXKzxYk9Pwqcpi3dMC74ct9GukjIevf1H46hm1L2d9VYTL0LGZGHOAyMnHmEGB8ZExWbI+k6khpurTQQ4sp4PZPRlgHtnj3Zzv7nmpTo7dtPG5z5S9J+L+Ba7dixT0jn3HuhaJ9b+VThboo4YfsX9PMNhWWxGjVksSFOcGluPO7QutCPyoY4gbxtwkN9W69HA=="
                        },
                        {
                            "name": "MIME-Version",
                            "value": "1.0"
                        },
                        {
                            "name": "From",
                            "value": "Jane Doe <janedoe@example.com>"
                        },
                        {
                            "name": "Date",
                            "value": "Wed, 7 Oct 2015 12:34:56 -0700"
                        },
                        {
                            "name": "Message-ID",
                            "value": "<0123456789example.com>"
                        },
                        {
                            "name": "Subject",
                            "value": "Test Subject"
                        },
                        {
                            "name": "To",
                            "value": "johndoe@example.com"
                        },
                        {
                            "name": "Content-Type",
                            "value": "text/plain; charset=UTF-8"
                        }
                    ],
                    "headersTruncated": False,
                    "messageId": "o3vrnil0e2ic28trm7dfhrc2v0clambda4nbp0g1",
                    "source": "janedoe@example.com",
                    "timestamp": "1970-01-01T00:00:00.000Z"
                },
                "receipt": {
                    "action": {
                        "functionArn": "arn:aws:lambda:us-west-2:123456789012:function:Example",
                        "invocationType": "Event",
                        "type": "Lambda"
                    },
                    "dkimVerdict": {
                        "status": "PASS"
                    },
                    "processingTimeMillis": 574,
                    "recipients": [
                        "johndoe@example.com"
                    ],
                    "spamVerdict": {
                        "status": "PASS"
                    },
                    "spfVerdict": {
                        "status": "PASS"
                    },
                    "timestamp": "1970-01-01T00:00:00.000Z",
                    "virusVerdict": {
                        "status": "PASS"
                    }
                }
            }
        }
    ]
}


