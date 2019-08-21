'''

This module retrives the AMI ID for the last build and runs vulnerability scanning and the InSpec Compliance test.

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
ssm_document = os.environ['SSMDocument']

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    build_automation_execution_id = event['BuildAutomationExecutionId']

    try:
        # Step 1
        event["BuildInstanceID"] = event["InstanceID"]
        print("BuildInstanceID", event["BuildInstanceID"])
        ami_id = get_ami(region, build_automation_execution_id)
        print("AMI ID:" + ami_id)

        # Step 2
        test_execution_id = trigger_ssm(region, ssm_document, ami_id)
        print("TestAutomationExecutionId: " + test_execution_id)

        event['TestAutomationExecutionId'] = test_execution_id
        event['AMI'] = ami_id
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def get_ami(region, automation_execution_id):

    '''
        Get AMI ID
    '''

    client = boto3.client('ssm', region_name=region)

    try:
        ssm_response = client.get_automation_execution(
            AutomationExecutionId=automation_execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Outputs']['createImage.ImageId'][0]

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return ami_id


def trigger_ssm(region, ssm_document, ami_id):

    '''
        Trigger test SSM automation
    '''

    client = boto3.client('ssm', region_name=region)


    try:
        ssm_response = client.start_automation_execution(
            DocumentName=ssm_document,
            Parameters={'sourceAMIid': [ami_id]}
        )
        execution_id = ssm_response['AutomationExecutionId']

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return execution_id
