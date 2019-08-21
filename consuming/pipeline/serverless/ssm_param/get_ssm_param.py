'''

This module updates the given parameter with the given value

This is called from CodePipeline invoke Lambda action
https://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html#how-to-lambda-more-samples-cf

'''
import json
import os
import re
from datetime import datetime

import boto3
import botocore
import tempfile
import shutil
from zipfile import ZipFile
from boto3.session import Session

print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
region = os.environ['Region']
fetch_parameter_role_arn = os.environ['FetchParameterRemoteRoleArn']

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
    codepipeline_client.put_job_failure_result(
        jobId=job,
        failureDetails={'message': message, 'type': 'JobFailed'}
    )


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

        client = boto3.client('sts')
        session_name = "fetch-parameter-session"
        response = client.assume_role(RoleArn=fetch_parameter_role_arn, RoleSessionName=session_name)
        
        session = Session(aws_access_key_id=response['Credentials']['AccessKeyId'],
                        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                        aws_session_token=response['Credentials']['SessionToken'])
                        
        client = session.client('ssm', region_name=region)

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


def create_artifact(filename, json_data):
    """
    Creates a zip file with a single file named with the given filename and
    content set to the json_data.
    """
    artifact_dir = tempfile.mkdtemp()
    artifact_file = artifact_dir + '/files/' + filename
    zipped_artifact_file = artifact_dir + '/artifact.zip'
    try:
        # Clean up temp directory, ignore any errors
        shutil.rmtree(artifact_dir+'/files/')
    except Exception:
        pass
    try:
        # Clean up target artifact file if it already exists
        os.remove(zipped_artifact_file)
    except Exception:
        pass

    # Create the directory, write to it and zip it
    os.makedirs(artifact_dir+'/files/')
    with open(artifact_file, 'w') as outfile:
        json.dump(json_data, outfile)
    with ZipFile(zipped_artifact_file, 'w') as zipped_artifact:
        zipped_artifact.write(artifact_file, os.path.basename(artifact_file))

    return zipped_artifact_file


def validate_param_value(value, user_params):
    """
    'Type' is optional for UserParameters.

    If provided, validate the value against the validation rule mapped to 'Type'
    """
    if "Type" in user_params:
        value_type = user_params['Type']
        if value_type == "ImageId":
            # TODO: cicd accounts cannot describe ec2 images - APO-991
            # try:
            #     ec2 = boto3.resource('ec2')
            #     image = ec2.Image(value)
            # except Exception as e:
            #     print("Image '%s' NOT Found. %s" % (value, e))
            #     raise ValueError("Image '%s' NOT Found. %s" % (value, e))
            # if image.state != 'available':
            #     print("Image '%s' exists but is not available, it's state is '%s'" % (value, image.state))
            #     raise Exception("Image '%s' exists but is not available, it's state is '%s'" % (value, image.state))

            # For now, just do a regex pattern matching
            ami_id_regex = "^ami-([a-f0-9]+)$"
            pattern = re.compile(ami_id_regex)
            if not pattern.match(value):
                print("UserParameters '" + value + "' does not match AMI Id format '" + ami_id_regex + "'")
                raise ValueError("UserParameters '" + value + "' does not match AMI Id format '" + ami_id_regex + "'")
    else:
        print("No SSM Param 'Type' provided in UserParameters. Skipping validation")


def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    try:
        # Extract the Job ID
        job_id = event['CodePipeline.job']['id']

        # Extract the Job Data
        job_data = event['CodePipeline.job']['data']

        # Extract the UserParameters
        user_params = get_user_params(job_data, ['Parameter', 'JSONFileName', 'keyName'])
        ssm_param_path = user_params['Parameter']
        output_json_file_name = user_params['JSONFileName']
        output_json_key_name = user_params['keyName']

        # Get parameter
        ssm_param_value = get_ssm_param(region, ssm_param_path)
        print("SSM Parameter store '" + ssm_param_path + "' has value '" + ssm_param_value + "'")

        # Extract the target output details & credentials for cloudformation
        output_artifact = job_data['outputArtifacts'][0]
        output_bucket = output_artifact['location']['s3Location']['bucketName']
        output_key = output_artifact['location']['s3Location']['objectKey']
        output_name = output_artifact['name']
        credentials = job_data['artifactCredentials']
        key_id = credentials['accessKeyId']
        key_secret = credentials['secretAccessKey']
        session_token = credentials['sessionToken']
    except Exception as e:
        print(e)
        put_job_failure(
            job_id,
            "Failed to retrieve required user inputs from event due to '%s'" % (e))
        raise e

    try:
        validate_param_value(ssm_param_value, user_params)
    except Exception as e:
        print(e)
        value_type = user_params['Type'] if 'Type' in user_params else "UNKNOWN"
        put_job_failure(job_id, "Failed to validate param '%s' with value '%s' as a '%s' Type due to '%s'" % (ssm_param_path, ssm_param_value, value_type, e))
        raise e

    try:
        # Create the output file and upload to s3 bucket
        output_data = {
            output_json_key_name: ssm_param_value
        }
        output_artifact = create_artifact(output_json_file_name, output_data)
        print("Created artifact '%s' for output '%s' with JSONFileName '%s' and keyName '%s' for Fn::Param" % (output_artifact, output_name, output_json_file_name, output_json_key_name))
        s3_client = boto3.client(
            's3',
            aws_access_key_id=key_id,
            aws_secret_access_key=key_secret,
            aws_session_token=session_token,
            region_name=region
        )
        print("Uploading file '%s' to s3 bucket '%s' with s3 key '%s'" % (output_artifact, output_bucket, output_key))
        s3_client.upload_file(output_artifact, output_bucket, output_key)

        # Mark the code pipeline job as success
        # TODO: Update with more info of uploading to s3
        put_job_success(job_id, "Successfully retrieved SSM param '%s' with value '%s' and uploaded output for '%s'" % (ssm_param_path, ssm_param_value, output_name))
    except Exception as e:
        print(e)
        put_job_failure(job_id, "Failed to retrieve value for SSM param '%s' due to '%s'" % (ssm_param_path, e))
        raise e

