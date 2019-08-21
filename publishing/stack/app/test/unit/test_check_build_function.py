"""
Test check_build_function
"""
import copy
from test import ContextMock

import pytest
from mock import MagicMock, patch, call

from check_build.check_build_function import lambda_handler


@pytest.mark.parametrize("automation_execution_status,build_status", [
    ('Pending', 'running'),
    ('InProgress', 'running'),
    ('Waiting', 'running'),
    ('Success', 'succeeded'),
    ('Cancelling', 'failed'),
    ('Failed', 'failed'),
    ('Cancelled', 'failed'),
    ('TimedOut', 'failed'),
    ('Other', 'unknown'),
])
@patch('botocore.client.BaseClient._make_api_call')
def test_lambda_handler(mock_get_automation_execution, automation_execution_status, build_status):
    """Test check_build_function.lambda_handler"""

    # Setup mock input
    mock_state = automation_execution_status
    mock_instance_id = 'i-12345678'
    mock_automation_execution_id = 'mock_automation_execution_id'

    # patch get_automation_execution as moto does NOT support it yet
    mock_get_automation_execution.side_effect = MagicMock(return_value={
        'AutomationExecution': {
            'AutomationExecutionStatus': mock_state,
            'Outputs': {
                'startInstances.InstanceIds': ["  \"%s\"  " % mock_instance_id]
            }
        }
    })

    # Setup Input
    event = {'BuildAutomationExecutionId': mock_automation_execution_id}
    context = ContextMock()

    # Test Lambda handler
    output_event = lambda_handler(copy.deepcopy(event), context)

    # Verify the output event
    assert output_event != event # Assert that the event has been modified
    assert output_event["InstanceID"] == mock_instance_id
    assert output_event["BuildStatus"] == build_status
    assert output_event["CheckType"] == "ssm_build"

    # Verify the mocks have been called as expected
    # TODO: Update lambda_handler to call once instead of twice the exact same request
    assert mock_get_automation_execution.call_count == 2
    expected = [
        call('GetAutomationExecution', {
            'AutomationExecutionId': mock_automation_execution_id
        }),
        call('GetAutomationExecution', {
            'AutomationExecutionId': mock_automation_execution_id
        }),
    ]
    assert mock_get_automation_execution.call_args_list == expected
