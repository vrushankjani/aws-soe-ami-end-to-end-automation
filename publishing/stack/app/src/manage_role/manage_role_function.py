'''

This module creates/manages an IAM role used by service owners for access to SSM parameter store to retrieve the SOE AMI ID.

'''
import json
import os
from datetime import datetime

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
solution_naming = os.environ['SolutionNaming']
region = os.environ['Region']
soe_type = os.environ['SOEType']

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''
    local_account_id = context.invoked_function_arn.split(":")[4]

    print("Event: " + json.dumps(event))
    account_ids = os.environ['AccountIDs'].split(',')

    try:
        # Step 1
        access_role_output = access_role(solution_naming, region, local_account_id, account_ids, soe_type)
        print(access_role_output)
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def access_role(solution_naming, region, local_account_id, account_ids, soe_type):

    '''
        Create and update IAM role used my service owners to access SOE AMI ID in SSM parameter store
    '''

    client = boto3.client('iam', region_name=region)
    role_name = (solution_naming + "-" + soe_type + "-soe-service-iam-role")
    role_policy_name = (solution_naming + "-" + soe_type + "-soe-service-iam-policy")

    try:

        # Check if role already exists
        roles = client.list_roles(
            PathPrefix='/service/'
        )
        print(roles)

        role_exists = False
        for role in roles['Roles']:
            if role['RoleName'] == role_name:
                print("Role " + role_name + " Exists")
                role_exists = True

        if account_ids:
            if role_exists:
                print("Updating IAM role " + role_name)
                accounts = []
                for account_id in account_ids:
                    print('Account: ' + account_id)
                    template = ("arn:aws:iam::" + account_id + ":root")
                    template_format = json.dumps(template).strip('"')
                    accounts.append(template_format)

                assume_role_policy_document = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": accounts,
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }

                role_response = client.update_assume_role_policy(
                    RoleName=role_name,
                    PolicyDocument=json.dumps(assume_role_policy_document)
                )

            # If not exist then create the role and policy
            else:
                print("Creating IAM role " + role_name)
                accounts = []
                for account_id in account_ids:
                    print('Account:' + account_id)
                    template = ("arn:aws:iam::" + account_id + ":root")
                    template_format = json.dumps(template).strip('"')
                    accounts.append(template_format)

                assume_role_policy_document = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": accounts,
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }

                role_response = client.create_role(
                    Path='/service/',
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                    Description='IAM Role used by service owners to retrieve SOE AMI',
                )

                role_policy_document = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "ssm:GetParameters",
                            "Resource": ("arn:aws:ssm:" + region + ":" + local_account_id + ":parameter/" + solution_naming + "/" + soe_type + "/*"),
                            "Effect": "Allow"
                        }
                    ]
                }

                policy_response = client.create_policy(
                    PolicyName=role_policy_name,
                    Path='/service/',
                    PolicyDocument=json.dumps(role_policy_document),
                    Description=(role_name + "-policy")
                )

                policy_arn = policy_response['Policy']['Arn']
                client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return role_response
