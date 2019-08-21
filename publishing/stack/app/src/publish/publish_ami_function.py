'''

This module publishes the next ami as the latest ami in ssm paramter store, this increments the version for the same parameter store. It also shares the AMI with latest account IDs.

'''
import json
import os
from datetime import datetime

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
region = os.environ['Region']
next_ami_ssm_param = os.environ['NextAMIParam']
latest_ami_ssm_param = os.environ['LatestAMIParam']


def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    try:
        # Step 1 - Get the next AMI id to publish
        next_ami_id = get_ssm_param(region, next_ami_ssm_param)
        # TODO: Verify the AMI_D is a valid format
        instance_id_ssm_param = '/ami-baking-lnx-amzn-soe/lnx-amzn/instanceId'
        instance_id = get_ssm_param(region, instance_id_ssm_param)

        # Step 2 - Share the AMI with target account_ids
        account_ids = os.environ['AccountIDs'].split(',')

        share_ami_output = share_ami(region, next_ami_id, account_ids)
        print("Permission update ouput: '" + share_ami_output + "'")

        # Step 3 - Update latestAmi with nextAmi once sharing is successful
        publish_output = update_ssm_param(region, latest_ami_ssm_param, next_ami_id)
        print("SSM Parameter store '" + latest_ami_ssm_param + "' updated with AMI '" + next_ami_id + "' version '" + publish_output + "'")

        event['SsmParamVersion'] = publish_output
        event['SsmParam'] = latest_ami_ssm_param
        event['AMI'] = next_ami_id
        event['BuildInstanceID'] = instance_id
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def share_ami(region, ami, account_ids):

    '''
        Share the AMI with account ids
    '''

    try:
        client = boto3.client('ec2', region_name=region)

        response = client.modify_image_attribute(
            Attribute='launchPermission',
            ImageId=ami,
            OperationType='add',
            UserIds=account_ids,
        )

        return json.dumps(response)

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc


def get_ssm_param(region, ssm_param):

    '''
        Get the SSM Parameter value
    '''

    try:
        client = boto3.client('ssm', region_name=region)

        # Get current latest parameter value
        get_parameter_response = client.get_parameter(
            Name=ssm_param,
        )
        current_value = get_parameter_response['Parameter']['Value']

        print("Retrieved SSM Param '" + ssm_param + "' with value '" + current_value + "'")

        return current_value

    except botocore.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] == "ParameterNotFound":
            print("Parameter '"+ssm_param+"' does not exist. Returning empty value")
            return ""
        print(exc)
        raise exc

def update_ssm_param(region, ssm_param, new_value):

    '''
        Update SSM Parameter with new value
    '''

    try:
        client = boto3.client('ssm', region_name=region)

        # Get current value
        current_value = get_ssm_param(region, ssm_param)

        print("Updating '" + ssm_param + "' with '" + new_value + "' was '" + current_value + "'")

        put_parameter_response = client.put_parameter(
            Name=ssm_param,
            Value=new_value,
            Type='String',
            Overwrite=True
        )

        version_id = put_parameter_response['Version']

        return json.dumps(version_id)

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc
