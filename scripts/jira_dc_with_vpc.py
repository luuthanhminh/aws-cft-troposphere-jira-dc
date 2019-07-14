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
Atlassian Jira Data Center with VPC""")
DBPoolMaxSize = t.add_parameter(Parameter(
    "DBPoolMaxSize",
    Default=20,
    Type="String",
    Description="The maximum number of database connections that can be opened at any time",
))

PublicSubnet1CIDR = t.add_parameter(Parameter(
    "PublicSubnet1CIDR",
    Default="10.0.128.0/20",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the public DMZ subnet 1 located in Availability Zone 1",
))

ClusterNodeInstanceType = t.add_parameter(Parameter(
    "ClusterNodeInstanceType",
    Default="c5.xlarge",
    Type="String",
    ConstraintDescription="Must be an EC2 instance type from the selection list",
    Description="Instance type for the cluster application nodes.",
    AllowedValues=["c4.large", "c4.xlarge", "c4.2xlarge", "c4.4xlarge", "c4.8xlarge", "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge", "c5.18xlarge", "c5d.large", "c5d.xlarge", "c5d.2xlarge", "c5d.4xlarge", "c5d.9xlarge", "c5d.18xlarge", "d2.xlarge", "d2.2xlarge", "d2.4xlarge", "d2.8xlarge", "h1.2xlarge", "h1.4xlarge", "h1.8xlarge", "h1.16xlarge", "i3.large", "i3.xlarge", "i3.2xlarge", "i3.4xlarge", "i3.8xlarge", "i3.16xlarge", "i3.metal", "m4.large", "m4.xlarge", "m4.2xlarge", "m4.4xlarge", "m4.10xlarge", "m4.16xlarge", "m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.12xlarge", "m5.24xlarge", "m5d.large", "m5d.xlarge", "m5d.2xlarge", "m5d.4xlarge", "m5d.12xlarge", "m5d.24xlarge", "r4.large", "r4.xlarge", "r4.2xlarge", "r4.4xlarge", "r4.8xlarge", "r4.16xlarge", "r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge", "r5.12xlarge", "r5.24xlarge", "r5d.large", "r5d.xlarge", "r5d.2xlarge", "r5d.4xlarge", "r5d.12xlarge", "r5d.24xlarge", "t2.medium", "t2.large", "t2.xlarge", "t2.2xlarge", "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge", "x1.16xlarge", "x1.32xlarge", "x1e.xlarge", "x1e.2xlarge", "x1e.4xlarge", "x1e.8xlarge", "x1e.16xlarge", "x1e.32xlarge", "z1d.large", "z1d.xlarge", "z1d.2xlarge", "z1d.3xlarge", "z1d.6xlarge", "z1d.12xlarge"],
))

TomcatEnableLookups = t.add_parameter(Parameter(
    "TomcatEnableLookups",
    Default=False,
    Type="String",
    Description="Set to true if you want calls to request.getRemoteHost() to perform DNS lookups in order to return the actual host name of the remote client",
))

QSS3BucketName = t.add_parameter(Parameter(
    "QSS3BucketName",
    Default="aws-quickstart",
    AllowedPattern="^[0-9a-zA-Z]+([0-9a-zA-Z-]*[0-9a-zA-Z])*$",
    Type="String",
    ConstraintDescription="Quick Start bucket name can include numbers, lowercase letters, uppercase letters, and hyphens (-). It cannot start or end with a hyphen (-).",
    Description="S3 bucket name for the Quick Start assets. Quick Start bucket name can include numbers, lowercase letters, uppercase letters, and hyphens (-). It cannot start or end with a hyphen (-).",
))

PrivateSubnet2CIDR = t.add_parameter(Parameter(
    "PrivateSubnet2CIDR",
    Default="10.0.32.0/19",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR block for private subnet 2 located in Availability Zone 2.",
))

ClusterNodeMin = t.add_parameter(Parameter(
    "ClusterNodeMin",
    Default=1,
    Type="Number",
    Description="Set to 1 for new deployment. Can be updated post launch.",
))

DBTimeBetweenEvictionRunsMillis = t.add_parameter(Parameter(
    "DBTimeBetweenEvictionRunsMillis",
    Default=60000,
    Type="String",
    Description="The number of milliseconds to sleep between runs of the idle object eviction thread. When non-positive, no idle object eviction thread will be run",
))

DBPassword = t.add_parameter(Parameter(
    "DBPassword",
    Type="String",
    Description="Database user account password.",
    MinLength=8,
    AllowedPattern="[a-zA-Z0-9]*",
    NoEcho=True,
    MaxLength=128,
    ConstraintDescription="Must be at least 8 alphanumeric characters.",
))

DBMaxWaitMillis = t.add_parameter(Parameter(
    "DBMaxWaitMillis",
    Default=10000,
    Type="String",
    Description="The length of time (in milliseconds) that Jira is allowed to wait for a database connection to become available (while there are no free ones available in the pool), before returning an error",
))

ClusterNodeVolumeSize = t.add_parameter(Parameter(
    "ClusterNodeVolumeSize",
    Default=50,
    Type="Number",
    Description="Size of cluster node root volume in Gb (note - size based upon Application indexes x 4)",
))

KeyPairName = t.add_parameter(Parameter(
    "KeyPairName",
    Default="",
    Type="String",
    ConstraintDescription="Must be the name of an existing EC2 Key Pair.",
    Description="The EC2 Key Pair to allow SSH access to the instances",
))

DBTestWhileIdle = t.add_parameter(Parameter(
    "DBTestWhileIdle",
    Default=True,
    Type="String",
    Description="Periodically tests if the database connection is valid when it is idle",
))

TomcatProtocol = t.add_parameter(Parameter(
    "TomcatProtocol",
    Default="HTTP/1.1",
    Type="String",
    Description="Sets the protocol to handle incoming traffic",
))

TomcatRedirectPort = t.add_parameter(Parameter(
    "TomcatRedirectPort",
    Default=8443,
    Type="String",
    Description="The port number for Catalina to use when automatically redirecting a non-SSL connector actioning a redirect to a SSL URI",
))

DeploymentAutomationPlaybook = t.add_parameter(Parameter(
    "DeploymentAutomationPlaybook",
    Default="aws_jira_dc_node.yml",
    Type="String",
    Description="The Ansible playbook to invoke to initialise the Jira node on first start.",
))

JiraProduct = t.add_parameter(Parameter(
    "JiraProduct",
    Default="Software",
    ConstraintDescription="Must be \"Core\", \"Software\", or \"ServiceDesk\".",
    Type="String",
    Description="The Jira product to install.",
    AllowedValues=["Core", "Software", "ServiceDesk"],
))

DBMaxIdle = t.add_parameter(Parameter(
    "DBMaxIdle",
    Default=20,
    Type="String",
    Description="The maximum number of database connections that are allowed to remain idle in the pool",
))

DBStorage = t.add_parameter(Parameter(
    "DBStorage",
    Default=200,
    Type="Number",
    Description="Database allocated storage size, in gigabytes (GB)",
))

PublicSubnet2CIDR = t.add_parameter(Parameter(
    "PublicSubnet2CIDR",
    Default="10.0.144.0/20",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the public DMZ subnet 2 located in Availability Zone 2",
))

DBPoolMinSize = t.add_parameter(Parameter(
    "DBPoolMinSize",
    Default=20,
    Type="String",
    Description="The minimum number of idle database connections that are kept open at any time",
))

DBTestOnBorrow = t.add_parameter(Parameter(
    "DBTestOnBorrow",
    Default=False,
    Type="String",
    Description="Tests if the database connection is valid when it is borrowed from the database connection pool by Jira",
))

TomcatConnectionTimeout = t.add_parameter(Parameter(
    "TomcatConnectionTimeout",
    Default=20000,
    Type="String",
    Description="The number of milliseconds this Connector will wait, after accepting a connection, for the request URI line to be presented",
))

DeploymentAutomationBranch = t.add_parameter(Parameter(
    "DeploymentAutomationBranch",
    Default="master",
    Type="String",
    Description="The deployment automation repository branch to pull from.",
))

JiraVersion = t.add_parameter(Parameter(
    "JiraVersion",
    Default="8.1.0",
    AllowedPattern="(\\d+\\.\\d+\\.\\d+(-?.*))|(latest)",
    Type="String",
    ConstraintDescription="Must be a valid version number or 'latest'; for example, 8.1.0 for Jira Software, or 4.1.0 for ServiceDesk.",
    Description="The version of Jira Software or Jira Service Desk to install. Find valid versions at https://confluence.atlassian.com/x/TVlNLg (Jira Software), https://confluence.atlassian.com/x/jh9-Lg (Jira Service Desk), or https://confluence.atlassian.com/x/XM2EO (Atlassian Enterprise Releases).",
))

DeploymentAutomationKeyName = t.add_parameter(Parameter(
    "DeploymentAutomationKeyName",
    Default="",
    Type="String",
    Description="Named KeyPair name to use with this repository. The key should be imported into the SSM parameter store. (Optional)",
))

DeploymentAutomationRepository = t.add_parameter(Parameter(
    "DeploymentAutomationRepository",
    Default="https://bitbucket.org/atlassian/dc-deployments-automation.git",
    Type="String",
    Description="The deployment automation repository to use for per-node initialisation. Leave this as default unless you have customisations.",
))

DBRemoveAbandoned = t.add_parameter(Parameter(
    "DBRemoveAbandoned",
    Default=True,
    Type="String",
    Description="Flag to remove abandoned database connections if they exceed the Removed Abandoned Timeout",
))

MailEnabled = t.add_parameter(Parameter(
    "MailEnabled",
    Default=True,
    Type="String",
    ConstraintDescription="Must be 'true' or 'false'.",
    Description="Enable mail processing and sending",
    AllowedValues=[True, False],
))

VPCCIDR = t.add_parameter(Parameter(
    "VPCCIDR",
    Default="10.0.0.0/16",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block for the VPC",
))

TomcatDefaultConnectorPort = t.add_parameter(Parameter(
    "TomcatDefaultConnectorPort",
    Default=8080,
    Type="String",
    Description="The port on which to serve the application",
))

TomcatAcceptCount = t.add_parameter(Parameter(
    "TomcatAcceptCount",
    Default=10,
    Type="String",
    Description="The maximum queue length for incoming connection requests when all possible request processing threads are in use",
))

CatalinaOpts = t.add_parameter(Parameter(
    "CatalinaOpts",
    Default="",
    Type="String",
    Description="Pass in any additional jvm options to tune Catalina",
))

CustomDnsName = t.add_parameter(Parameter(
    "CustomDnsName",
    Default="",
    Type="String",
    Description="Use custom existing DNS name for your Data Center instance. This will take precedence over HostedZone. Please note: you must own the domain and configure it to point at the load balancer.",
))

DBIops = t.add_parameter(Parameter(
    "DBIops",
    Description="Must be in the range of 1000 - 30000 and a multiple of 1000. This value is only used with Provisioned IOPS. Note: The ratio of IOPS per allocated-storage must be between 3.00 and 10.00",
    Default=1000,
    ConstraintDescription="Must be in the range 1000 - 30000",
    MaxValue=30000,
    MinValue=1000,
    Type="Number",
))

AccessCIDR = t.add_parameter(Parameter(
    "AccessCIDR",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR Block allowed to access the Atlassian product. This should be set to a trusted IP range; if you want to give public access use '0.0.0.0/0'.",
))

TomcatMaxThreads = t.add_parameter(Parameter(
    "TomcatMaxThreads",
    Default=200,
    Type="String",
    Description="The maximum number of request processing threads to be created by this Connector, which therefore determines the maximum number of simultaneous requests that can be handled",
))

SSLCertificateARN = t.add_parameter(Parameter(
    "SSLCertificateARN",
    Default="",
    MinLength=0,
    Type="String",
    Description="Amazon Resource Name (ARN) of your SSL certificate. Every certificate created with the AWS Certificate Manager has a corresponding ARN. To use a certificate generated outside of AWS, you need to import it into AWS Certificate Manager first. AWS Certificate Manager will provide you with its ARN, which you can use here.",
    MaxLength=90,
))

DBMinEvictableIdleTimeMillis = t.add_parameter(Parameter(
    "DBMinEvictableIdleTimeMillis",
    Default=180000,
    Type="String",
    Description="The minimum amount of time an object may sit idle in the database connection pool before it is eligible for eviction by the idle object eviction",
))

DBMasterUserPassword = t.add_parameter(Parameter(
    "DBMasterUserPassword",
    Type="String",
    Description="Database admin account password.",
    MinLength=8,
    AllowedPattern="[a-zA-Z0-9]*",
    NoEcho=True,
    MaxLength=128,
    ConstraintDescription="Must be at least 8 alphanumeric characters.",
))

AssociatePublicIpAddress = t.add_parameter(Parameter(
    "AssociatePublicIpAddress",
    Default=True,
    Type="String",
    ConstraintDescription="Must be 'true' or 'false'.",
    Description="Controls if the EC2 instances are assigned a public IP address",
    AllowedValues=[True, False],
))

DBStorageType = t.add_parameter(Parameter(
    "DBStorageType",
    Default="General Purpose (SSD)",
    Type="String",
    ConstraintDescription="Must be 'General Purpose (SSD)' or 'Provisioned IOPS'.",
    Description="Database storage type",
    AllowedValues=["General Purpose (SSD)", "Provisioned IOPS"],
))

DBStorageEncrypted = t.add_parameter(Parameter(
    "DBStorageEncrypted",
    Default=False,
    Type="String",
    Description="Whether or not to encrypt the database",
    AllowedValues=[True, False],
))

TomcatScheme = t.add_parameter(Parameter(
    "TomcatScheme",
    Default="http",
    Type="String",
    Description="The name of the protocol you wish to have returned, ie 'https' for an SSL Connector. The value of this setting also configures Tomcat's proxy port (443/80) and secure (true/false) settings appropriately.",
    AllowedValues=["http", "https"],
))

TomcatMinSpareThreads = t.add_parameter(Parameter(
    "TomcatMinSpareThreads",
    Default=10,
    Type="String",
    Description="The minimum number of threads always kept running",
))

JvmHeapOverride = t.add_parameter(Parameter(
    "JvmHeapOverride",
    Default="",
    Type="String",
    Description="Override the default amount of memory to allocate to the JVM for your instance type - set size in meg or gig e.g. 1024m or 1g",
))

DBMultiAZ = t.add_parameter(Parameter(
    "DBMultiAZ",
    Default=True,
    Type="String",
    ConstraintDescription="Must be 'true' or 'false'.",
    Description="Whether to provision a multi-AZ RDS instance.",
    AllowedValues=[True, False],
))

QSS3KeyPrefix = t.add_parameter(Parameter(
    "QSS3KeyPrefix",
    Default="quickstart-atlassian-jira/",
    AllowedPattern="^[0-9a-zA-Z-/]*$",
    Type="String",
    ConstraintDescription="Quick Start key prefix can include numbers, lowercase letters, uppercase letters, hyphens (-), and forward slash (/).",
    Description="S3 key prefix for the Quick Start assets. Quick Start key prefix can include numbers, lowercase letters, uppercase letters, hyphens (-), and forward slash (/).",
))

DBMinIdle = t.add_parameter(Parameter(
    "DBMinIdle",
    Default=10,
    Type="String",
    Description="The minimum number of idle database connections that are kept open at any time",
))

PrivateSubnet1CIDR = t.add_parameter(Parameter(
    "PrivateSubnet1CIDR",
    Default="10.0.0.0/19",
    AllowedPattern="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/([0-9]|[1-2][0-9]|3[0-2]))$",
    Type="String",
    Description="CIDR block for private subnet 1 located in Availability Zone 1.",
))

DBRemoveAbandonedTimeout = t.add_parameter(Parameter(
    "DBRemoveAbandonedTimeout",
    Default=60,
    Type="String",
    Description="The length of time (in seconds) that a database connection can be idle before it is considered abandoned",
))

HostedZone = t.add_parameter(Parameter(
    "HostedZone",
    Default="",
    Type="String",
    ConstraintDescription="Must be the name of an existing Route53 Hosted Zone.",
    Description="The domain name of the Route53 PRIVATE Hosted Zone in which to create cnames",
))

DBInstanceClass = t.add_parameter(Parameter(
    "DBInstanceClass",
    Default="db.m4.large",
    Type="String",
    ConstraintDescription="Must be a valid RDS instance class, from the selection list",
    Description="RDS instance type",
    AllowedValues=["db.m4.large", "db.m4.xlarge", "db.m4.2xlarge", "db.m4.4xlarge", "db.m4.10xlarge", "db.m4.16xlarge", "db.r4.large", "db.r4.xlarge", "db.r4.2xlarge", "db.r4.4xlarge", "db.r4.8xlarge", "db.r4.16xlarge", "db.t2.medium", "db.t2.large", "db.t2.xlarge", "db.t2.2xlarge"],
))

AvailabilityZones = t.add_parameter(Parameter(
    "AvailabilityZones",
    Type="List<AWS::EC2::AvailabilityZone::Name>",
    Description="List of Availability Zones to use for the subnets in the VPC. Note: You must specify 2 AZs here; if more are specified only the first 2 will be used.",
))

CidrBlock = t.add_parameter(Parameter(
    "CidrBlock",
    Description="CIDR block allowed to access the Atlassian product. This should be set to a trusted IP range; if you want to give public access use '0.0.0.0/0'.",
    ConstraintDescription="Must be a valid IP CIDR range of the form x.x.x.x/x.",
    AllowedPattern="(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
    MinLength=9,
    MaxLength=18,
    Type="String",
))

TomcatContextPath = t.add_parameter(Parameter(
    "TomcatContextPath",
    Default="",
    AllowedPattern="^(\\/[A-z_\\-0-9\\.]+)?$",
    Type="String",
    Description="The context path of this web application, which is matched against the beginning of each request URI to select the appropriate web application for processing. If used, must include leading \"/\"",
))

ClusterNodeMax = t.add_parameter(Parameter(
    "ClusterNodeMax",
    Default=1,
    Type="Number",
    Description="Maximum number of nodes in the cluster.",
))

t.add_condition("UseDatabaseEncryption",
    Equals(Ref(DBStorageEncrypted), True)
)

t.add_condition("GovCloudCondition",
    Equals(Ref("AWS::Region"), "us-gov-west-1")
)

JiraDCStack = t.add_resource(Stack(
    "JiraDCStack",
    TemplateURL={ "Fn::Sub": ["https://${QSS3BucketName}.${QSS3Region}.amazonaws.com/${QSS3KeyPrefix}templates/quickstart-jira-dc.template.yaml", { "QSS3Region": If("GovCloudCondition", "s3-us-gov-west-1", "s3") }] },
    Parameters={ "DBPoolMaxSize": Ref(DBPoolMaxSize), "ClusterNodeInstanceType": Ref(ClusterNodeInstanceType), "TomcatEnableLookups": Ref(TomcatEnableLookups), "ClusterNodeMin": Ref(ClusterNodeMin), "DBTimeBetweenEvictionRunsMillis": Ref(DBTimeBetweenEvictionRunsMillis), "DBPassword": Ref(DBPassword), "DBMaxWaitMillis": Ref(DBMaxWaitMillis), "ClusterNodeVolumeSize": Ref(ClusterNodeVolumeSize), "KeyPairName": Ref(KeyPairName), "DBTestWhileIdle": Ref(DBTestWhileIdle), "TomcatProtocol": Ref(TomcatProtocol), "TomcatRedirectPort": Ref(TomcatRedirectPort), "JiraProduct": Ref(JiraProduct), "DBMaxIdle": Ref(DBMaxIdle), "DBStorage": Ref(DBStorage), "DBPoolMinSize": Ref(DBPoolMinSize), "DBTestOnBorrow": Ref(DBTestOnBorrow), "TomcatConnectionTimeout": Ref(TomcatConnectionTimeout), "DeploymentAutomationBranch": Ref(DeploymentAutomationBranch), "JiraVersion": Ref(JiraVersion), "DeploymentAutomationKeyName": Ref(DeploymentAutomationKeyName), "DeploymentAutomationRepository": Ref(DeploymentAutomationRepository), "DBRemoveAbandoned": Ref(DBRemoveAbandoned), "MailEnabled": Ref(MailEnabled), "TomcatDefaultConnectorPort": Ref(TomcatDefaultConnectorPort), "TomcatAcceptCount": Ref(TomcatAcceptCount), "CatalinaOpts": Ref(CatalinaOpts), "CustomDnsName": Ref(CustomDnsName), "DBIops": Ref(DBIops), "TomcatMaxThreads": Ref(TomcatMaxThreads), "SSLCertificateARN": Ref(SSLCertificateARN), "DBMinEvictableIdleTimeMillis": Ref(DBMinEvictableIdleTimeMillis), "DBMasterUserPassword": Ref(DBMasterUserPassword), "AssociatePublicIpAddress": Ref(AssociatePublicIpAddress), "DBStorageType": Ref(DBStorageType), "DBStorageEncrypted": Ref(DBStorageEncrypted), "TomcatScheme": Ref(TomcatScheme), "TomcatMinSpareThreads": Ref(TomcatMinSpareThreads), "JvmHeapOverride": Ref(JvmHeapOverride), "DBMultiAZ": Ref(DBMultiAZ), "DBMinIdle": Ref(DBMinIdle), "DBRemoveAbandonedTimeout": Ref(DBRemoveAbandonedTimeout), "HostedZone": Ref(HostedZone), "DBInstanceClass": Ref(DBInstanceClass), "CidrBlock": Ref(CidrBlock), "TomcatContextPath": Ref(TomcatContextPath), "ClusterNodeMax": Ref(ClusterNodeMax) },
    DependsOn="VPCStack",
))

VPCStack = t.add_resource(Stack(
    "VPCStack",
    TemplateURL={ "Fn::Sub": ["https://${QSS3BucketName}.${QSS3Region}.amazonaws.com/${QSS3KeyPrefix}submodules/quickstart-atlassian-services/templates/quickstart-vpc-for-atlassian-services.yaml", { "QSS3Region": If("GovCloudCondition", "s3-us-gov-west-1", "s3") }] },
    Parameters={ "PrivateSubnet1CIDR": Ref(PrivateSubnet1CIDR), "VPCCIDR": Ref(VPCCIDR), "PublicSubnet1CIDR": Ref(PublicSubnet1CIDR), "PrivateSubnet2CIDR": Ref(PrivateSubnet2CIDR), "AccessCIDR": Ref(AccessCIDR), "AvailabilityZones": Join(",", Ref(AvailabilityZones)), "PublicSubnet2CIDR": Ref(PublicSubnet2CIDR), "KeyPairName": Ref(KeyPairName) },
))

DBEncryptionKey = t.add_output(Output(
    "DBEncryptionKey",
    Value=GetAtt(JiraDCStack, "Outputs.DBEncryptionKey"),
    Description="The alias of the encryption key created for RDS",
    Condition="UseDatabaseEncryption",
))

BastionIP = t.add_output(Output(
    "BastionIP",
    Description="Bastion node IP (use as a jumpbox to connect to the nodes)",
    Value=GetAtt(VPCStack, "Outputs.BastionPubIp"),
))

SGname = t.add_output(Output(
    "SGname",
    Description="The name of the SecurityGroup",
    Value=GetAtt(JiraDCStack, "Outputs.SGname"),
))

DBEndpointAddress = t.add_output(Output(
    "DBEndpointAddress",
    Description="The Database Connection String",
    Value=GetAtt(JiraDCStack, "Outputs.DBEndpointAddress"),
))

LoadBalancerURL = t.add_output(Output(
    "LoadBalancerURL",
    Description="The Load Balancer URL",
    Value=GetAtt(JiraDCStack, "Outputs.LoadBalancerURL"),
))

ServiceURL = t.add_output(Output(
    "ServiceURL",
    Description="The URL to access this Atlassian service",
    Value=GetAtt(JiraDCStack, "Outputs.ServiceURL"),
))

EFSCname = t.add_output(Output(
    "EFSCname",
    Description="The cname of the EFS",
    Value=GetAtt(JiraDCStack, "Outputs.EFSCname"),
))

print(t.to_json())
