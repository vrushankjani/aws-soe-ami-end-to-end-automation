"""
Common Test Utils
"""
import os

CONST_REGION = 'ap-southeast-2'
CONST_ENVIRONMENT = 'unit'
CONST_NEXT_AMI_PARAM = 'unit-test/nextAmi'
CONST_SOL_NAMING = 'plt-baking-unit'
CONST_SOE_TYPE = 'lnx'

os.environ['Region'] = CONST_REGION
os.environ['Environment'] = CONST_ENVIRONMENT
os.environ['NextAMIParam'] = CONST_NEXT_AMI_PARAM
os.environ['OrganisationAccountID'] = 'dummyId'
os.environ['OrganisationAccountRole'] = 'dummyRole'
os.environ['SolutionNaming'] = CONST_SOL_NAMING
os.environ['SOEType'] = CONST_SOE_TYPE
os.environ['VulnerabilityExceptionsList'] = ''

# Below are overriden within the respective test modules
os.environ['SSMDocument'] = 'NON_SESNSIBLE_DEFAULT'
os.environ['AMIPattern'] = 'NON_SESNSIBLE_DEFAULT'
os.environ['AMIOwner'] = 'NON_SESNSIBLE_DEFAULT'
os.environ['OverrideAMI'] = 'NON_SESNSIBLE_DEFAULT'

class ContextMock(object):
    """Mock Context
    """

    def __init__(self, account_id="172332831461"):
        self.invoked_function_arn = "0:1:2:3:%s" % account_id
