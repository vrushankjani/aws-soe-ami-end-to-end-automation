'''

This module will remove AMIs for the SOE type older than x days

'''
import json
import os
from datetime import datetime, timedelta

import boto3
import botocore


print('Loading function ' + datetime.now().time().isoformat())

### Environment variables ###
# General
region = os.environ['Region']
ssm_path = os.environ['SSMPath']
soe_type = os.environ['SOEType']
solution_naming = os.environ['SolutionNaming']

# Days to delete after
day_limit = datetime.now() - timedelta(days=30)
today = day_limit.isoformat()


def lambda_handler(event, context):

    '''
        Run function and return output.
    '''

    print("Event: " + json.dumps(event))

    try:

        # Step 1
        purge_output = purge(region, ssm_path, soe_type, solution_naming, day_limit, today, context)
        event["purge output"] = purge_output
        return event

    except BaseException as exc:
        print(exc)
        raise exc


def purge(region, ssm_path, soe_type, solution_naming, day_limit, today, context):

    '''
        Purge AMI olde than x days
    '''

    try:
        client = boto3.client('ec2', region_name=region)
        tagkey = 'SoeType'
        tagvalue = (solution_naming + "-" + soe_type)
        account_id = context.invoked_function_arn.split(":")[4]

        images = client.describe_images(
            Filters=[
                {
                    'Name': 'tag:'+tagkey,
                    'Values': [tagvalue]
                },
            ],
            Owners=[
                account_id,
            ]
        )
        print("All SOE Type images: " + json.dumps(images))

        delete_images_list = []
        delete_snapshot_list = []
        for image in images['Images']:
            image_created_time = image["CreationDate"]
            if image_created_time < today:
                delete_images_list.append(image['ImageId'])
                delete_snapshot_list.append(image['BlockDeviceMappings'][0]['Ebs']['SnapshotId'])
                image_id = image['ImageId']
                snapshot_id = image['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
                client.deregister_image(ImageId=image_id)
                client.delete_snapshot(SnapshotId=snapshot_id)

        if delete_images_list:
            print("Images deleted: " + json.dumps(delete_images_list))
            output = ("Images deleted: " + json.dumps(delete_images_list))
        else:
            print("No images to delete")
            output = ("No images deleted")

        if delete_snapshot_list:
            print("Snapshots deleted: " + json.dumps(delete_snapshot_list))
        else:
            print("No snapshots to delete")

        return output

    except botocore.exceptions.ClientError as exc:
        print(exc)
        raise exc
