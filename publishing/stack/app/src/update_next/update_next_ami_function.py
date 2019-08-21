'''

This module updates the next AMI with the latest SOE build

'''
import json
import os
import re
from datetime import datetime

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
region = os.environ['Region']
next_ami_ssm_param = os.environ['NextAMIParam']

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    try:
        # Step 1 - Get the latest build AMI ID (saved from trigger_test_function)
        next_ami_id = event['AMI']
        ami_id_regex = "^ami-([a-f0-9]+)$"
        pattern = re.compile(ami_id_regex)
        if not pattern.match(next_ami_id):
            print("NextAMIParam '" + next_ami_ssm_param + "' does not match AMI Id format '" + ami_id_regex + "'")
            raise ValueError("NextAMIParam '" + next_ami_ssm_param + "' does not match AMI Id format '" + ami_id_regex + "'")

        # Step 2 - Update nextAmi SSM parameter
        update_ssm_output = update_ssm_param(region, next_ami_ssm_param, next_ami_id)
        print("SSM Parameter store '" + next_ami_ssm_param + "' updated with AMI '" + next_ami_id + "' version '" + update_ssm_output + "'")

        # Step 3 - Update instanceId SSM parameter
        instance_id = event['BuildInstanceID']
        if instance_id:
            instance_id_ssm_param = '/ami-baking-lnx-amzn-soe/lnx-amzn/instanceId'
            update_ssm_output2 = update_ssm_param(region, instance_id_ssm_param, instance_id)
            print("SSM Parameter store '" + instance_id_ssm_param + "' updated with AMI '" + instance_id + "' version '" + update_ssm_output2 + "'")
        else:
            raise ValueError("BuildInstanceID is None")

        event["SsmParamVersion"] = update_ssm_output
        event["SsmParam"] = next_ami_ssm_param
        return event

    except BaseException as exc:
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
        else:
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

        print("Updating '%s' with '%s' was '%s'" % (ssm_param, new_value, current_value))

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
