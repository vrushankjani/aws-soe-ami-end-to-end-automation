"""Tests the get_ssm_param function.
"""

import json
import os
import pytest
import boto3
from moto import mock_ssm, mock_s3
from mock import patch, MagicMock
from serverless.ssm_param.get_ssm_param import (
    create_artifact,
    get_user_params,
    get_ssm_param,
    lambda_handler,
    put_job_failure,
    put_job_success,
    validate_param_value
)

REGION = os.environ['Region']
MODULE_PATH = 'serverless.ssm_param.get_ssm_param'


def test_get_user_params_success():
    """Tests the get_user_params function with a success scenario.
    """

    # Setup input data
    param_from = '/mock/path/from'
    param_to = '/mock/path/to'
    job_id = 1234

    # Setup input data structures
    user_params = {
        "CopyValueFrom": param_from,
        "CopyValueTo": param_to
    }
    job_data = {
        "actionConfiguration": {
            "configuration": {
                "UserParameters": json.dumps(user_params)
            }
        }
    }

    test_get_user_params_value = get_user_params(job_data)

    assert test_get_user_params_value == user_params


@mock_ssm
def test_get_ssm_param_success():
    """Tests the get_ssm_parameter function with a success scenario.
    """

    # Setup input data
    param_from = '/mock/path/from'
    param_from_value = 'from_value'

    # Setup mocked value in SSM with moto
    client = boto3.client('ssm', region_name='ap-southeast-2')
    client.put_parameter(Name=param_from, Value=param_from_value, Type='String', Overwrite=True)

    # Check the mocked value in SSM
    test_get_ssm_param_value = get_ssm_param(REGION, param_from)

    assert test_get_ssm_param_value == param_from_value


def test_create_artifact_success():
    """Tests the create_artifact function with a success scenario.
    """
    # TODO: check file contents
    # test params and filename
    test_params = {
        "CopyValueFrom": "param_from",
        "CopyValueTo": "param_to"
    }
    test_filename = 'somefile.txt'

    test_create_artifact_value = create_artifact(test_filename, test_params)

    # check file exists
    assert os.path.exists(test_create_artifact_value)


@pytest.mark.parametrize("ami_id", [
    "x",
    "ami-",
    "ami-invalid",
])
def test_validate_param_value_invalid_value(ami_id):
    """Tests the validate_param_value function with a failure scenario.
    """
    user_params = {
        "Type": "ImageId"
    }
    with pytest.raises(ValueError) as excinfo:
        validate_param_value(ami_id, user_params)
    assert "does not match" in str(excinfo.value)


@pytest.mark.parametrize("ami_id", [
    "ami-03cbaa39",
    "ami-0d5d3e27d925f3a5a",
    "ami-0e7cabde0b347dc65",
])
def test_validate_param_value_valid_value(ami_id):
    """Tests the validate_param_value function with a success scenario.
    """
    user_params = {
        "Type": "ImageId"
    }
    try:
        validate_param_value(ami_id, user_params)
    except ValueError:
        pytest.fail("Failed valid AMI test.")


def test_put_job_failure_mock_call(codepipeline_client_mock):
    """Tests the codepipeline function with a failure scenario.
    """
    job_id = 123
    message = "testing success"

    put_job_failure(job_id, message)

    codepipeline_client_mock.get_success_mock().assert_not_called()
    codepipeline_client_mock.get_failure_mock().assert_called_once_with(jobId=job_id, failureDetails={'message': message, 'type': 'JobFailed'})


def test_put_job_success_mock_call(codepipeline_client_mock):
    """Tests the codepipeline function with a success scenario.
    """
    job_id = 456
    message = "testing failure"

    put_job_success(job_id, message)

    codepipeline_client_mock.get_success_mock().assert_called_once_with(jobId=job_id)
    codepipeline_client_mock.get_failure_mock().assert_not_called()


@mock_s3
@mock_ssm
def test_lambda_handler_success(codepipeline_client_mock):
    """Tests the lambda_handler function with a success scenario.
    """

    # Setup input data
    job_id = 1234
    param_path = 'test_parameter_path'
    param_val = 'test_parameter_value'
    json_file_name = 'test_json_file_name'
    s3_bucket = 'test_bucket'
    s3_key = 'test_key'

    # Setup input data structures
    user_params = {
        "Parameter": param_path,
        "JSONFileName": json_file_name,
        "keyName": s3_key
    }
    event = {
        'CodePipeline.job': {
            'id': job_id,
            'data': {
                "actionConfiguration": {
                    "configuration": {
                        "UserParameters": json.dumps(user_params)
                    }
                },
                "outputArtifacts": [
                    {
                        "location": {
                            "type": "S3",
                            "s3Location": {
                                "objectKey": s3_key,
                                "bucketName": s3_bucket
                            }
                        },
                        "revision": None,
                        "name": "GetLatestTestAmiOutput"
                    }
                ],
                "artifactCredentials": {
                    "sessionToken": "session_token",
                    "secretAccessKey": "secret_access_key",
                    "accessKeyId": "access_key_id"
                }
            }
        }
    }

    # Setup the mock data with moto
    ssm_client = boto3.client('ssm', region_name='ap-southeast-2')
    ssm_client.put_parameter(Name=param_path, Value=param_val, Type='String', Overwrite=True)

    # Setup mock S3 bucket
    s3_client = boto3.client('s3', region_name='ap-southeast-2')
    s3_client.create_bucket(Bucket=s3_bucket)

    lambda_handler(event, None)

    # check if file exists in S3
    s3_client = boto3.client('s3', region_name='ap-southeast-2')
    test_s3_file_exists = s3_client.get_object(
        Bucket=s3_bucket,
        Key=s3_key
    )

    assert test_s3_file_exists['Body'] is not None

    # check if SSM Param is the same
    test_ssm_param_value = ssm_client.get_parameter(Name=param_path)

    # assert ssm param value to the original value
    assert test_ssm_param_value['Parameter']['Value'] == param_val

    codepipeline_client_mock.get_success_mock().assert_called_once_with(jobId=job_id)
    codepipeline_client_mock.get_failure_mock().assert_not_called()
