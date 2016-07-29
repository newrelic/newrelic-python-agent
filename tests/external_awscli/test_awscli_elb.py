import uuid

import awscli.clidriver
import moto

from newrelic.agent import background_task
from testing_support.fixtures import validate_transaction_metrics

AWS_REGION = 'us-west-2'

TEST_ELB = 'python-agent-test-%s' % uuid.uuid4()

_elb_scoped_metrics = [
    ('External/elasticloadbalancing.us-west-2.amazonaws.com/botocore/POST', 4),
]

_elb_rollup_metrics = [
    ('External/all', 4),
    ('External/allOther', 4),
    ('External/elasticloadbalancing.us-west-2.amazonaws.com/all', 4),
    ('External/elasticloadbalancing.us-west-2.amazonaws.com/botocore/POST', 4),
]

@validate_transaction_metrics(
        'test_awscli_elb:test_elb',
        scoped_metrics=_elb_scoped_metrics,
        rollup_metrics=_elb_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_elb
def test_elb():
    # Under the covers, the `aws` executable creates a driver object then calls
    # its `main` method
    driver = awscli.clidriver.create_clidriver()

    # Create a load balancer
    # `args` is a list of command line arguments, all minus the beginning `aws`
    args = ['elb', 'create-load-balancer', '--load-balancer-name', TEST_ELB,
            '--listeners',
            'Protocol=HTTP,LoadBalancerPort=12345,InstancePort=2345',
            '--region', AWS_REGION]
    rc = driver.main(args=args)
    assert rc == 0

    # Add tags to it
    args = ['elb', 'add-tags', '--load-balancer-names', TEST_ELB, '--tags',
            'Key=hello,Value=world', '--region', AWS_REGION]
    rc = driver.main(args=args)
    assert rc == 0

    # List all load balancers
    args = ['elb', 'describe-load-balancers', '--region', AWS_REGION]
    rc = driver.main(args=args)
    assert rc == 0

    # Delete the load balancer
    args = ['elb', 'delete-load-balancer', '--load-balancer-name', TEST_ELB,
            '--region', AWS_REGION]
    rc = driver.main(args=args)
    assert rc == 0
