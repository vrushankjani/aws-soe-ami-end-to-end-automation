"""
Test check_test_function
"""
import copy
from test import ContextMock

import pytest
from mock import MagicMock, patch, call

from check_test.check_test_function import lambda_handler


@pytest.mark.parametrize("automation_execution_status, expected_build_status, ignore_test_failure", [
    # Without IgnoreTestFailure
    ('Pending', 'running', None),
    ('InProgress', 'running', None),
    ('Waiting', 'running', None),
    # ('Success', 'succeeded', None), # TODO: Expand coverage to all other cases
    ('Cancelling', 'failed', None),
    ('Failed', 'failed', None),
    ('Cancelled', 'failed', None),
    ('TimedOut', 'failed', None),
    ('Other', 'unknown', None),
    # With IgnoreTestFailure set to True
    ('Pending', 'running', 'True'),
    ('InProgress', 'running', 'True'),
    ('Waiting', 'running', 'True'),
    # ('Success', 'succeeded', 'True'), # TODO: Expand coverage to all other cases
    ('Cancelling', 'failed', 'True'),
    ('Failed', 'failed', 'True'),
    ('Cancelled', 'failed', 'True'),
    ('TimedOut', 'failed', 'True'),
    ('Other', 'unknown', 'True'),
    # With IgnoreTestFailure to False (ie. Not True with Capital T)
    ('Pending', 'running', 'False'),
    ('InProgress', 'running', 'true'), # lower case true is ignored
    ('Waiting', 'running', 'false'),
    # ('Success', 'succeeded', 'random'), # TODO: Expand coverage to all other cases
    ('Cancelling', 'failed', ''),
    ('Failed', 'failed', '1234'),
    ('Cancelled', 'failed', 'other'),
    ('TimedOut', 'failed', 'unknown'),
    ('Other', 'unknown', 'blah'),
])
@patch('botocore.client.BaseClient._make_api_call')
def test_lambda_handler(mock_get_automation_execution, automation_execution_status, expected_build_status, ignore_test_failure):
    """Test check_test_function.lambda_handler"""

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
    event = {'TestAutomationExecutionId': mock_automation_execution_id}
    context = ContextMock()

    if ignore_test_failure:
        # Set the IgnoreTestFailure event flag
        event['IgnoreTestFailure'] = ignore_test_failure
        # Update the expected status to skipped if its not succeeded or running state
        if ignore_test_failure == 'True':
            if expected_build_status in ['failed', 'unknown']:
                expected_build_status = 'skipped'

    # Test Lambda handler
    output_event = lambda_handler(copy.deepcopy(event), context)

    # Verify the output event
    assert output_event != event # Assert that the event has been modified
    assert output_event["InstanceID"] == mock_instance_id
    assert output_event["TestStatus"] == expected_build_status
    assert output_event["CheckType"] == "ssm_test"

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
