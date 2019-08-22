
_REGION=ap-southeast-2

############################# Provide your custom values #######################

# Replace with your own solution prefix to avoid any bucket name clash
SolutionNamingPrefix=soetest# e.g. ami-baking-lnx-amzn

# Provide Slack configurations if you need to integrate with slack channel for notifications
# If you don't need slack integration, keep UseSlackIntegration=false, otherwise set this to true
SlackChannel=  #(e.g. \\\#test-channel)
SlackURL= 
SlackIcon= 
UseSlackIntegration=false #set this to true if you need slack integration and provide values for above parameters

# IMP: This is a mandatory input. 
# Provide a another account id (member account) to share this AMI with.
MemberAccountId=

############################# Provide your custom values  #######################


# Parameters to fetch the latest base AMI from CIS market place
# Note: 
# 1. This solution is tested with CIS Marketplace Image (hardened image). It has a nominal hourly charge. 
# Please check the pricing in marketplace before you test this solution.
# 2. You can use your own AMI by providing AMI ID in override_ami, however you will need to harden it by 
# using your own script, so that it doesn't fail on inspector assessment test

OS?=lnx
OS_TYPE?=amzn
AMI_PATTERN?=CIS Amazon Linux 2 Benchmark *
AMI_OWNER?=aws-marketplace
VULNERABILITY_EXCEPTIONS_LIST?=
OVERRIDE_AMI?=



# Files and Directory settings
STACK_TEMPLATE_NAME=ami-baking-lnx-amzn-soe-sam-cf.yaml
STACK_OPS_TEMPLATE_NAME=ami-baking-lnx-amzn-soe-ops-monitoring-cf.yaml
STACK_INFRA_DIR=stack/infra
StackAppDir=stack/app
STACK_SRC_DIR=$(StackAppDir)/src
StackTestDir=$(StackAppDir)/test
STACK_UNIT_TEST_DIR=$(StackTestDir)/unit

# Stack Name
STACK_NAME=$(SolutionNamingPrefix)-stack-cf
StackEnvironment?=sbx


# Setup PYTHONPATH so tests can find the required modules
export PYTHONPATH := ./$(STACK_SRC_DIR)/:./$(STACK_UNIT_TEST_DIR)/:$(PYTHONPATH)

# S3 bucket names
# S3 bucket to host inspec test files used during testing step of AMI build step functions
STACK_INSPEC_TEST_BUCKET=$(SolutionNamingPrefix)-inspec-tests-s3
# Make Bucket Settings: Used by this Makefile to store the artifacts to create the pipeline/stack
STACK_SRC_BUCKET=$(SolutionNamingPrefix)-stack-src-s3


# Cloudwatch event schedules
BuildSchedule=cron(0 18 ? * WED *)
ReleaseSchedule=cron(0 18 ? * SUN *)
VulnerabilityScanDuration=600
LogRetentionDays=7

# Stack Parameters
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