"""
Test trigger_test_function
"""
import copy
from importlib import reload
from test import ContextMock

from mock import call, patch

from trigger_test import trigger_test_function

MOCK_TEST_AUTOMATION_EXECUTION_ID = 'mock_test_automation_execution_id'
MOCK_AMI_ID = 'ami-68686868'


def mock_ssm_client(operation, args): # pylint: disable=unused-argument
    """Mock's the boto base client to control the ssm client methods NOT supported by moto"""
    if operation == 'GetAutomationExecution': # For get_ami
        return {
            'AutomationExecution': {
                'Outputs': {
                    'createImage.ImageId': [MOCK_AMI_ID]
                }
            }
        }
    elif operation == 'StartAutomationExecution': # For trigger_ssm
        return {'AutomationExecutionId': MOCK_TEST_AUTOMATION_EXECUTION_ID}
    else:
        raise ValueError("Unsupported operation for '%s', please mock if required" % operation)


@patch('botocore.client.BaseClient._make_api_call')
def test_lambda_handler(mock_boto_client, monkeypatch):
    """Test trigger_test_function.lambda_handler"""

    # Setup mock input
    mock_build_automation_execution_id = 'mock_build_automation_execution_id'
    mock_instance_id = 'i-12341234'
    ssm_document = 'SSMDocument'

    # Set Environment Variables
    monkeypatch.setenv("SSMDocument", ssm_document)
    # We need to reload the module so it re-reads the os.environ values we set above
    reload(trigger_test_function)

    # patch trigger_ssm as moto does NOT support start_automation_execution yet
    # https://github.com/spulec/moto/blame/603f7c58a230919da3ee836575351366e46cc26c/IMPLEMENTATION_COVERAGE.md#L4022
    # mock_boto_client = MagicMock(return_value=MOCK_TEST_AUTOMATION_EXECUTION_ID)
    mock_boto_client.side_effect = mock_ssm_client

    # Setup Input
    event = {
        'BuildAutomationExecutionId': mock_build_automation_execution_id,
        'InstanceID': mock_instance_id
    }
    context = ContextMock()

    # Test Lambda handler
    output_event = trigger_test_function.lambda_handler(copy.deepcopy(event), context)
    print("output_event")
    print(output_event)

    # Verify the output
    assert output_event != event # Assert that the event has been modified
    assert output_event["BuildInstanceID"] == mock_instance_id
    assert output_event["TestAutomationExecutionId"] == MOCK_TEST_AUTOMATION_EXECUTION_ID
    assert output_event["AMI"] == MOCK_AMI_ID

    # Assert the boto client mock is called exactly as expected
    assert mock_boto_client.call_count == 2
    expected = [
        call('GetAutomationExecution', {
            'AutomationExecutionId': mock_build_automation_execution_id
        }),
        call('StartAutomationExecution', {
            'DocumentName': ssm_document,
            'Parameters': {'sourceAMIid': [MOCK_AMI_ID]}
        })
    ]
    assert mock_boto_client.call_args_list == expected
