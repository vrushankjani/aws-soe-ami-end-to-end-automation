'''

This module checks the status on the test ssm autoamtion run vulenerability scan and InSpec Compliance test.

'''
import json
import logging
import os
from datetime import datetime
import time

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
region = os.environ['Region']
exception_list = os.environ['VulnerabilityExceptionsList']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    global exception_list
    exception_list = event['IgnoreFindings'] if 'IgnoreFindings' in event else None
    ignore_failure = event['IgnoreTestFailure'] == 'True' if 'IgnoreTestFailure' in event else False

    test_automation_execution_id = event['TestAutomationExecutionId']

    try:
        # Step 1
        ssm_state = check_ssm(region, test_automation_execution_id)
        print("SSM Automation State: " + ssm_state)
        # Step 2
        instance_id = get_instance_id(region, test_automation_execution_id)
        print("Instance ID: " + instance_id)
        event["InstanceID"] = instance_id

        if ssm_state == 'succeeded':

            # Step 3
            inspector_state = vulnerability_status(region, test_automation_execution_id)
            print("Inspector Scan State: " + inspector_state)
            if inspector_state == 'succeeded':

                # Step 4
                inspec_test_output = get_inspec_test_result(region, instance_id)
                print("InSpec Status: " + inspec_test_output)

                if inspec_test_output == 'COMPLIANT':

                    # Step 5
                    vulnerability_result_output, vulnerability_result_stats = vulnerability_result(region, test_automation_execution_id)
                    print("Vulnerability Status: " + vulnerability_result_output)
                    print("Vulnerability Stats: %s" % vulnerability_result_stats)

                    event["VulnerabilityFindingsStats"] = vulnerability_result_stats
                    if vulnerability_result_output == 'Passed':
                        event["TestStatus"] = 'succeeded'
                    else:
                        event["TestStatus"] = 'failed'
                        event["CheckType"] = "vulnerability"

                else:
                    event["TestStatus"] = 'failed'
                    event["CheckType"] = "inspec"

            else:
                event["TestStatus"] = inspector_state
                event["CheckType"] = "inspector"

        else:
            event["TestStatus"] = ssm_state
            event["CheckType"] = "ssm_test"

        if event["TestStatus"] in ['failed', 'unknown'] and ignore_failure:
            print("Check Type '%s' has Status '%s' but IgnoreTestFailure has been set. Setting Status to 'skipped'" % (event["CheckType"], event["TestStatus"]))
            event["TestStatus"] = 'skipped'

        return event

    except BaseException as exc:
        print(exc)
        raise exc


def check_ssm(region, test_automation_execution_id):

    '''
        Check Build SSM automation status
    '''

    client = boto3.client('ssm', region_name=region)

    try:
        ssm_response = client.get_automation_execution(
            AutomationExecutionId=test_automation_execution_id
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


def vulnerability_status(region, test_automation_execution_id):

    '''
        Get vulnerability run status
    '''

    ssm_client = boto3.client('ssm', region_name=region)
    inspector_client = boto3.client('inspector')

    try:
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=test_automation_execution_id
        )

        scan_output = ssm_response['AutomationExecution']['Outputs']['runVulnerabilityScan.Output'][0]
        scan_output_format = scan_output.strip()
        inspector_assessment_run_arn = scan_output_format.strip('"')
        #print("SSM Vulnerability Output: " + inspector_assessment_run_arn)

        assesment_run_response = inspector_client.describe_assessment_runs(
            assessmentRunArns=[
                inspector_assessment_run_arn,
            ]
        )

        # print("Inspector assesment run response:")
        # print(assesment_run_response)
        state_created = False
        state_start_data_collection_pending = False
        state_start_data_collection_in_progress = False
        state_collecting_data = False
        state_stop_data_collection_pending = False
        state_data_collected = False
        state_start_evauluating_rules_pending = False
        state_evaluating_rules = False
        state_failed = False
        state_error = False
        state_completed = False
        state_complete_with_errors = False
        state_canceled = False

        if assesment_run_response['assessmentRuns'][0]['state'] == 'CREATED':
            state_created = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'START_DATA_COLLECTION_PENDING':
            state_start_data_collection_pending = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'START_DATA_COLLECTION_IN_PROGRESS':
            state_start_data_collection_in_progress = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'COLLECTING_DATA':
            state_collecting_data = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'STOP_DATA_COLLECTION_PENDING':
            state_stop_data_collection_pending = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'DATA_COLLECTED':
            state_data_collected = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'START_EVALUATING_RULES_PENDING':
            state_start_evauluating_rules_pending = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'EVALUATING_RULES':
            state_evaluating_rules = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'FAILED':
            state_failed = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'ERROR':
            state_error = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'COMPLETED':
            state_completed = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'COMPLETED_WITH_ERRORS':
            state_complete_with_errors = True
        elif assesment_run_response['assessmentRuns'][0]['state'] == 'CANCELED':
            state_canceled = True
        else:
            print("State Unknown")

        if state_start_data_collection_pending or state_start_data_collection_in_progress or state_collecting_data or state_stop_data_collection_pending or state_data_collected or state_start_evauluating_rules_pending or state_evaluating_rules:
            state = 'running'
        elif state_completed:
            state = 'succeeded'
        elif state_created or state_failed or state_error or state_complete_with_errors or state_canceled:
            state = 'failed'
        else:
            state = 'unknown'

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return state


def is_breaking_finding(findings_detail, stats):
    """
        Determine if a finding is a breaking failure.
    """
    # Ignore user exceptions list
    if exception_list and findings_detail['id'] in exception_list:
        if 'ExceptionList' in stats:
            stats['ExceptionList'] += 1
        else:
            stats['ExceptionList'] = 1
        logger.debug("Finding '%s' is in VulnerabilityExceptionsList, ignoring.", findings_detail['id'])
        return False

    # Ignore CIS Level 2
    for attr in findings_detail['attributes']:
        if attr['key'] == "CIS_BENCHMARK_PROFILE":
            # Ignore Level 2 as we are currently using CIS Hardened AMI to Level 1 only
            if "Level 2" in attr['value']:
                if 'CIS_Level_2' in stats:
                    stats['CIS_Level_2'] += 1
                else:
                    stats['CIS_Level_2'] = 1
                logger.debug("Finding '%s' has CIS Profile '%s', ignoring.", findings_detail['id'], attr['value'])
                return False

    # Ignore non High severity
    if 'severity' in findings_detail and findings_detail['severity'] != 'High':
        # Update stats about the severity of findings found
        if findings_detail['severity'] in stats:
            stats[findings_detail['severity']] += 1
        else:
            stats[findings_detail['severity']] = 1
        logger.debug("Finding '%s' has Severity '%s', ignoring.", findings_detail['id'], findings_detail['severity'])
        return False

    # Every other findings are a breaking failure
    logger.error("Finding '%s' is a breaking failure.", findings_detail['id'])
    return True


def vulnerability_result(region, test_automation_execution_id):

    '''
        Get vulnerability scan results
    '''

    ssm_client = boto3.client('ssm', region_name=region)
    inspector_client = boto3.client('inspector')
    stats = {}

    try:
        ssm_response = ssm_client.get_automation_execution(
            AutomationExecutionId=test_automation_execution_id
        )

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

        # Using List comprehension to break the list in the chunks of 100 as describe_findings 
        # call can only accept 100 findings ARNs only at max
        n = 100
        findings_arns_chunks = [all_findings_arns[i * n:(i + 1) * n] for i in range((len(all_findings_arns) + n - 1) // n )]
        ignored_findings = []
        breaking_findings = []
        for finding_arns in findings_arns_chunks:   
            findings_details = inspector_client.describe_findings(
                findingArns=finding_arns
            )

            # For each finding, filter down to breaking findings only
            for findings_detail in findings_details['findings']:
                if is_breaking_finding(findings_detail, stats):
                    breaking_findings.append(findings_detail['id'])
                else:
                    ignored_findings.append(findings_detail['id'])

        print("%s High Vulnerabilities Found With No Exception" % len(breaking_findings))
        print("%s Vulnerabilities Ignored" % len(ignored_findings))
        
        if breaking_findings:
            result = 'Failed'
        else:
            result = 'Passed'

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return result, stats


def get_inspec_test_result(region, instance_id):

    '''
        Gets the compliance result of the InSpec test
    '''

    ssm_client = boto3.client('ssm', region_name=region)

    try:
        # run a loop to check SSM Compliance API whether instance is compliant or not
        while True:
            lrcs_response = ssm_client.list_resource_compliance_summaries(
                Filters=[
                    {
                        'Key': 'ComplianceType',
                        'Values': [
                            'Custom:Inspec',
                        ]
                    },
                    {
                        'Key': 'InstanceId',
                        'Values': [
                            instance_id
                        ]
                    }
                ]
            )

            # set compliance status to None
            instance_compliance = None

            for c_items in lrcs_response['ResourceComplianceSummaryItems']:
                if c_items['ResourceId'] == instance_id:
                    print(c_items['ResourceId'])
                    print(c_items['Status'])
                    if c_items['Status'] == 'COMPLIANT':
                        print("Passed")
                        instance_compliance = 'COMPLIANT'
                    elif c_items['Status'] == 'NON_COMPLIANT':
                        print("Failed")
                        instance_compliance = 'NON_COMPLIANT'
            if instance_compliance == 'COMPLIANT':
                break
            elif instance_compliance == 'NON_COMPLIANT':
                break
            else:
                print("Retrying after 5 seconds...")
                time.sleep(5)

    except:
        raise

    return instance_compliance


def get_instance_id(region, test_automation_execution_id):

    '''
        Get instance ID for test instance
    '''

    client = boto3.client('ssm', region_name=region)

    try:
        ssm_response = client.get_automation_execution(
            AutomationExecutionId=test_automation_execution_id
        )

        scan_output = ssm_response['AutomationExecution']['Outputs']['startInstances.InstanceIds'][0]
        scan_output_format = scan_output.strip()
        instance_id = scan_output_format.strip('"')

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc

    return instance_id
