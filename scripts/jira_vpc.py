from troposphere import Base64, Select, FindInMap, GetAtt
from troposphere import GetAZs, Join, Output, If, And, Not
from troposphere import Or, Equals, Condition
from troposphere import Parameter, Ref, Tags, Template
from troposphere.cloudformation import Init
from troposphere.cloudfront import Distribution
from troposphere.cloudfront import DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.ec2 import PortRange
from troposphere.cloudformation import Stack


t = Template()

t.add_version("2010-09-09")

t.add_description("""\
Master Template for Atlassian Services (qs-1p9o4n3sq)""")
PrivateSubnet1CIDR = t.add_parameter(Parameter(
    "PrivateSubnet1CIDR",
    Default="10.0.0.0/19",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR block for private subnet 1 located in Availability Zone 1.",
))

VPCCIDR = t.add_parameter(Parameter(
    "VPCCIDR",
    Default="10.0.0.0/16",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the VPC",
))

PublicSubnet1CIDR = t.add_parameter(Parameter(
    "PublicSubnet1CIDR",
    Default="10.0.128.0/20",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the public DMZ subnet 1 located in Availability Zone 1",
))

PrivateSubnet2CIDR = t.add_parameter(Parameter(
    "PrivateSubnet2CIDR",
    Default="10.0.32.0/19",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR block for private subnet 2 located in Availability Zone 2.",
))

QSS3KeyPrefix = t.add_parameter(Parameter(
    "QSS3KeyPrefix",
    Default="quickstart-atlassian-services/",
    AllowedPattern="^[0-9a-zA-Z-/]*$",
    Type="String",
    ConstraintDescription="Quick Start key prefix can include numbers, lowercase letters, uppercase letters, hyphens (-), and forward slash (/).",
    Description="S3 key prefix for the Quick Start assets. Quick Start key prefix can include numbers, lowercase letters, uppercase letters, hyphens (-), and forward slash (/).",
))

NATInstanceType = t.add_parameter(Parameter(
    "NATInstanceType",
    Default="t2.small",
    Type="String",
    Description="Amazon EC2 instance type for the NAT Instances. This is only used if the region does not support NAT gateways.",
    AllowedValues=["t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large", "m3.medium", "m3.large", "m4.large"],
))

AccessCIDR = t.add_parameter(Parameter(
    "AccessCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR block allowed to access Atlassian Services. This should be set to a trusted IP range; if you want to give public access use '0.0.0.0/0'.",
))

QSS3BucketName = t.add_parameter(Parameter(
    "QSS3BucketName",
    Default="aws-quickstart",
    AllowedPattern="^[0-9a-zA-Z]+([0-9a-zA-Z-]*[0-9a-zA-Z])*$",
    Type="String",
    ConstraintDescription="Quick Start bucket name can include numbers, lowercase letters, uppercase letters, and hyphens (-). It cannot start or end with a hyphen (-).",
    Description="S3 bucket name for the Quick Start assets. Quick Start bucket name can include numbers, lowercase letters, uppercase letters, and hyphens (-). It cannot start or end with a hyphen (-).",
))

AvailabilityZones = t.add_parameter(Parameter(
    "AvailabilityZones",
    Type="List<AWS::EC2::AvailabilityZone::Name>",
    Description="List of Availability Zones to use for the subnets in the VPC. Note: You must specify 2 AZs here; if more are specified only the first 2 will be used.",
))

PublicSubnet2CIDR = t.add_parameter(Parameter(
    "PublicSubnet2CIDR",
    Default="10.0.144.0/20",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the public DMZ subnet 2 located in Availability Zone 2",
))

KeyPairName = t.add_parameter(Parameter(
    "KeyPairName",
    Type="AWS::EC2::KeyPair::KeyName",
    Description="Public/private key pairs allow you to securely connect to your instance after it launches",
))

t.add_condition("GovCloudCondition",
    Equals(Ref("AWS::Region"), "us-gov-west-1")
)

t.add_mapping("AWSInfoRegionMap",
{u'ap-northeast-1': {u'Partition': u'aws',
                     u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'ap-northeast-2': {u'Partition': u'aws',
                     u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'ap-south-1': {u'Partition': u'aws',
                 u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'ap-southeast-1': {u'Partition': u'aws',
                     u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'ap-southeast-2': {u'Partition': u'aws',
                     u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'eu-central-1': {u'Partition': u'aws',
                   u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'eu-west-1': {u'Partition': u'aws',
                u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'sa-east-1': {u'Partition': u'aws',
                u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'us-east-1': {u'Partition': u'aws',
                u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'us-gov-west-1': {u'Partition': u'aws-us-gov',
                    u'QuickStartS3URL': u'https://s3-us-gov-west-1.amazonaws.com'},
 u'us-west-1': {u'Partition': u'aws',
                u'QuickStartS3URL': u'https://s3.amazonaws.com'},
 u'us-west-2': {u'Partition': u'aws',
                u'QuickStartS3URL': u'https://s3.amazonaws.com'}}
)

BastionStack = t.add_resource(Stack(
    "BastionStack",
    TemplateURL={ "Fn::Sub": ["https://${QSS3BucketName}.${QSS3Region}.amazonaws.com/${QSS3KeyPrefix}quickstarts/quickstart-bastion-for-atlassian-services.yaml", { "QSS3Region": If("GovCloudCondition", "s3-us-gov-west-1", "s3") }] },
    Parameters={ "Subnet": GetAtt("VPCStack", "Outputs.PublicSubnet1ID"), "KeyName": Ref(KeyPairName), "VPC": GetAtt("VPCStack", "Outputs.VPCID"), "AccessCIDR": Ref(AccessCIDR) },
    DependsOn=["VPCStack"],
))

VPCStack = t.add_resource(Stack(
    "VPCStack",
    TemplateURL={ "Fn::Sub": ["https://${QSS3BucketName}.${QSS3Region}.amazonaws.com/${QSS3KeyPrefix}submodules/quickstart-aws-vpc/templates/aws-vpc.template", { "QSS3Region": If("GovCloudCondition", "s3-us-gov-west-1", "s3") }] },
    Parameters={ "NATInstanceType": Ref(NATInstanceType), "PrivateSubnet1ACIDR": Ref(PrivateSubnet1CIDR), "NumberOfAZs": "2", "PublicSubnet1CIDR": Ref(PublicSubnet1CIDR), "VPCCIDR": Ref(VPCCIDR), "AvailabilityZones": Join(",", Ref(AvailabilityZones)), "PrivateSubnet2ACIDR": Ref(PrivateSubnet2CIDR), "PublicSubnet2CIDR": Ref(PublicSubnet2CIDR), "KeyPairName": Ref(KeyPairName) },
))

PublicSubnets = t.add_output(Output(
    "PublicSubnets",
    Export={ "Name": "ATL-PubNets" },
    Description="A list of 2 Public subnets",
    Value=Join(",", [GetAtt(VPCStack, "Outputs.PublicSubnet1ID"), GetAtt(VPCStack, "Outputs.PublicSubnet2ID")]),
))

VPCID = t.add_output(Output(
    "VPCID",
    Export={ "Name": "ATL-VPCID" },
    Description="Atlassian Services VPC ID",
    Value=GetAtt(VPCStack, "Outputs.VPCID"),
))

BastionPubIp = t.add_output(Output(
    "BastionPubIp",
    Description="The Public IP to ssh to the Bastion",
    Value=GetAtt(BastionStack, "Outputs.BastionPubIp"),
))

DefaultKey = t.add_output(Output(
    "DefaultKey",
    Export={ "Name": "ATL-DefaultKey" },
    Description="Default Ec2 keypair name",
    Value=Ref(KeyPairName),
))

PrivateSubnets = t.add_output(Output(
    "PrivateSubnets",
    Export={ "Name": "ATL-PriNets" },
    Description="A list of 2 Private subnets",
    Value=Join(",", [GetAtt(VPCStack, "Outputs.PrivateSubnet1AID"), GetAtt(VPCStack, "Outputs.PrivateSubnet2AID")]),
))

print(t.to_json())
