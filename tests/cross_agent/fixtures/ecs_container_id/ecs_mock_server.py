import json

import pytest
from testing_support.mock_external_http_server import MockExternalHTTPServer

STANDARD_RESPONSE = {
    "DockerId": "1e1698469422439ea356071e581e8545-2769485393",
    "Name": "fargateapp",
    "DockerName": "fargateapp",
    "Image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/fargatetest:latest",
    "ImageID": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
    "Labels": {
        "com.amazonaws.ecs.cluster": "arn:aws:ecs:us-west-2:123456789012:cluster/testcluster",
        "com.amazonaws.ecs.container-name": "fargateapp",
        "com.amazonaws.ecs.task-arn": "arn:aws:ecs:us-west-2:123456789012:task/testcluster/1e1698469422439ea356071e581e8545",
        "com.amazonaws.ecs.task-definition-family": "fargatetestapp",
        "com.amazonaws.ecs.task-definition-version": "7",
    },
    "DesiredStatus": "RUNNING",
    "KnownStatus": "RUNNING",
    "Limits": {"CPU": 2},
    "CreatedAt": "2024-04-25T17:38:31.073208914Z",
    "StartedAt": "2024-04-25T17:38:31.073208914Z",
    "Type": "NORMAL",
    "LogDriver": "awslogs",
    "LogOptions": {
        "awslogs-create-group": "true",
        "awslogs-group": "/ecs/fargatetestapp",
        "awslogs-region": "us-west-2",
        "awslogs-stream": "ecs/fargateapp/1e1698469422439ea356071e581e8545",
    },
    "ContainerARN": "arn:aws:ecs:us-west-2:123456789012:container/testcluster/1e1698469422439ea356071e581e8545/050256a5-a7f3-461c-a16f-aca4eae37b01",
    "Networks": [
        {
            "NetworkMode": "awsvpc",
            "IPv4Addresses": ["10.10.10.10"],
            "AttachmentIndex": 0,
            "MACAddress": "06:d7:3f:49:1d:a7",
            "IPv4SubnetCIDRBlock": "10.10.10.0/20",
            "DomainNameServers": ["10.10.10.2"],
            "DomainNameSearchList": ["us-west-2.compute.internal"],
            "PrivateDNSName": "ip-10-10-10-10.us-west-2.compute.internal",
            "SubnetGatewayIpv4Address": "10.10.10.1/20",
        }
    ],
    "Snapshotter": "overlayfs",
}

NO_ID_RESPONSE = {
    "Name": "fargateapp",
    "DockerName": "fargateapp",
    "Image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/fargatetest:latest",
    "ImageID": "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
    "Labels": {
        "com.amazonaws.ecs.cluster": "arn:aws:ecs:us-west-2:123456789012:cluster/testcluster",
        "com.amazonaws.ecs.container-name": "fargateapp",
        "com.amazonaws.ecs.task-arn": "arn:aws:ecs:us-west-2:123456789012:task/testcluster/1e1698469422439ea356071e581e8545",
        "com.amazonaws.ecs.task-definition-family": "fargatetestapp",
        "com.amazonaws.ecs.task-definition-version": "7",
    },
    "DesiredStatus": "RUNNING",
    "KnownStatus": "RUNNING",
    "Limits": {"CPU": 2},
    "CreatedAt": "2024-04-25T17:38:31.073208914Z",
    "StartedAt": "2024-04-25T17:38:31.073208914Z",
    "Type": "NORMAL",
    "LogDriver": "awslogs",
    "LogOptions": {
        "awslogs-create-group": "true",
        "awslogs-group": "/ecs/fargatetestapp",
        "awslogs-region": "us-west-2",
        "awslogs-stream": "ecs/fargateapp/1e1698469422439ea356071e581e8545",
    },
    "ContainerARN": "arn:aws:ecs:us-west-2:123456789012:container/testcluster/1e1698469422439ea356071e581e8545/050256a5-a7f3-461c-a16f-aca4eae37b01",
    "Networks": [
        {
            "NetworkMode": "awsvpc",
            "IPv4Addresses": ["10.10.10.10"],
            "AttachmentIndex": 0,
            "MACAddress": "06:d7:3f:49:1d:a7",
            "IPv4SubnetCIDRBlock": "10.10.10.0/20",
            "DomainNameServers": ["10.10.10.2"],
            "DomainNameSearchList": ["us-west-2.compute.internal"],
            "PrivateDNSName": "ip-10-10-10-10.us-west-2.compute.internal",
            "SubnetGatewayIpv4Address": "10.10.10.1/20",
        }
    ],
    "Snapshotter": "overlayfs",
}


def simple_get(self):
    response = json.dumps(STANDARD_RESPONSE).encode("utf-8")
    self.send_response(200)
    self.end_headers()
    self.wfile.write(response)


def bad_response_get(self):
    response = json.dumps(NO_ID_RESPONSE).encode("utf-8")
    self.send_response(200)
    self.end_headers()
    self.wfile.write(response)


@pytest.fixture(scope="function")
def mock_server():
    with MockExternalHTTPServer(handler=simple_get) as mock_server:
        yield mock_server


@pytest.fixture(scope="function")
def bad_response_mock_server():
    with MockExternalHTTPServer(handler=bad_response_get) as bad_response_mock_server:
        yield bad_response_mock_server
