'''

This module checks the status of a ssm automation execution and takes actions based on success or failure.

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

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    build_automation_execution_id = event['BuildAutomationExecutionId']

    try:
        # Step 1
        state = check_ssm(region, build_automation_execution_id)
        print("State: " + state)
        # Step 2
        instance_id = get_instance_id(region, build_automation_execution_id)
        print("Instance ID: " + instance_id)
        event["BuildStatus"] = state
        event["InstanceID"] = instance_id
        event["CheckType"] = "ssm_build"
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def check_ssm(region, build_automation_execution_id):

    '''
        Check Build SSM automation
    '''

    client = boto3.client('ssm', region_name=region)

    try:
        ssm_response = client.get_automation_execution(
            AutomationExecutionId=build_automation_execution_id
        )
        state_pending = False
        state_in_progress = False
        state_waiting = False
        state_success = False
        state_cancelling = False
        state_failed = False
        state_cancelled = False
        state_timed_out = False

        if ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Pending':
            state_pending = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'InProgress':
            state_in_progress = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Waiting':
            state_waiting = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Success':
            state_success = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Cancelling':
            state_cancelling = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Failed':
            state_failed = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'Cancelled':
            state_cancelled = True
        elif ssm_response['AutomationExecution']['AutomationExecutionStatus'] == 'TimedOut':
            state_timed_out = True
        else:
            print("State Unknown")

        if state_pending or state_in_progress or state_waiting:
            state = 'running'
        elif state_success:
            state = 'succeeded'
        elif state_cancelling or state_failed or state_cancelled or state_timed_out:
            state = 'failed'
        else:
            state = 'unknown'

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return state

def get_instance_id(region, build_automation_execution_id):

    '''
        Get instance ID for build instance
    '''

    client = boto3.client('ssm', region_name=region)

    try:
        ssm_response = client.get_automation_execution(
            AutomationExecutionId=build_automation_execution_id
        )

        scan_output = ssm_response['AutomationExecution']['Outputs']['startInstances.InstanceIds'][0]
        scan_output_format = scan_output.strip()
        instance_id = scan_output_format.strip('"')

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return instance_id
