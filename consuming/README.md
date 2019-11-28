# Reference solution Consuming AMI published by baking solution

&nbsp;

## Overview 
&nbsp;

## Consuming
*consuming* folder contains reference solution to consume the new AMI produce by SOE baking solution under 'publishing' folder and use that to deploy EC2 



&nbsp;
As a part of this reference soliution we add an action in a stage to fetch latest AMI Id from the publising account using cross account role. This is done via *Lambda Invoke Action* in the pipeline to fetch the AMI and inject it as a cloudformation parameter.

&nbsp;

##  Folder Structure within consuming folder
&nbsp;

`stack/pipeline` - Pipeline to deploy EC2 instnace by fetching latest AMI Id from publishing accont and then deploying the EC2 instance with new AMI ID throught the cloudformatin template in stack/infra folder below

`stack/infra` - Very basic cloudformation deploy EC2 using latest AMI

  

&nbsp;
## Prerequisites
&nbsp;

## Multiaccount
This solution is tested in multi account setup. So it is recommended to use two accounts.
- One account where you publish the SOE baking solution as in 'publishing' folder
- And another account here to use it as a member account for consuming this AMI

### Subscription to CIS marketplace
If you are using the same base AMI, sourced from CIS marketplace, as in the solution, then you would need to ensure that all the accounts that you want to share this AMI are subscribed to CIS marketplace - https://aws.amazon.com/marketplace/pp/B07M68CJS5/

### Event bus in member account
Ensure that the default event bus is setup to allowing access from publishing account where you deploy the baking solution.

Follow this reference document to setup cross account permission for the detault event bus - https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/CloudWatchEvents-CrossAccountEventDelivery.html

**Note:** This account's event bus will receive the event for the AMI parameter change from publishing account. We can then further create a cloudwatch rule to catch this event and trigger the codepipeline automatically to then deploy new AMI soon after new AMNI is released.


### Permission
&nbsp;

In order to test deploying this solution to your account it would be advisable that you use user with **Administrator Access** for smooth testing.


&nbsp;
### Softwares
&nbsp;

- AWS CLI
- Python 3.*
- Pytest, if you want to perform unit testing on python code


&nbsp;
### Deploying the Solution
&nbsp;
Follow steps as below

#### Set environment variables
```
Set credentials/profile for the AWS account you want to deploy this solution before running any make commands
```
&nbsp;
#### Set cloudformation parameter inputs 
**IMPORTANT**
Below are the parameters in the **consuming/Makefile** that you need to provide your own custom values for. Rest of the parameter values you can kept as is.

These parameters are marked with << Input your value here >> message.
```
- PublishingAccountId:<< Input your value here >>
Provide the publishing account ID which build and publish AMI that we need to access  here.
```
&nbsp;
#### Deploy/Update Solution
From the consuming folder, run:
```
cd consuming (ensure you are in consuming folder)
make deploy-stack
```

#### Destroy Solution
From the consuming folder, run:
```
cd consuming (ensure you are in consuming folder)
make destroy-stack
```

&nbsp;
###  Running syntax tests
To run a syntax test on CFN templates for the CICD pipeline and solution:
```
make test-cfn
```

&nbsp;

&nbsp;
###  Upcoming changes
Below are the upcoming changes that I am working on and I'll be releasing them soon
- Add cloudwatch rule to trigger codepipeline upon receiving event on SSM Parameter Change for the '$(context)/latestAMI' parameter. 
- Update cloudformation with AutoScalingGroup to roll over new AMI on the existing EC2 cluster using blue/green approach
- Show how we can use macro to inject Lambda Invoke Stage to fetch latest AMI. This macro then can be used in any pipeline which require to use this AMI.

&nbsp;




&nbsp;
## Developer:
* Vrushank Jani
