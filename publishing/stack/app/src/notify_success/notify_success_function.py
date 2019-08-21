'''

This module notifies on success.

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


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
region = os.environ['Region']
solution_naming = os.environ['SolutionNaming']
os_type = os.environ['OSType']
operating_system = os.environ['OS']
slack_channel = os.environ['SlackChannel']
slack_url = os.environ['SlackURL']
slack_icon = os.environ['SlackIcon']
enable_slack = os.environ['EnableSlackIntegration']
exception_list = os.environ['VulnerabilityExceptionsList']
environment = os.environ['Environment']

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

            account_id = (boto3.client('sts').get_caller_identity()['Account'])

            if 'Action' in event:
                if event['Action'] == 'Release':
                    notify_slack_release(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, event, exception_list, environment, event['Action'], context)
                else:
                    notify_slack(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, event, exception_list, environment, event['Action'])
            else:
                action = 'UNKNOWN_ACTION'
                notify_slack(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, event, exception_list, environment, action)

            event["Notification"] = "Success"
            return event

        except BaseException as exc:
            print(exc)
            raise exc


def notify_slack(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, event, exception_list, environment, action):

    '''
        Send message to slack.
    '''

    try:
        if exception_list:
            exception_list_content = exception_list
        else:
            exception_list_content = "None"

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-" + action.lower() + "-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)
        ami_id = event['AMI']

        ami_url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#Images:visibility=owned-by-me;search=" + ami_id + ";sort=desc:creationDate")
        link_to_ami_service = '<%s|%s>' % (ami_url, ami_id)

        parameter_store_url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#Parameters:sort=Name")
        link_to_parameter_store_service = '<%s|%s>' % (parameter_store_url, event['SsmParam'])

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Success - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'AMI SOE Baking Success',
                    'color': "#06a233",
                    # 'text': 'Inspector Found High Vulnerabilities.',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'AMI', 'value': link_to_ami_service, 'short': True},
                        {'title': 'Parameter Store', 'value': link_to_parameter_store_service, 'short': True},
                        {'title': 'Parameter Store Version', 'value': event['SsmParamVersion'], 'short': True},
                        {'title': 'VulnerabilityExceptions', 'value': exception_list_content, 'short': True},
                        {'title': 'StepFunction', 'value': step_function_url_formatted, 'short': True}
                    ]
                }
            ]
        }

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

def get_log_stream(log_group_name, event):
    '''
        Get Versions from outputVersion/stdout logStream on logGroup.
    '''
    build_instance_id = event['BuildInstanceID']
    instance_id = build_instance_id.split('__')
    print("instance_id", instance_id[0])
    client = boto3.client('logs')
    all_streams = []
    stream_batch = client.describe_log_streams(logGroupName=log_group_name)
    all_streams += stream_batch['logStreams']
    while 'nextToken' in stream_batch:
        stream_batch = client.describe_log_streams(logGroupName=log_group_name, nextToken=stream_batch['nextToken'])
        all_streams += stream_batch['logStreams']

    stream_names = [stream['logStreamName'] for stream in all_streams]
    release_note = ''
    for stream in stream_names:
        if 'outputVersion/stdout' in stream:
            print("stream: ", stream)
            logs_batch = client.get_log_events(logGroupName=log_group_name, logStreamName=stream)
            for events in logs_batch['events']:
                if instance_id[0] in events['message']:
                    yum_update = datetime.fromtimestamp(events['timestamp']/1000).strftime("%d/%m/%Y %H:%M:%S")
                    release_note = events['message'].replace('     ', ' ') + "\nYum updated at: " + str(yum_update)
                    print(release_note)
    return release_note


def notify_slack_release(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, account_id, event, exception_list, environment, action, context):

    '''
        Send release message to slack.
    '''

    try:        
        slack_channel = slack_channel
        slack_url = slack_url
        slack_icon = slack_icon

        if exception_list:
            exception_list_content = exception_list
        else:
            exception_list_content = "None"

        step_function_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/arn:aws:states:" + region + ":" + account_id + ":stateMachine:" + solution_naming + "-" + operating_system  + "-" + os_type + "-" + action.lower() + "-soe-sf-sm")
        step_function_url_formatted = '<%s|Link>' % (step_function_url)
        ami_id = event['AMI']

        ami_url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#Images:visibility=owned-by-me;search=" + ami_id + ";sort=desc:creationDate")
        link_to_ami_service = '<%s|%s>' % (ami_url, ami_id)

        parameter_store_url = ("https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#Parameters:sort=Name")
        link_to_parameter_store_service = '<%s|%s>' % (parameter_store_url, event['SsmParam'])


        if operating_system == 'lnx' and os_type == 'amzn':
            subtitle = 'Amazon Linux 2 New Release'
        else:
            subtitle = 'Unknown OS'


        build_instance_id = event['BuildInstanceID']
        instance = "instance-id: " + build_instance_id
        log_group_name = '/ami/baking/%s-build-lg' % (solution_naming)
        release_version = get_log_stream(log_group_name, event)
        release_version = release_version.replace(instance, '')

        slack_message = {
            'channel': slack_channel,
            'username': ("Latest SOE release"),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    'title': (subtitle),
                    'fallback': 'AMI SOE New Release',
                    'color': "#06a233",
                    'fields': [
                        {'title': 'AMI', 'value': ami_id, 'short': True},
                        {'title': 'Parameter Store', 'value': event['SsmParam'], 'short': True},
                        {'title': 'Release Versions', 'value': release_version, 'short': False}
                    ]
                }
            ]
        }

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
