'''

This module updates the given parameter with the given value

This is called from CodePipeline invoke Lambda action
https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html#how-to-lambda-more-samples-cf

'''
import json
import os
from datetime import datetime

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
region = os.environ['Region']

codepipeline_client = boto3.client('codepipeline')

# Copied Sample Python Code from
# https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html#actions-invoke-lambda-function-samples-python-cloudformation
def put_job_success(job, message):
    """Notify CodePipeline of a successful job

    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status

    Raises:
        Exception: Any exception thrown by .put_job_success_result()

    """
    print('Putting job success')
    print(message)
    codepipeline_client.put_job_success_result(jobId=job)


# Copied Sample Python Code from
# https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html#actions-invoke-lambda-function-samples-python-cloudformation
def put_job_failure(job, message):
    """Notify CodePipeline of a failed job

    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status

    Raises:
        Exception: Any exception thrown by .put_job_failure_result()

    """
    print('Putting job failure')
    print(message)
    codepipeline_client.put_job_failure_result(jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})


# Copied and modified Sample Python Code from
# https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html#actions-invoke-lambda-function-samples-python-cloudformation
def get_user_params(job_data, required_params=None):
    """Decodes the JSON user parameters and validates the required properties.

    Args:
        job_data: The job data structure containing the UserParameters string which should be a valid JSON structure

    Returns:
        The JSON parameters decoded as a dictionary.

    Raises:
        Exception: The JSON can't be decoded or a property is missing.

    """
    try:
        # Get the user parameters which contain the stack, artifact and file settings
        user_parameters = job_data['actionConfiguration']['configuration']['UserParameters']
        print("UserParameters: '%s' (%s)" % (str(user_parameters), type(user_parameters)))
    except Exception as e:
        raise Exception('UserParameters could not be retrieved from job_data "%s"' % job_data, e)

    try:
        decoded_parameters = json.loads(user_parameters)
    except Exception as e:
        # We're expecting the user parameters to be encoded as JSON
        # so we can pass multiple values. If the JSON can't be decoded
        # then fail the job with a helpful message.
        raise Exception('UserParameters "%s" could not be decoded as JSON' % user_parameters, e)

    if required_params:
        for required_param in required_params:
            if required_param not in decoded_parameters:
                # Validate that the required_param is provided, otherwise fail the job
                # with a helpful message.
                raise Exception("Your UserParameters JSON is missing '%s'" % required_param)

    return decoded_parameters


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

        return(current_value)

    except botocore.exceptions.ClientError as e:
        print(e)
        raise e


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

        return(json.dumps(version_id))

    except botocore.exceptions.ClientError as e:
        print(e)
        raise e
