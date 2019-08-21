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


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
region = os.environ['Region']
solution_naming = os.environ['SolutionNaming']
os_type = os.environ['OSType']
operating_system = os.environ['OS']
slack_channel = os.environ['SlackChannel']
slack_url = os.environ['SlackURL']
slack_icon = os.environ['SlackIcon']
enable_slack = os.environ['EnableSlackIntegration']
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
            alert = event['Records'][0]['Sns']['Message']
            message = json.loads(alert)
            print("Message:" + json.dumps(message))

            dimensions = None

            if 'Dimensions' in message['Trigger']:
                dimensions = message['Trigger']['Dimensions']
            elif 'Metrics' in message['Trigger']:
                for metric in message['Trigger']['Metrics']:
                    if 'MetricStat' in metric:
                        dimensions = metric['MetricStat']['Metric']['Dimensions']
                        break

            if dimensions:
                statemachine_arn = dimensions[0]['value']
            else:
                raise BaseException("State machine ARN could not be found in the  SNS event message")

            print("State Machine ARN for the failed step function:"+statemachine_arn)

            if 'build-soe' in statemachine_arn:
                action = 'Build'
            elif 'release-soe' in statemachine_arn:
                action = 'Release'
            else:
                action = 'UNKNOWN_ACTION'

            # Step 1
            notify_slack(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, statemachine_arn, environment, action)

            event["Notification"] = "Success"
            return event

    except BaseException as exc:
        print(exc)
        raise exc


def notify_slack(slack_url, region, slack_icon, slack_channel, solution_naming, os_type, operating_system, statemachine_arn, environment, action):

    '''
        Send message to slack for workflow failure.
    '''

    try:

        workflow_url = ("https://" + region + ".console.aws.amazon.com/states/home?region=" + region + "#/statemachines/view/" + statemachine_arn)
        workflow_url_formatted = '<%s|Link>' % (workflow_url)

        slack_message = {
            'channel': slack_channel,
            'username': ("AMI SOE " + action + " Failure - " + environment),
            'icon_emoji': slack_icon,
            'attachments': [
                {
                    'mrkdwn_in': ['text', 'pretext', 'fields'],
                    'title': (solution_naming + "-" + os_type + "-" + operating_system),
                    'fallback': 'Workflow Failure',
                    'color': "#FF0000",
                    'text': action + ' StepFunction Workflow Execution Failed',
                    'fields': [
                        {'title': 'Action', 'value': action, 'short': True},
                        {'title': 'StepFunction', 'value': workflow_url_formatted, 'short': True},
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
