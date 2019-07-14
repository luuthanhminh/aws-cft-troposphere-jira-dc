from troposphere import Base64, Select, FindInMap, GetAtt
from troposphere import GetAZs, Join, Output, If, And, Not
from troposphere import Or, Equals, Condition
from troposphere import Parameter, Ref, Tags, Template
from troposphere.cloudformation import Init
from troposphere.cloudfront import Distribution
from troposphere.cloudfront import DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.ec2 import PortRange
from troposphere.ec2 import Instance, NetworkInterfaceProperty, PrivateIpAddressSpecification
from troposphere.ec2 import SecurityGroup


t = Template()

t.add_version("2010-09-09")

t.add_description("""\
QS(5027) Atlassian Vpc Bastion Oct,19,2016""")
Subnet = t.add_parameter(Parameter(
    "Subnet",
    Type="AWS::EC2::Subnet::Id",
    ConstraintDescription="Must be one of the external Subnet ID's within the selected VPC.",
    Description="External Subnet where your bastion will be deployed. MUST be within the selected VPC.",
))

KeyName = t.add_parameter(Parameter(
    "KeyName",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="Must be the name of an existing EC2 Key Pair.",
    Description="The EC2 Key Pair to allow SSH access to the instances.",
))

LatestAmiId = t.add_parameter(Parameter(
    "LatestAmiId",
    Default="/aws/service/ami-amazon-linux-latest/amzn-ami-hvm-x86_64-gp2",
    Type="AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
    Description="(leave default) System property containing AMI ID for the Bastion host.",
))

VPC = t.add_parameter(Parameter(
    "VPC",
    Type="AWS::EC2::VPC::Id",
    ConstraintDescription="Must be the ID of a VPC.",
    Description="Virtual Private Cloud",
))

AccessCIDR = t.add_parameter(Parameter(
    "AccessCIDR",
    Description="The CIDR IP range that is permitted to access Services in this VPC. Use 0.0.0.0/0 if you want public access from the internet.",
    Default="0.0.0.0/0",
    ConstraintDescription="Must be a valid IP CIDR range of the form x.x.x.x/x.",
    MaxLength=18,
    AllowedPattern="(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
    MinLength=9,
    Type="String",
))

Bastion = t.add_resource(Instance(
    "Bastion",
    NetworkInterfaces=[
    NetworkInterfaceProperty(
        SubnetId=Ref(Subnet),
        DeviceIndex="0",
        GroupSet=[Ref("SecurityGroup")],
        AssociatePublicIpAddress=True,
    ),
    ],
    Tags=Tags(
        Name="Bastion for Atlassian Product VPC",
    ),
    KeyName=Ref(KeyName),
    InstanceType="t2.micro",
    ImageId=Ref(LatestAmiId),
))

SecurityGroup = t.add_resource(SecurityGroup(
    "SecurityGroup",
    SecurityGroupIngress=[{ "ToPort": 22, "IpProtocol": "tcp", "CidrIp": Ref(AccessCIDR), "FromPort": 22 }],
    VpcId=Ref(VPC),
    GroupDescription="Security group allowing SSH access",
))

BastionPubIp = t.add_output(Output(
    "BastionPubIp",
    Description="The Public IP to ssh to the Bastion",
    Value=GetAtt(Bastion, "PublicIp"),
))

print(t.to_json())
