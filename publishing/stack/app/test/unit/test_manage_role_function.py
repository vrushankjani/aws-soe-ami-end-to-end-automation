"""
Test get_accounts_function
"""
import copy
import json
from test import ContextMock, CONST_REGION, CONST_SOE_TYPE, CONST_SOL_NAMING

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_iam

from manage_role.manage_role_function import lambda_handler


@pytest.mark.parametrize("test_role_creation, account_ids,expected_error", [
    # Test the creation of new roles
    (True, None, TypeError), # None
    (True, '', None), # empty account list as a str
    (True, [], None), # empty account list
    (True, '123456789012', None), # Single account id string
    (True, ['123456789012'], None), # Single account id list
    (True, ['123456789012', '123456789012'], None), # Duplicate account ids
    (True, ['123456789012', '098765432101'], None), # Different account ids
    # Test the update of existing roles
    (False, None, TypeError), # None
    (False, '', None), # empty account list as a str
    (False, [], None), # empty account list
    (False, '123456789012', None), # Single account id string
    (False, ['123456789012'], None), # Single account id list
    (False, ['123456789012', '123456789012'], None), # Duplicate account ids
    (False, ['123456789012', '098765432101'], None), # Different account ids
])
@mock_iam
def test_lambda_handler_new_roles(test_role_creation, account_ids, expected_error):
    """Test get_accounts_function.lambda_handler to return all account ids"""

    iam_client = boto3.client('iam', region_name=CONST_REGION)
    role_name = (CONST_SOL_NAMING + "-" + CONST_SOE_TYPE + "-soe-service-iam-role")

    if test_role_creation:
        # Verify role does not exist
        with pytest.raises(ClientError) as excinfo:
            iam_client.get_role(RoleName=role_name)
        assert 'Role {} not found'.format(role_name) in str(excinfo.value)
    else:
        # Create the role before the lambda_handler to test the update
        init_policy_doc = json.dumps({
            "Version": "2012-10-17",
            "Statement": []
        })
        role = iam_client.create_role(
            Path='/service/',
            RoleName=role_name,
            AssumeRolePolicyDocument=init_policy_doc,
            Description='Unit Test initialised role'
        )
        print('role')
        print(role)
        role_response = iam_client.get_role(RoleName=role_name)
        assert role_response['Role']['RoleName'] == role_name
        role_policy_statements = role_response['Role']['AssumeRolePolicyDocument']['Statement']
        assert not role_policy_statements # set to [] in above policy doc

    # Inputs for Lambda handler
    event = {'Accounts': account_ids}
    context = ContextMock()

    # Test Lambda handler
    if expected_error:
        with pytest.raises(expected_error) as excinfo:
            lambda_handler(event, context)
        assert "'NoneType' object is not iterable" in str(excinfo.value)
    else:
        output_event = lambda_handler(copy.deepcopy(event), context)

        # Assert that the event is not modified
        assert output_event == event

        # Verify the role has been created/updated correctly
        role_response = iam_client.get_role(RoleName=role_name)
        assert role_response['Role']['RoleName'] == role_name
        role_policy_statements = role_response['Role']['AssumeRolePolicyDocument']['Statement']
        assert len(role_policy_statements) == 1
        assert role_policy_statements[0]['Action'] == 'sts:AssumeRole'
        assert role_policy_statements[0]['Effect'] == 'Allow'
        principal_accounts = ["arn:aws:iam::" + account_id + ":root" for account_id in account_ids]
        assert role_policy_statements[0]['Principal']['AWS'] == principal_accounts
