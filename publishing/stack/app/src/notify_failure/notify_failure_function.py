'''

This module deletes stale running instances from failed failed ssm runs and notifies on failure.
https://api.slack.com/methods/chat.postMessage
https://api.slack.com/docs/message-attachments
https://api.slack.com/docs/message-formatting
https://htmlcolorcodes.com/
https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-repository-email.html#how-to-repository-email-using

'''
import json
import logging
import os
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
region = os.environ['Region']
exception_list = os.environ['VulnerabilityExceptionsList']
solution_naming = os.environ['SolutionNaming']
os_type = os.environ['OSType']
operating_system = os.environ['OS']
slack_channel = os.environ['SlackChannel']
slack_url = os.environ['SlackURL']
slack_icon = os.environ['SlackIcon']
enable_slack = os.environ['EnableSlackIntegration']
environment = os.environ['Environment']

## Clients
ssm_client = boto3.client('ssm', region_name=region) # pylint: disable=invalid-name
inspector_client = boto3.client('inspector') # pylint: disable=invalid-name
ec2_client = boto3.client('ec2', region_name=region) # pylint: disable=invalid-name

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))
    logger.info("Event: " + str(event))
    message = event
    logger.info("Message: " + str(message))

    if enable_slack == 'false':
        # Skip notifying slack channel
        logger.info("enable_slack is set to 'false'. Skipping this function")
        event["Notification"] = "Success"
        return event
    else:
        try:
            instance_id = event['InstanceID']
            failure_on = event['CheckType']
            account_id = (boto3.client('sts').get_caller_identity()['Account'])
            global exception_list
            exception_list = event['IgnoreFindings'] if 'IgnoreFindings' in event else None
            keep_ec2 = event['KeepTestInstance'] in ['True', 'FailedOnly'] if 'KeepTestInstance' in event else False

            # Step 1
            if keep_ec2:
                print("KeepTestInstance is '%s'. Skipping termination of '%s'" % (event['KeepTestInstance'], instance_id))
            else:
                delete_instance_output = delete_instance(region, instance_id)
                print(delete_instance_output)

            # Step 2
            if 'Action' in event:
                action = event['Action']
            else:
                action = 'UNKNOWN_ACTION'

            if failure_on == "ssm_build":
                slack_message = get_failure_ssm_build(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment)
            elif failure_on == "ssm_test":
                purge_output = purge_ami(region, event)
                print(purge_output)
                slack_message = get_failure_ssm_test(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment)
            elif failure_on == "inspector":
                purge_output = purge_ami(region, event)
                print(purge_output)
                slack_message = get_failure_inspector(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment)
            elif failure_on == "inspec":
                purge_output = purge_ami(region, event)
                print(purge_output)
                slack_message = get_failure_inspec(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment)
            else:
                purge_output = purge_ami(region, event)
                print(purge_output)
                slack_message = get_vulnerabilies(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment)

            # Step 3
            notify_slack(slack_url, slack_message)

            event["Notification"] = "Success"
            return event

    except BaseException as exc:
        print(exc)
        raise exc


def delete_instance(region, instance_id):

    '''
        Delete SSM instance due to failed run.
    '''

    client = boto3.client('ec2', region_name=region)

    try:
        response = client.describe_instances(
            InstanceIds=[
                instance_id,
            ]
        )
        print(response)

        try:
            instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
        except:
            instance_state = "Failed to create"

        if instance_state == 'running':
            response = client.terminate_instances(
                InstanceIds=[
                    instance_id,
                ]
            )
            output = ("Terminated Instance: " + json.dumps(instance_id))
        else:
            output = ("No Instance to Terminate or Failed to Create")

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return output


def get_failure_ssm_build(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment):

    '''
        Get ssm build failure message
    '''

    try:
        print("SSM Build Failure")
        execution_id = event['BuildAutomationExecutionId']
        url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#ExecutionOutputs:AutomationExecutionId=execution_id")
        link_to_service = '<%s|%s>' % (url, execution_id)

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-build-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    # "author_name": "SSM Build Failure",
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'SSM Build Failure',
                    'color': "#FF0000",
                    'text': 'SSM Build Execution Failed',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'SSM Build', 'value': link_to_service, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True},
                    ]
                }
            ]
        }
        print(slack_message)

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return slack_message


def get_failure_ssm_test(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment):

    '''
        Get ssm test failure message
    '''

    try:
        print("SSM Test Failure")
        execution_id = event['TestAutomationExecutionId']
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Parameters']['sourceAMIid'][0]
        print(ami_id)
        url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#ExecutionOutputs:AutomationExecutionId=execution_id")
        link_to_service = '<%s|%s>' % (url, execution_id)

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-build-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    # "author_name": "SSM Test Failure",
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'SSM Test Failure',
                    'color': "#FF0000",
                    'text': 'SSM Test Execution Failed',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'SSM Build', 'value': link_to_service, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True},
                        {'title': 'Deleted AMI', 'value': ami_id, 'short': True},
                    ]
                }
            ]
        }

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return slack_message


def get_failure_inspector(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment):

    '''
        Get inspector failure message
    '''

    try:
        print("Inspector Failure")
        execution_id = event['TestAutomationExecutionId']
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Parameters']['sourceAMIid'][0]
        print(ami_id)
        scan_output = ssm_response['AutomationExecution']['Outputs']['runVulnerabilityScan.Output'][0]
        scan_output_format = scan_output.strip()
        inspector_assessment_run_arn = scan_output_format.strip('"')
        assesment_run_response = inspector_client.describe_assessment_runs(
            assessmentRunArns=[
                inspector_assessment_run_arn,
            ]
        )
        state = assesment_run_response['assessmentRuns'][0]['state']
        print(state)
        url = ("https://" + region + ".console.aws.amazon.com/inspector/home?region=" + region + "#/run")

        link_to_service = '<%s|Link>' % (url)

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-build-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    # "author_name": "Inspector Scan Failure",
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'Inspector Scan Failure',
                    'color': "#FF0000",
                    'text': ("Inspector Assesment Run " + state),
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'Inspector Assesment', 'value': link_to_service, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True},
                        {'title': 'Deleted AMI', 'value': ami_id, 'short': True},
                    ]
                }
            ]
        }


    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return slack_message

def get_failure_inspec(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment):

    '''
        Get Inspec failure message
    '''

    try:
        print("InSpec Compliance Test Failure")
        execution_id = event['TestAutomationExecutionId']
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Parameters']['sourceAMIid'][0]
        print(ami_id)
        url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#ExecutionOutputs:AutomationExecutionId=execution_id")
        link_to_service = '<%s|%s>' % (url, execution_id)

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-build-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    # "author_name": "InSpec Failure",
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'InSpec Compliance Failure',
                    'color': "#FF0000",
                    'text': 'InSpec Compliance Test Failed',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'SSM Build', 'value': link_to_service, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True},
                        {'title': 'Deleted AMI', 'value': ami_id, 'short': True},
                    ]
                }
            ]
        }

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return slack_message


def is_breaking_finding(findings_detail):
    """
        Determine if a finding is a breaking failure.
    """
    # Ignore non High severity
    if 'severity' in findings_detail and findings_detail['severity'] != 'High':
        logger.debug("Finding '%s' has Severity '%s', ignoring.", findings_detail['id'], findings_detail['severity'])
        return False

    # Ignore CIS Level 2
    for attr in findings_detail['attributes']:
        if attr['key'] == "CIS_BENCHMARK_PROFILE":
            # Ignore Level 2 as we are currently using CIS Hardened AMI to Level 1 only
            if "Level 2" in attr['value']:
                logger.debug("Finding '%s' has CIS Profile '%s', ignoring.", findings_detail['id'], attr['value'])
                return False

    if exception_list and findings_detail['id'] in exception_list:
        logger.debug("Finding '%s' is in VulnerabilityExceptionsList, ignoring.", findings_detail['id'])
        return False

    # Every other findings are a breaking failure
    logger.error("Finding '%s' is a breaking failure.", findings_detail['id'])
    return True


def get_vulnerabilies(failure_on, event, action, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, environment):

    '''
        Get vulnerability message
    '''

    try:
        print("Vulnerability Scan Failure")
        execution_id = event['TestAutomationExecutionId']
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Parameters']['sourceAMIid'][0]
        print(ami_id)
        scan_output = ssm_response['AutomationExecution']['Outputs']['runVulnerabilityScan.Output'][0]
        scan_output_format = scan_output.strip()
        inspector_assessment_run_arn = scan_output_format.strip('"')

        # Do while has nextToken (true the first time)
        has_next_token = True
        all_findings_arns = []
        findings_response = {}
        next_token_kwargs = {}
        while has_next_token:
            findings_response = inspector_client.list_findings(
                assessmentRunArns=[inspector_assessment_run_arn], **next_token_kwargs
            )
            all_findings_arns += findings_response['findingArns']
            if 'nextToken' in findings_response and findings_response['nextToken']:
                next_token_kwargs = {'nextToken': findings_response['nextToken']}
            else:
                has_next_token = False

        ignored_findings = []
        breaking_findings = []
        all_findings_details = inspector_client.describe_findings(
            findingArns=all_findings_arns
        )
        # For each finding, filter down to breaking findings only
        for findings_detail in all_findings_details['findings']:
            if is_breaking_finding(findings_detail):
                breaking_findings.append(findings_detail['id'])
            else:
                ignored_findings.append(findings_detail['id'])

        url = 'https://%s.console.aws.amazon.com/inspector/home?region=%s#/finding?filter={%%22assessmentRunArns%%22:[%%20%%20"%s"]}' % (region, region, inspector_assessment_run_arn)
        link_to_service = '<%s|%s>' % (url, json.dumps(breaking_findings))

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-build-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)
        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    # "author_name": "Vulnerabilties Found",
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'Vulnerabilties Found',
                    'color': "#FF0000",
                    'text': 'Inspector Found High Vulnerabilities.',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True},
                        {'title': 'Inspector Findings (%s)' % len(breaking_findings), 'value': link_to_service, 'short': True},
                        {'title': 'Ignored Findings', 'value': "%s Findings ignored (Not High Severity or CIS Level 2)" % len(ignored_findings), 'short': True},
                        {'title': 'Deleted AMI', 'value': ami_id, 'short': True},
                    ]
                }
            ]
        }

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return slack_message


def notify_slack(slack_url, slack_message):

    '''
        Send message to slack.
    '''

    try:

        slack_message_format = json.dumps(slack_message)
        req = Request(slack_url, slack_message_format.encode('utf-8'))

        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as exc:
        logger.error("Request failed: %d %s", exc.code, exc.reason)
        raise exc
    except URLError as exc:
        logger.error("Server connection failed: %s", exc.reason)
        raise exc


def purge_ami(region, event):

    '''
        Purge AMI and snapshot for failed run
    '''

    try:
        print("Deleting AMI and snapshot")

        execution_id = event['TestAutomationExecutionId']
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=execution_id
        )
        ami_id = ssm_response['AutomationExecution']['Parameters']['sourceAMIid'][0]

        image = ec2_client.describe_images(
            ImageIds=[ami_id],
        )

        # image = ec2_client.describe_image_attribute(
        #     Attribute='blockDeviceMapping',
        #     ImageId=ami_id,
        # )

        if image['Images']:
            snapshot_id = image['Images'][0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
            ec2_client.deregister_image(ImageId=ami_id)
            ec2_client.delete_snapshot(SnapshotId=snapshot_id)
            output = ("Deleted - AMI: " + ami_id + " & Snapshot: " + snapshot_id)
        else:
            output = ("Nothing to purge. AMI: " + ami_id + " does not exist")

        return output

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc
