"""
Test get_accounts_function
"""
import copy
from test import CONST_NEXT_AMI_PARAM, CONST_REGION, ContextMock

import boto3
import pytest
from moto import mock_ssm

from update_next.update_next_ami_function import get_ssm_param, lambda_handler


@mock_ssm
def test_lambda_handler():
    """Test update_next_ami_function.lambda_handler to update next"""

    # Setup test data
    original_param_value = 'blank' # same as initial cfn deployment value
    client = boto3.client('ssm', region_name=CONST_REGION)
    client.put_parameter(
        Name=CONST_NEXT_AMI_PARAM,
        Value=original_param_value,
        Type='String',
        Overwrite=True
    )

    # Test Lambda handler
    next_ami_id = "ami-1234567890abcdef"
    event = {"AMI": next_ami_id, "BuildInstanceID": 'i-12345678'}
    context = ContextMock()
    output_event = lambda_handler(copy.deepcopy(event), context)

    # Verify the output_event is updated with the param store path and its version
    assert output_event != event # Assert that the event has been modified
    assert output_event["SsmParamVersion"] == '2'
    assert output_event["SsmParam"] == CONST_NEXT_AMI_PARAM

    # Verify the SSM param is actually updated
    param_value = get_ssm_param(CONST_REGION, CONST_NEXT_AMI_PARAM)
    assert param_value != original_param_value
    assert param_value == next_ami_id


@mock_ssm
def test_lambda_handler_with_invalid_ami_id():
    """Test update_next_ami_function.lambda_handler to update next"""

    # Test Lambda handler
    next_ami_id = "ami-invalid-id"
    event = {"AMI": next_ami_id, "BuildInstanceID": 'i-12345678'}
    context = ContextMock()
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert 'does not match AMI Id format' in str(excinfo.value)


@mock_ssm
def test_lambda_handler_with_missing_instance_id():
    """Test update_next_ami_function.lambda_handler to update next"""

    # Test Lambda handler
    next_ami_id = "ami-12345678"
    event = {"AMI": next_ami_id}
    context = ContextMock()
    with pytest.raises(KeyError) as excinfo:
        lambda_handler(event, context)
    assert 'BuildInstanceID' in str(excinfo.value)


@mock_ssm
def test_lambda_handler_with_invalid_instance_id():
    # Test Lambda handler
    next_ami_id = "ami-12345678"
    event = {"AMI": next_ami_id, "BuildInstanceID": None}
    context = ContextMock()
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert 'BuildInstanceID is None' in str(excinfo.value)


@mock_ssm
def test_lambda_handler_with_valid_instance_id():
    param = '/plt-baking/lnx-amzn/instanceId'

    # Setup test data
    original_param_value = 'blank' # same as initial cfn deployment value
    client = boto3.client('ssm', region_name=CONST_REGION)
    client.put_parameter(
        Name=param,
        Value=original_param_value,
        Type='String',
        Overwrite=True
    )

    # Test Lambda handler
    next_ami_id = "ami-12345678"
    instance_id = 'i-87654321'
    event = {"AMI": next_ami_id, "BuildInstanceID": instance_id}
    context = ContextMock()
    output_event = lambda_handler(copy.deepcopy(event), context)

    # Verify the output event
    assert output_event != event # Assert that the event has been modified
    assert output_event["SsmParamVersion"] == '1'
    assert output_event["SsmParam"] == CONST_NEXT_AMI_PARAM

    # Verify the SSM param is actually updated
    param_value = get_ssm_param(CONST_REGION, param)
    assert param_value != original_param_value
    assert param_value == instance_id
