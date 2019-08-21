.DEFAULT_GOAL := deploy

_REGION=ap-southeast-2

# Change these to your respective environment settings

# Solution and Repository
SolutionNamingPrefix=soe-consumption
PipelineSolutionNaming=$(SolutionNamingPrefix)

# Change these to match your cloudformation template names (if different)
PipelineTemplateName=pipeline-cf.yaml
AppInfraTemplateName=application-cf.yaml

# Change this to match the name in your template if different
# PipelineArtifactBucketName and PipelineSourceBucketName are defined in pipeline template
# Used in 'make destroy' to delete all the files with in for delete-stack to succeed
PipelineArtifactBucketName=$(PipelineSolutionNaming)-pipeline-s3
PipelineSourceBucketName=$(PipelineSolutionNaming)-source-s3

# ArtifactBucketName is used to store the artifacts to create the pipeline stack
ArtifactBucketName=$(PipelineSolutionNaming)-artifact
PipelineStackName=$(PipelineSolutionNaming)-pipeline-cf

#IMP: Provide your publishing account Id below
PublishingAccountId=XXXXXXXXX #<<Input your publishig account here which deploys SOE baking solution>>
FetchParameterRemoteRoleArn=arn:aws:iam::$(PublishingAccountId):role/service/ami-baking-lnx-amzn-soe-lnx-amzn-soe-service-iam-role

LatestAmiPath=/ami-baking-lnx-amzn-soe/lnx-amzn/latestAmi

.PHONY: test-cfn
test-cfn: 
	# Validate CICD Pipeline Template (using --template-body has 51k file size limit)
	aws cloudformation validate-template \
		--template-body file://pipeline/$(PipelineTemplateName) \
		--region $(_REGION)
	# Validate Application Infra Template (Upload to s3 and use --template-url to avoid 51k file size limit)
	aws cloudformation validate-template \
		--template-body file://stack/infra/$(AppInfraTemplateName) \
		--region $(_REGION)

.PHONY: test
test: test-cfn

.PHONY: deploy-stack
deploy-stack: test
	# Package the local artifacts referenced to s3
	aws cloudformation package --template-file pipeline/$(PipelineTemplateName) \
		--s3-bucket $(ArtifactBucketName) \
		--output-template-file output-$(PipelineTemplateName)
	#Create and execute a change set
	aws cloudformation deploy \
		--stack-name $(PipelineStackName) \
		--template-file output-$(PipelineTemplateName) \
		--parameter-overrides \
			pPipelinePrefix=$(PipelineSolutionNaming) \
			pStackPrefix=$(SolutionNamingPrefix) \
			pLatestAmiPath=$(LatestAmiPath) \
			pSourceObjectKey=source.zip \
			pFetchParameterRemoteRoleArn=$(FetchParameterRemoteRoleArn) \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(_REGION)
	-rm source.zip
	zip -r source.zip .
	aws s3 cp source.zip s3://$(PipelineSourceBucketName)

.PHONY: destroy-stack
destroy-stack: 
	# Remove all files within the Artifact bucket and the bucket itself
	-aws s3 rm s3://$(ArtifactBucketName) --recursive
	-aws s3 rb s3://$(ArtifactBucketName) --force

	# Remove all files within the Pipeline bucket and the bucket itself
	-aws s3 rm s3://$(PipelineArtifactBucketName) --recursive
	-aws s3 rb s3://$(PipelineArtifactBucketName) --force

	# Remove all files within the Pipeline source bucket and the bucket itself
	-aws s3 rm s3://$(PipelineSourceBucketName) --recursive
	-aws s3 rb s3://$(PipelineSourceBucketName) --force

	# Delete the pipeline stack
	aws cloudformation delete-stack --stack-name $(PipelineStackName)
	# Wait for the pipeline stack to be deleted
	aws cloudformation wait stack-delete-complete --stack-name $(PipelineStackName)

	# Delete the app stack (Used within pipeline)
	aws cloudformation delete-stack --stack-name ${pStackPrefix}-cf
	# Wait for the the stack to be deleted
	aws cloudformation wait stack-delete-complete --stack-name ${pStackPrefix}-cf
	

.PHONY: _events
_events: 
	aws cloudformation describe-stack-events --stack-name $(PipelineStackName)

.PHONY: _output
_output: 
	aws cloudformation describe-stacks --stack-name $(PipelineStackName)