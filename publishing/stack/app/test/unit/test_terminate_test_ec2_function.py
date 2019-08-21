"""
Test get_accounts_function
"""
import copy
from test import CONST_REGION, ContextMock
import pytest

import boto3
from mock import patch
from moto import mock_ec2

from terminate_test_ec2.terminate_test_ec2_function import lambda_handler

# Mock Constants
MOCK_NAME = 'mock-account'
MOCK_DOMAIN = 'moto-example.org'


@pytest.mark.parametrize("keep_ec2, expect_termination", [
    (None, True),
    ('', True),
    ('True', False), # Instance should not be terminated
    ('true', True),
    ('false', True),
    ('FailedOnly', True),
])
@mock_ec2
def test_lambda_handler(keep_ec2, expect_termination):
    """Test get_accounts_function.lambda_handler to return all account ids"""

    # Setup a test instance to delete
    ec2_client = boto3.client('ec2', region_name=CONST_REGION)
    run_ec2_response = ec2_client.run_instances(ImageId='ami-12345678', MaxCount=1, MinCount=1)
    instance_id = run_ec2_response['Instances'][0]['InstanceId']
    print(instance_id)

    # Check the instance is initially running
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
    assert instance_state == 'running'

    # Test Lambda handler
    event = {'InstanceID': instance_id}
    context = ContextMock()
    if keep_ec2:
        event['KeepTestInstance'] = keep_ec2

    output_event = lambda_handler(copy.deepcopy(event), context)

    # Assert that the event is not modified
    assert output_event == event

    # Check the instance is terminated (moto is instant vs boto will take time to terminate)
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
    if expect_termination:
        assert instance_state == 'terminated'
    else:
        assert instance_state == 'running'
