'''

This module terminates the test EC2 instance

'''
import json
import os

import boto3


### Environment variables ###
region = os.environ['Region']


def terminate_test_instance(instance_id):
    '''Terminates the test EC2 instance.
    '''
    ec2_client = boto3.client('ec2', region_name=region)
    try:
        response = ec2_client.terminate_instances(
            InstanceIds=[instance_id]
        )
    except:
        raise
    return response


def lambda_handler(event, context):
    '''Runs the function and returns the output.
    '''
    print("Event: " + json.dumps(event))

    keep_ec2 = event['KeepTestInstance'] == 'True' if 'KeepTestInstance' in event else False
    instance_id = event['InstanceID']

    if keep_ec2:
        print("KeepTestInstance is True. Skipping termination of '%s'" % instance_id)
    else:
        terminate_response = terminate_test_instance(instance_id)
        print(terminate_response)

    return event
