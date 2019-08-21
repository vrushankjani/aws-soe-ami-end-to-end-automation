"""
Test trigger_build_function
"""
import copy
from importlib import reload
from test import CONST_REGION, CONST_SOL_NAMING, ContextMock

import boto3
import pytest
from mock import MagicMock, patch
from moto import mock_ec2, mock_organizations

from trigger_build import trigger_build_function


@pytest.mark.parametrize("ami_pattern, pipeline_override_ami, event_override_ami, expected_error, exception_message", [
    # Standard Test Cases (with No event OverrideAMI)
    ('plt-baking-soe*', '', None, None, None), # Regex AMI pattern
    ('plt-baking-soe*', None, None, ValueError, "Invalid Override AMI format set"), # pipeline_override_ami is None
    ('plt-baking-soe*', 'ami-12345678', None, None, None), # Override AMI
    ('plt-baking-soe*', 'invalid-ami', None, ValueError, "Invalid Override AMI format set"), # Invalid Overide AMI
    ('plt-baking-soe-ami-for-unit-test', '', None, None, None), # Full matching AMI pattern
    ('not-matching-image', '', None, ValueError, 'max() arg is an empty sequence'), # no matching images to AMI Pattern
    # Even OverrideAMI test Cases
    ('plt-baking-soe*', '', 'ami-11111111', None, None), # Regex AMI pattern
    ('plt-baking-soe*', None, 'ami-22222222', None, None), # pipeline_override_ami is None and valid event OverrideAMI
    ('plt-baking-soe*', None, 'invalid-event-ami', ValueError, "Invalid Override AMI format set"), # pipeline_override_ami is None
    ('plt-baking-soe*', 'ami-12345678', 'ami-33333333', None, None), # Override AMI
    ('plt-baking-soe*', 'invalid-ami', 'ami-44444444', None, None), # Invalid Overide AMI bu valid event Override AMI
    ('plt-baking-soe*', 'invalid-ami', 'invalid-event-ami', ValueError, "Invalid Override AMI format set"), # Invalid Overide AMI bu valid event Override AMI
    ('plt-baking-soe-ami-for-unit-test', '', 'ami-55555555', None, None), # Full matching AMI pattern
    ('not-matching-image', '', 'ami-66666666', None, None), # no matching images to AMI Pattern but valid event Override AMI
])
@mock_ec2
@mock_organizations
def test_lambda_handler(ami_pattern, pipeline_override_ami, event_override_ami, expected_error, exception_message, monkeypatch):
    """Test trigger_build_function.lambda_handler"""

    # Setup mock input
    soe_image_name = 'plt-baking-soe-ami-for-unit-test'
    mock_automation_execution_id = 'mock_automation_execution_id'
    ssm_document = 'SSMDocument'
    soe_type = 'lnx'
    ami_owner = 'self'

    # Set Environment Variables
    monkeypatch.setenv("SSMDocument", ssm_document)
    monkeypatch.setenv("SOEType", soe_type)
    monkeypatch.setenv("AMIPattern", ami_pattern)
    monkeypatch.setenv("AMIOwner", ami_owner)
    monkeypatch.setenv("OverrideAMI", pipeline_override_ami)
    # We need to reload the module so it re-reads the os.environ values we set above
    reload(trigger_build_function)

    # patch trigger_ssm as moto does NOT support start_automation_execution yet
    # https://github.com/spulec/moto/blame/603f7c58a230919da3ee836575351366e46cc26c/IMPLEMENTATION_COVERAGE.md#L4022
    mock_trigger_ssm = MagicMock(return_value=mock_automation_execution_id)
    monkeypatch.setattr('trigger_build.trigger_build_function.trigger_ssm', mock_trigger_ssm)

    if pipeline_override_ami:
        ami_id = pipeline_override_ami
    else:
        # Setup mock Public AMI (we need to create a AMI and modify launch permissions)
        # 1. Create a mock SOE image from a instance
        ec2_client = boto3.client('ec2', region_name=CONST_REGION)
        run_ec2_response = ec2_client.run_instances(ImageId='ami-12345678', MaxCount=1, MinCount=1)
        instance_id = run_ec2_response['Instances'][0]['InstanceId']
        print(instance_id)
        create_ami_response = ec2_client.create_image(
            Description='Moto unit test image 1',
            InstanceId=instance_id,
            Name=soe_image_name
        )
        ami_id = create_ami_response['ImageId']

        # 2. Make mock SOE image Public
        exec_user_id = '123456789012'
        # We need to override the EXEC_USERS in the actual module as moto does not support 'all' yet
        # https://github.com/spulec/moto/blob/d8dbc6a49ccf969f50ed3f7b52f341db3a7715f0/moto/ec2/models.py#L1190
        monkeypatch.setattr('trigger_build.trigger_build_function.EXEC_USERS', exec_user_id)
        modify_image_response = ec2_client.modify_image_attribute(
            Attribute='launchPermission',
            ImageId=ami_id,
            OperationType='add',
            UserIds=[exec_user_id],
            UserGroups=['all']
        )
        print("modify_image_response")
        print(modify_image_response)

    # Setup Input
    event = {}
    context = ContextMock()

    if event_override_ami:
        event['OverrideAMI'] = event_override_ami
        ami_id = event_override_ami

    # Test Lambda handler
    if isinstance(expected_error, type):
        with pytest.raises(expected_error) as excinfo:
            trigger_build_function.lambda_handler(event, context)
        #TODO: Improve the error handling in the lambda_handler
        assert exception_message in str(excinfo.value)
        mock_trigger_ssm.assert_not_called()
    else:
        output_event = trigger_build_function.lambda_handler(copy.deepcopy(event), context)
        print("output_event")
        print(output_event)

        # Verify the output
        assert output_event != event # Assert that the event has been modified
        assert output_event["BuildAutomationExecutionId"] == mock_automation_execution_id

        mock_trigger_ssm.assert_called_with(
            CONST_SOL_NAMING, CONST_REGION, ssm_document, soe_type, ami_id
        )
