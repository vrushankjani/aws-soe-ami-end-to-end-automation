'''

This module triggers a SSM automation build for a SOE AMI.

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
ssm_document = os.environ['SSMDocument']
soe_type = os.environ['SOEType']
ami_pattern = os.environ['AMIPattern']
ami_owner = os.environ['AMIOwner']
pipeline_override_ami = os.environ['OverrideAMI']

# To override from unit test to work around moto
EXEC_USERS = 'all'

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    try:
        # Check if there is override AMI is set in the event
        if 'OverrideAMI' in event:
            event_override_ami = event['OverrideAMI']
            if pipeline_override_ami:
                print("Overriding the Pipeline level OverrideAMI '%s' with event OverrideAMI '%s'" % (pipeline_override_ami, event_override_ami))
            else:
                print("Overriding the AMI Pattern '%s' with event OverrideAMI '%s'" % (ami_pattern, event_override_ami))
            override_ami = event_override_ami
        else:
            override_ami = pipeline_override_ami

        # Step 1
        source_ami_id = get_ami(ami_pattern, region, override_ami, ami_owner)
        print("AMI ID: " + source_ami_id)

        # Step 2
        build_execution_id = trigger_ssm(solution_naming, region, ssm_document, soe_type, source_ami_id)
        print("BuildAutomationExecutionId: " + build_execution_id)
        event['BuildAutomationExecutionId'] = build_execution_id
        event['SourceAMI'] = source_ami_id
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def get_ami(ami_pattern, region, override_ami, ami_owner):

    '''
        Get latest market place AMI for the SOE Type
    '''

    global EXEC_USERS
    client = boto3.client('ec2', region_name=region)

    try:
        if override_ami == "":

            print("Get available images matching '%s' with owner '%s'" % (ami_pattern, ami_owner))
            images = client.describe_images(
                ExecutableUsers=[
                    EXEC_USERS,
                ],
                Filters=[
                    {
                        'Name': 'name',
                        'Values': [
                            ami_pattern,
                        ]
                    },
                    {
                        'Name': 'state',
                        'Values': [
                            'available',
                        ]
                    },
                ],
                Owners=[
                    ami_owner,
                ]
            )
            print(images)
            image_date_list = []
            for image in images['Images']:
                date = image['CreationDate']
                image_date_list.append(date)

            print("Date list: " + json.dumps(image_date_list))
            latest_date = max(image_date_list)
            print("Latest date: " + latest_date)

            for image in images['Images']:
                if image['CreationDate'] == latest_date:
                    print("Latest AMI ID: " + image['ImageId'])
                    ami_id = image['ImageId']

        else:
            if override_ami.startswith('ami-'):
                ami_id = override_ami
                print("Overriding AMI image: '%s'" % ami_id)
            else:
                raise ValueError("Invalid Override AMI format set: '%s'" % override_ami)

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return ami_id

def trigger_ssm(solution_naming, region, ssm_document, soe_type, ami_id):

    '''
        Trigger Build SSM automation
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
