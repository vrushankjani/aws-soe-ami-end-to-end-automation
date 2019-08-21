
_REGION=ap-southeast-2

# Default to Amazon Linux 2 (Override from command line)
OS?=lnx
OS_TYPE?=amzn
AMI_PATTERN?=CIS Amazon Linux 2 Benchmark *
AMI_OWNER?=aws-marketplace
VULNERABILITY_EXCEPTIONS_LIST?=
OVERRIDE_AMI?=


# Solution Settings
SolutionNamingPrefix=ami-baking-$(OS)-$(OS_TYPE)-soe

# File settings
STACK_TEMPLATE_NAME=$(SolutionNamingPrefix)-sam-cf.yaml
STACK_OPS_TEMPLATE_NAME=$(SolutionNamingPrefix)-ops-monitoring-cf.yaml
StackEnvironment?=sbx
# Stack Name
STACK_NAME=$(SolutionNamingPrefix)-stack-cf

# Directory settings
STACK_INFRA_DIR=stack/infra
StackAppDir=stack/app
STACK_SRC_DIR=$(StackAppDir)/src
StackTestDir=$(StackAppDir)/test
STACK_UNIT_TEST_DIR=$(StackTestDir)/unit
# Setup PYTHONPATH so tests can find the required modules
export PYTHONPATH := ./$(STACK_SRC_DIR)/:./$(STACK_UNIT_TEST_DIR)/:$(PYTHONPATH)


# S3 bucket to host inspec test files used during testing step of AMI build step functions
STACK_INSPEC_TEST_BUCKET=$(SolutionNamingPrefix)-inspec-tests-s3
# Make Bucket Settings: Used by this Makefile to store the artifacts to create the pipeline/stack
STACK_SRC_BUCKET=$(SolutionNamingPrefix)-stack-src-s3


# We are developing the CICD pipeline in Sandbox
SlackChannel= #<< Input your value here >> (e.g. \\\#test-channel)
SlackURL= #<< Input your value here >>
SlackIcon= #<< Input your value here >>
UseSlackIntegration=false

# Cloudwatch event schedules
BuildSchedule=cron(0 18 ? * WED *)
ReleaseSchedule=cron(0 18 ? * SUN *)

VulnerabilityScanDuration=600
LogRetentionDays=7

#IMP: Member account id to share this AMI with. Currently only supporting one member account.
MemberAccountId=XXXXXXXXX #<< Input your nominated member account id here >>


STACK_PARAMETERS = \
	pEnvironment=$(StackEnvironment) \
	pStackPrefix=$(SolutionNamingPrefix) \
	pAMIPattern="$(AMI_PATTERN)" \
	pOSType=$(OS_TYPE) \
	pOS=$(OS) \
	pVulnerabilityExceptionsList="$(VULNERABILITY_EXCEPTIONS_LIST)" \
	pSlackChannel=$(SlackChannel) \
	pUseSlackIntegration=false \
	pSlackURL=$(SlackURL) \
	pSlackIcon=$(SlackIcon) \
	pOverrideAMI=$(OVERRIDE_AMI) \
	pBuildSchedule="$(BuildSchedule)" \
	pReleaseSchedule="$(ReleaseSchedule)" \
	pVulnerabilityScanDuration=$(VulnerabilityScanDuration) \
	pAMIOwner=$(AMI_OWNER) \
	pLogRetentionDays=$(LogRetentionDays) \
	pMemberAccountId=$(MemberAccountId) \
	pInspecTestFilesBucket=$(STACK_INSPEC_TEST_BUCKET)


# Override TEST_AMI_ID with the AMI ID you want to run the Test Document against
# This will not terminate the instance, so you must clean up manually
TEST_AMI_ID?=ami-0e5c476c0a7d0c62b
TEST_INSTANCE_TYPE?=t3.micro
TEST_DOC_NAME_PREFIX?=$(StackName)-rAutomationDocTestLinuxAMI-
FIND_DOC_NAME_CMD=aws ssm list-documents --filters 'Key=Name,Values=$(TEST_DOC_NAME_PREFIX)' | grep Name | cut -d '"' -f 4
.PHONY: test-inspec
test-inspec:
	aws ssm start-automation-execution --document-name "$(shell $(FIND_DOC_NAME_CMD))" --parameters "sourceAMIid=$(TEST_AMI_ID),InstanceType=$(TEST_INSTANCE_TYPE)"
	# Replace AUTOMATION_EXECUTION_ID with above output to check
	@echo aws ssm get-automation-execution --automation-execution-id AUTOMATION_EXECUTION_ID
	# Please ensure you clean up and terminate the EC2 instance (Output: startInstances.InstanceIds)

#
# OVERRIDE CICD TARGETS - Override after the CICD import (if any)
#
test-cfn:
	-aws s3 mb s3://$(STACK_SRC_BUCKET) --region $(_REGION)
	# Validate Application Infra Template (Upload to s3 and use --template-url to avoid 51k file size limit)
	aws s3 cp $(STACK_INFRA_DIR)/$(STACK_TEMPLATE_NAME) s3://$(STACK_SRC_BUCKET)/$(STACK_TEMPLATE_NAME)
	aws cloudformation validate-template \
		--template-url https://s3-$(_REGION).amazonaws.com/$(STACK_SRC_BUCKET)/$(STACK_TEMPLATE_NAME) \
		--region $(_REGION)
	aws s3 cp $(STACK_INFRA_DIR)/$(STACK_OPS_TEMPLATE_NAME) s3://$(STACK_SRC_BUCKET)/$(STACK_OPS_TEMPLATE_NAME)
	aws cloudformation validate-template \
		--template-url https://s3-$(_REGION).amazonaws.com/$(STACK_SRC_BUCKET)/$(STACK_OPS_TEMPLATE_NAME) \
		--region $(_REGION)
	@echo ""

.PHONY: package-cf
package-cf: test-cfn
	-aws s3 mb s3://$(STACK_SRC_BUCKET) --region $(_REGION)
	# Package the local artifacts referenced to s3
	aws cloudformation package --template-file $(STACK_INFRA_DIR)/$(STACK_TEMPLATE_NAME) \
		--output-template-file $(STACK_INFRA_DIR)/output-$(STACK_TEMPLATE_NAME) \
		--s3-bucket $(STACK_SRC_BUCKET)
	@echo "Cloudformation packaging completed"

.PHONY: deploy-stack
deploy-stack: test-cfn package-cf
	$(call deploy_cf_with_s3,,,)
	-aws s3 mb s3://$(STACK_INSPEC_TEST_BUCKET) --region $(_REGION)
	-aws s3 mb s3://$(STACK_SRC_BUCKET) --region $(_REGION)
	# Create and execute a change set
	aws cloudformation deploy \
		--stack-name $(STACK_NAME) \
		--template-file $(STACK_INFRA_DIR)/output-$(STACK_TEMPLATE_NAME) \
		--parameter-overrides \
			$(STACK_PARAMETERS) \
		--capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
		--s3-bucket $(STACK_SRC_BUCKET) \
		--region $(_REGION)
	@echo "Stack is deployed"
	# Copy the required inspec test file
	aws s3 cp $(StackTestDir)/functional/linux_soe_compliance.rb s3://$(STACK_INSPEC_TEST_BUCKET)/inspec/ --acl bucket-owner-full-control