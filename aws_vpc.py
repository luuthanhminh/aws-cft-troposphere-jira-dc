from troposphere import Base64, Select, FindInMap, GetAtt
from troposphere import GetAZs, Join, Output, If, And, Not
from troposphere import Or, Equals, Condition
from troposphere import Parameter, Ref, Tags, Template
from troposphere.cloudformation import Init
from troposphere.cloudfront import Distribution
from troposphere.cloudfront import DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.ec2 import PortRange
from troposphere.ec2 import Route
from troposphere.ec2 import RouteTable
from troposphere.ec2 import NetworkAclEntry
from troposphere.ec2 import SubnetRouteTableAssociation
from troposphere.ec2 import Subnet
from troposphere.ec2 import NetworkAcl
from troposphere.ec2 import InternetGateway
from troposphere.ec2 import SubnetNetworkAclAssociation
from troposphere.ec2 import NatGateway
from troposphere.ec2 import DHCPOptions
from troposphere.ec2 import VPC
from troposphere.ec2 import EIP
from troposphere.ec2 import VPCDHCPOptionsAssociation
from troposphere.ec2 import VPCGatewayAttachment
from troposphere.ec2 import VPCEndpoint


t = Template()

t.add_version("2010-09-09")

t.add_description("""\
This template creates a Multi-AZ, multi-subnet VPC infrastructure with managed NAT gateways in the public subnet for each Availability Zone. You can also create additional private subnets with dedicated custom network access control lists (ACLs). If you deploy the Quick Start in a region that doesn't support NAT gateways, NAT instances are deployed instead. **WARNING** This template creates AWS resources. You will be billed for the AWS resources used if you create a stack from this template. QS(0027)""")
PrivateSubnet2BCIDR = t.add_parameter(Parameter(
    "PrivateSubnet2BCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.200.0/21",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 2B with dedicated network ACL located in Availability Zone 2",
))

VPCTenancy = t.add_parameter(Parameter(
    "VPCTenancy",
    Default="default",
    Type="String",
    Description="The allowed tenancy of instances launched into the VPC",
    AllowedValues=["default", "dedicated"],
))

PrivateSubnet4ACIDR = t.add_parameter(Parameter(
    "PrivateSubnet4ACIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.96.0/19",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 4A located in Availability Zone 4",
))

PrivateSubnet3ACIDR = t.add_parameter(Parameter(
    "PrivateSubnet3ACIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.64.0/19",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 3A located in Availability Zone 3",
))

PublicSubnetTag3 = t.add_parameter(Parameter(
    "PublicSubnetTag3",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to public subnets, in format Key=Value (Optional)",
))

PrivateSubnet2ACIDR = t.add_parameter(Parameter(
    "PrivateSubnet2ACIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.32.0/19",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 2A located in Availability Zone 2",
))

PublicSubnet2CIDR = t.add_parameter(Parameter(
    "PublicSubnet2CIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.144.0/20",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for the public DMZ subnet 2 located in Availability Zone 2",
))

KeyPairName = t.add_parameter(Parameter(
    "KeyPairName",
    Default="deprecated",
    Type="String",
    Description="Deprecated. NAT gateways are now supported in all regions.",
))

PrivateSubnet1ACIDR = t.add_parameter(Parameter(
    "PrivateSubnet1ACIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.0.0/19",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 1A located in Availability Zone 1",
))

NumberOfAZs = t.add_parameter(Parameter(
    "NumberOfAZs",
    Default="2",
    Type="String",
    Description="Number of Availability Zones to use in the VPC. This must match your selections in the list of Availability Zones parameter.",
    AllowedValues=["2", "3", "4"],
))

PrivateSubnetBTag1 = t.add_parameter(Parameter(
    "PrivateSubnetBTag1",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="Network=Private",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets B, in format Key=Value (Optional)",
))

PublicSubnetTag1 = t.add_parameter(Parameter(
    "PublicSubnetTag1",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="Network=Public",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to public subnets, in format Key=Value (Optional)",
))

PublicSubnetTag2 = t.add_parameter(Parameter(
    "PublicSubnetTag2",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to public subnets, in format Key=Value (Optional)",
))

PublicSubnet4CIDR = t.add_parameter(Parameter(
    "PublicSubnet4CIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.176.0/20",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for the public DMZ subnet 4 located in Availability Zone 4",
))

CreatePrivateSubnets = t.add_parameter(Parameter(
    "CreatePrivateSubnets",
    Default="true",
    Type="String",
    Description="Set to false to create only public subnets. If false, the CIDR parameters for ALL private subnets will be ignored.",
    AllowedValues=["true", "false"],
))

PrivateSubnetATag1 = t.add_parameter(Parameter(
    "PrivateSubnetATag1",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="Network=Private",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets A, in format Key=Value (Optional)",
))

PrivateSubnetATag3 = t.add_parameter(Parameter(
    "PrivateSubnetATag3",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets A, in format Key=Value (Optional)",
))

PrivateSubnetATag2 = t.add_parameter(Parameter(
    "PrivateSubnetATag2",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets A, in format Key=Value (Optional)",
))

PrivateSubnetBTag2 = t.add_parameter(Parameter(
    "PrivateSubnetBTag2",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets B, in format Key=Value (Optional)",
))

PrivateSubnetBTag3 = t.add_parameter(Parameter(
    "PrivateSubnetBTag3",
    AllowedPattern="^([a-zA-Z0-9+\\-._:/@]+=[a-zA-Z0-9+\\-.,_:/@ *\\\\\"'\\[\\]\\{\\}]*)?$",
    Default="",
    Type="String",
    ConstraintDescription="tags must be in format \"Key=Value\" keys can only contain [a-zA-Z0-9+\\-._:/@], values can contain [a-zA-Z0-9+\\-._:/@ *\\\\\"'\\[\\]\\{\\}]",
    Description="tag to add to private subnets B, in format Key=Value (Optional)",
))

NATInstanceType = t.add_parameter(Parameter(
    "NATInstanceType",
    Default="deprecated",
    Type="String",
    Description="Deprecated. NAT gateways are now supported in all regions.",
))

PublicSubnet3CIDR = t.add_parameter(Parameter(
    "PublicSubnet3CIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.160.0/20",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for the public DMZ subnet 3 located in Availability Zone 3",
))

PrivateSubnet1BCIDR = t.add_parameter(Parameter(
    "PrivateSubnet1BCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.192.0/21",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 1B with dedicated network ACL located in Availability Zone 1",
))

PrivateSubnet3BCIDR = t.add_parameter(Parameter(
    "PrivateSubnet3BCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.208.0/21",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 3B with dedicated network ACL located in Availability Zone 3",
))

PrivateSubnet4BCIDR = t.add_parameter(Parameter(
    "PrivateSubnet4BCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.216.0/21",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for private subnet 4B with dedicated network ACL located in Availability Zone 4",
))

VPCCIDR = t.add_parameter(Parameter(
    "VPCCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.0.0/16",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for the VPC",
))

CreateAdditionalPrivateSubnets = t.add_parameter(Parameter(
    "CreateAdditionalPrivateSubnets",
    Default="false",
    Type="String",
    Description="Set to true to create a network ACL protected subnet in each Availability Zone. If false, the CIDR parameters for those subnets will be ignored. If true, it also requires that the 'Create private subnets' parameter is also true to have any effect.",
    AllowedValues=["true", "false"],
))

AvailabilityZones = t.add_parameter(Parameter(
    "AvailabilityZones",
    Type="List<AWS::EC2::AvailabilityZone::Name>",
    Description="List of Availability Zones to use for the subnets in the VPC. Note: The logical order is preserved.",
))

PublicSubnet1CIDR = t.add_parameter(Parameter(
    "PublicSubnet1CIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(1[6-9]|2[0-8]))$",
    Default="10.0.128.0/20",
    Type="String",
    ConstraintDescription="CIDR block parameter must be in the form x.x.x.x/16-28",
    Description="CIDR block for the public DMZ subnet 1 located in Availability Zone 1",
))

t.add_condition("PrivateSubnetATag3Condition",
    Not(Equals(Ref(PrivateSubnetATag3), ""))
)

t.add_condition("PrivateSubnetATag2Condition",
    Not(Equals(Ref(PrivateSubnetATag2), ""))
)

t.add_condition("PrivateSubnetBTag3Condition",
    Not(Equals(Ref(PrivateSubnetBTag3), ""))
)

t.add_condition("PrivateSubnetBTag1Condition",
    Not(Equals(Ref(PrivateSubnetBTag1), ""))
)

t.add_condition("PublicSubnetTag1Condition",
    Not(Equals(Ref(PublicSubnetTag1), ""))
)

t.add_condition("4AZCondition",
    Equals(Ref(NumberOfAZs), "4")
)

t.add_condition("3AZCondition",
    Or(Equals(Ref(NumberOfAZs), "3"), Condition("4AZCondition"))
)

t.add_condition("PublicSubnetTag3Condition",
    Not(Equals(Ref(PublicSubnetTag3), ""))
)

t.add_condition("PublicSubnetTag2Condition",
    Not(Equals(Ref(PublicSubnetTag2), ""))
)

t.add_condition("PrivateSubnets&4AZCondition",
    And(Condition("PrivateSubnetsCondition"), Condition("4AZCondition"))
)

t.add_condition("PrivateSubnets&3AZCondition",
    And(Condition("PrivateSubnetsCondition"), Condition("3AZCondition"))
)

t.add_condition("NVirginiaRegionCondition",
    Equals(Ref("AWS::Region"), "us-east-1")
)

t.add_condition("AdditionalPrivateSubnetsCondition",
    And(Equals(Ref(CreatePrivateSubnets), "true"), Equals(Ref(CreateAdditionalPrivateSubnets), "true"))
)

t.add_condition("PrivateSubnetBTag2Condition",
    Not(Equals(Ref(PrivateSubnetBTag2), ""))
)

t.add_condition("PrivateSubnetsCondition",
    Equals(Ref(CreatePrivateSubnets), "true")
)

t.add_condition("AdditionalPrivateSubnets&3AZCondition",
    And(Condition("AdditionalPrivateSubnetsCondition"), Condition("3AZCondition"))
)

t.add_condition("AdditionalPrivateSubnets&4AZCondition",
    And(Condition("AdditionalPrivateSubnetsCondition"), Condition("4AZCondition"))
)

t.add_condition("PrivateSubnetATag1Condition",
    Not(Equals(Ref(PrivateSubnetATag1), ""))
)

t.add_condition("GovCloudCondition",
    Equals(Ref("AWS::Region"), "us-gov-west-1")
)

PrivateSubnet2BRoute = t.add_resource(Route(
    "PrivateSubnet2BRoute",
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref("PrivateSubnet2BRouteTable"),
    NatGatewayId=Ref("NATGateway2"),
    Condition="AdditionalPrivateSubnetsCondition",
))

PrivateSubnet3ARouteTable = t.add_resource(RouteTable(
    "PrivateSubnet3ARouteTable",
    VpcId=Ref("VPC"),
    Tags=Tags(
        Name="Private subnet 3A",
        Network="Private",
    ),
    Condition="PrivateSubnets&3AZCondition",
))

PrivateSubnet3BNetworkAclEntryOutbound = t.add_resource(NetworkAclEntry(
    "PrivateSubnet3BNetworkAclEntryOutbound",
    NetworkAclId=Ref("PrivateSubnet3BNetworkAcl"),
    RuleNumber=100,
    Protocol=-1,
    Egress=True,
    RuleAction="allow",
    CidrBlock="0.0.0.0/0",
    Condition="AdditionalPrivateSubnets&3AZCondition",
))

PrivateSubnet2BRouteTableAssociation = t.add_resource(SubnetRouteTableAssociation(
    "PrivateSubnet2BRouteTableAssociation",
    SubnetId=Ref("PrivateSubnet2B"),
    RouteTableId=Ref("PrivateSubnet2BRouteTable"),
    Condition="AdditionalPrivateSubnetsCondition",
))

PrivateSubnet3BRouteTable = t.add_resource(RouteTable(
    "PrivateSubnet3BRouteTable",
    VpcId=Ref("VPC"),
    Tags=Tags(
        Name="Private subnet 3B",
        Network="Private",
    ),
    Condition="AdditionalPrivateSubnets&3AZCondition",
))

PublicSubnet2RouteTableAssociation = t.add_resource(SubnetRouteTableAssociation(
    "PublicSubnet2RouteTableAssociation",
    SubnetId=Ref("PublicSubnet2"),
    RouteTableId=Ref("PublicSubnetRouteTable"),
))

PublicSubnetRouteTable = t.add_resource(RouteTable(
    "PublicSubnetRouteTable",
    VpcId=Ref("VPC"),
    Tags=Tags(
        Name="Public Subnets",
        Network="Public",
    ),
))

PrivateSubnet1ARouteTableAssociation = t.add_resource(SubnetRouteTableAssociation(
    "PrivateSubnet1ARouteTableAssociation",
    SubnetId=Ref("PrivateSubnet1A"),
    RouteTableId=Ref("PrivateSubnet1ARouteTable"),
    Condition="PrivateSubnetsCondition",
))

PrivateSubnet2B = t.add_resource(Subnet(
    "PrivateSubnet2B",
    Tags=Tags(
        Name="Private subnet 2B",
