from troposphere import Base64, Select, FindInMap, GetAtt
from troposphere import GetAZs, Join, Output, If, And, Not
from troposphere import Or, Equals, Condition
from troposphere import Parameter, Ref, Tags, Template
from troposphere.cloudformation import Init
from troposphere.cloudfront import Distribution
from troposphere.cloudfront import DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.ec2 import PortRange
from troposphere.route53 import RecordSet, RecordSetType
from troposphere.autoscaling import AutoScalingGroup
from troposphere.rds import DBInstance
from troposphere.efs import FileSystem
from troposphere.ec2 import SecurityGroup
from troposphere.ec2 import SecurityGroupIngress
from troposphere.rds import DBSubnetGroup
from troposphere.iam import Role
from troposphere.kms import Alias
from troposphere.efs import MountTarget
from troposphere.elasticloadbalancing import LoadBalancer, HealthCheck, ConnectionDrainingPolicy, AccessLoggingPolicy
from troposphere.iam import InstanceProfile
from troposphere.kms import Key
from troposphere.autoscaling import LaunchConfiguration


t = Template()

t.add_version("2010-09-09")

t.add_description("""\
Atlassian Jira Data Center QS(0035)""")
DBPoolMaxSize = t.add_parameter(Parameter(
    "DBPoolMaxSize",
    Default=20,
    Type="String",
    Description="The maximum number of database connections that can be opened at any time",
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
    ConstraintDescription="Must be \"Core\", \"Software\", or \"ServiceDesk\"",
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
    Default="7.13.3",
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

DBMinIdle = t.add_parameter(Parameter(
    "DBMinIdle",
    Default=10,
    Type="String",
    Description="The minimum number of idle database connections that are kept open at any time",
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

CidrBlock = t.add_parameter(Parameter(
    "CidrBlock",
    Description="CIDR Block allowed to access the Atlassian product. This should be set to a trusted IP range; if you want to give public access use '0.0.0.0/0'.",
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

t.add_condition("DoSetDBMasterUserPassword",
    Not(Equals(Ref(DBMasterUserPassword), ""))
)

t.add_condition("SSLScheme",
    Equals(Ref(TomcatScheme), "https")
)

t.add_condition("KeyProvided",
    Not(Equals(Ref(KeyPairName), ""))
)

t.add_condition("UseDatabaseEncryption",
    Equals(Ref(DBStorageEncrypted), True)
)

t.add_condition("OverrideHeap",
    Not(Equals(Ref(JvmHeapOverride), ""))
)

t.add_condition("UseContextPath",
    Not(Equals(Ref(TomcatContextPath), ""))
)

t.add_condition("UseCustomDnsName",
    Not(Equals(Ref(CustomDnsName), ""))
)

t.add_condition("UsePublicIp",
    Equals(Ref(AssociatePublicIpAddress), "true")
)

t.add_condition("DBProvisionedIops",
    Equals(Ref(DBStorageType), "Provisioned IOPS")
)

t.add_condition("UseHostedZone",
    Not(Equals(Ref(HostedZone), ""))
)

t.add_condition("DisableMail",
    Not(Equals(Ref(MailEnabled), True))
)

t.add_condition("DoSSL",
    Not(Equals(Ref(SSLCertificateARN), ""))
)

t.add_mapping("JIRAProduct2NameAndVersion",
{u'Core': {u'fulldisplayname': u'"Atlassian Jira Core"',
           u'name': u'jira-core',
           u'shortdisplayname': u'"Jira Core"'},
 u'ServiceDesk': {u'fulldisplayname': u'"Atlassian Jira Service Desk"',
                  u'name': u'servicedesk',
                  u'shortdisplayname': u'"Jira SD"'},
 u'Software': {u'fulldisplayname': u'"Atlassian Jira Software"',
               u'name': u'jira-software',
               u'shortdisplayname': u'"Jira SW"'}}
)

t.add_mapping("AWSInstanceType2Arch",
{u'c4.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c4.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c4.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c4.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'4608m'},
 u'c5.18xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5.9xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5.large': {u'Arch': u'HVM64', u'Jvmheap': u'2048m'},
 u'c5.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u'c5d.18xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5d.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5d.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5d.9xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'c5d.large': {u'Arch': u'HVM64', u'Jvmheap': u'2048m'},
 u'c5d.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u'd2.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'd2.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'd2.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'd2.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'h1.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'h1.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'h1.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'h1.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.large': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.metal': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'i3.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm4.10xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm4.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm4.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm4.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm4.large': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u'm4.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5.12xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5.24xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5.large': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u'm5.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5d.12xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5d.24xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5d.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5d.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'm5d.large': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u'm5d.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.large': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r4.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.12xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.24xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.large': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.12xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.24xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.large': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'r5d.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u't2.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u't2.large': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u't2.medium': {u'Arch': u'HVM64', u'Jvmheap': u'2048m'},
 u't2.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u't3.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u't3.large': {u'Arch': u'HVM64', u'Jvmheap': u'5120m'},
 u't3.medium': {u'Arch': u'HVM64', u'Jvmheap': u'2048m'},
 u't3.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1.32xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.16xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.32xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.4xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.8xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'x1e.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.12xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.2xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.3xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.6xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.large': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'},
 u'z1d.xlarge': {u'Arch': u'HVM64', u'Jvmheap': u'12288m'}}
)

t.add_mapping("AWSRegionArch2AMI",
{u'ap-northeast-1': {u'HVM64': u'ami-00d101850e971728d',
                     u'HVMG2': u'NOT_SUPPORTED'},
 u'ap-northeast-2': {u'HVM64': u'ami-08ab3f7e72215fe91',
                     u'HVMG2': u'NOT_SUPPORTED'},
 u'ap-south-1': {u'HVM64': u'ami-00e782930f1c3dbc7',
                 u'HVMG2': u'NOT_SUPPORTED'},
 u'ap-southeast-1': {u'HVM64': u'ami-0b5a47f8865280111',
                     u'HVMG2': u'NOT_SUPPORTED'},
 u'ap-southeast-2': {u'HVM64': u'ami-0fb7513bcdc525c3b',
                     u'HVMG2': u'NOT_SUPPORTED'},
 u'ca-central-1': {u'HVM64': u'ami-08a9b721ecc5b0a53',
                   u'HVMG2': u'NOT_SUPPORTED'},
 u'eu-central-1': {u'HVM64': u'ami-0ebe657bc328d4e82',
                   u'HVMG2': u'NOT_SUPPORTED'},
 u'eu-north-1': {u'HVM64': u'ami-1fb13961', u'HVMG2': u'NOT_SUPPORTED'},
 u'eu-west-1': {u'HVM64': u'ami-030dbca661d402413',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'eu-west-2': {u'HVM64': u'ami-0009a33f033d8b7b6',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'eu-west-3': {u'HVM64': u'ami-0ebb3a801d5fb8b9b',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'sa-east-1': {u'HVM64': u'ami-058141e091292ecf0',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'us-east-1': {u'HVM64': u'ami-0c6b1d09930fac512',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'us-east-2': {u'HVM64': u'ami-0ebbf2179e615c338',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'us-west-1': {u'HVM64': u'ami-015954d5e5548d13b',
                u'HVMG2': u'NOT_SUPPORTED'},
 u'us-west-2': {u'HVM64': u'ami-0cb72367e98845d43',
                u'HVMG2': u'NOT_SUPPORTED'}}
)

LoadBalancerCname = t.add_resource(RecordSetType(
    "LoadBalancerCname",
    Comment="Route53 cname for the ALB",
    Name=Join(".", [Ref("AWS::StackName"), Ref(HostedZone)]),
    HostedZoneName=Ref(HostedZone),
    ResourceRecords=[GetAtt("LoadBalancer", "DNSName")],
    TTL=900,
    Type="CNAME",
    Condition="UseHostedZone",
))

EFSCname = t.add_resource(RecordSetType(
    "EFSCname",
    Comment="Route53 cname for the efs",
    Name=If("UseHostedZone", Join(".", [Ref("AWS::StackName"), "efs", Ref(HostedZone)]), ""),
    HostedZoneName=Ref(HostedZone),
    ResourceRecords=[Join(".", [Ref("ElasticFileSystem"), "efs", Ref("AWS::Region"), "amazonaws.com."])],
    TTL=900,
    Type="CNAME",
    Condition="UseHostedZone",
))

DBCname = t.add_resource(RecordSetType(
    "DBCname",
    Comment="Route53 cname for the RDS",
    Name=Join(".", [Ref("AWS::StackName"), "db", Ref(HostedZone)]),
    HostedZoneName=Ref(HostedZone),
    ResourceRecords=[GetAtt("DB", "Endpoint.Address")],
    TTL=900,
    Type="CNAME",
    Condition="UseHostedZone",
))

ClusterNodeGroup = t.add_resource(AutoScalingGroup(
    "ClusterNodeGroup",
    DesiredCapacity=Ref(ClusterNodeMin),
    Tags=Tags(
        Name={ "Fn::Sub": ["${StackName} Jira Node", { "StackName": Ref("AWS::StackName") }] },
        Cluster=Ref("AWS::StackName"),
    ),
    LaunchConfigurationName=Ref("ClusterNodeLaunchConfig"),
    MinSize=Ref(ClusterNodeMin),
    MaxSize=Ref(ClusterNodeMax),
    VPCZoneIdentifier={ "Fn::Split": [",", { "Fn::ImportValue": "ATL-PriNets" }] },
    LoadBalancerNames=[Ref("LoadBalancer")],
))

DB = t.add_resource(DBInstance(
    "DB",
    Engine="postgres",
    MultiAZ=Ref(DBMultiAZ),
    Tags=Tags(
        Name={ "Fn::Sub": ["${StackName} Jira PostgreSQL Database", { "StackName": Ref("AWS::StackName") }] },
    ),
    MasterUsername="postgres",
    MasterUserPassword=If("DoSetDBMasterUserPassword", Ref(DBMasterUserPassword), Ref("AWS::NoValue")),
    KmsKeyId=If("UseDatabaseEncryption", GetAtt("EncryptionKey", "Arn"), Ref("AWS::NoValue")),
    StorageType=If("DBProvisionedIops", "io1", "gp2"),
    VPCSecurityGroups=[Ref("SecurityGroup")],
    Iops=If("DBProvisionedIops", Ref(DBIops), Ref("AWS::NoValue")),
    StorageEncrypted=If("UseDatabaseEncryption", Ref(DBStorageEncrypted), Ref("AWS::NoValue")),
    AllocatedStorage=Ref(DBStorage),
    EngineVersion=9.6,
    DBInstanceClass=Ref(DBInstanceClass),
    DBSubnetGroupName=Ref("DBSubnetGroup"),
    DBInstanceIdentifier=Ref("AWS::StackName"),
))

ElasticFileSystem = t.add_resource(FileSystem(
    "ElasticFileSystem",
    FileSystemTags=[{ "Value": Join(" ", [Ref("AWS::StackName"), "cluster shared-files"]), "Key": "Name" }, { "Value": Ref("AWS::StackId"), "Key": "Application" }],
))

SecurityGroup = t.add_resource(SecurityGroup(
    "SecurityGroup",
    SecurityGroupIngress=[{ "ToPort": 22, "IpProtocol": "tcp", "CidrIp": Ref(CidrBlock), "FromPort": 22 }, { "ToPort": 80, "IpProtocol": "tcp", "CidrIp": Ref(CidrBlock), "FromPort": 80 }, { "ToPort": 443, "IpProtocol": "tcp", "CidrIp": Ref(CidrBlock), "FromPort": 443 }],
    VpcId={ "Fn::ImportValue": "ATL-VPCID" },
    GroupDescription="Security group allowing SSH and HTTP/HTTPS access",
    Tags=Tags(
        Name=Join(" ", [Ref("AWS::StackName"), "sg"]),
    ),
))

SecurityGroupIngress = t.add_resource(SecurityGroupIngress(
    "SecurityGroupIngress",
    ToPort=-1,
    IpProtocol=-1,
    SourceSecurityGroupId=Ref(SecurityGroup),
    GroupId=Ref(SecurityGroup),
    FromPort=-1,
))

DBSubnetGroup = t.add_resource(DBSubnetGroup(
    "DBSubnetGroup",
    SubnetIds={ "Fn::Split": [",", { "Fn::ImportValue": "ATL-PriNets" }] },
    DBSubnetGroupDescription="DBSubnetGroup",
))

JiraClusterNodeRole = t.add_resource(Role(
    "JiraClusterNodeRole",
    Path="/",
    ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"],
    Policies=[{ "PolicyName": "JiraClusterNodePolicy", "PolicyDocument": { "Version": "2012-10-17", "Statement": [{ "Action": ["ec2:DescribeInstances", "route53:ListHostedZones", "route53:ListResourceRecordSet"], "Resource": ["*"], "Effect": "Allow" }, { "Action": ["route53:ChangeResourceRecordSets"], "Resource": ["arn:aws:route53:::healthcheck/*", "arn:aws:route53:::change/*", "arn:aws:route53:::hostedzone/*", "arn:aws:route53:::delegationset/*"], "Effect": "Allow" }] } }],
    AssumeRolePolicyDocument={ "Version": "2012-10-17", "Statement": [{ "Action": ["sts:AssumeRole"], "Effect": "Allow", "Principal": { "Service": ["ec2.amazonaws.com"] } }] },
))

EncryptionKeyAlias = t.add_resource(Alias(
    "EncryptionKeyAlias",
    TargetKeyId=Ref("EncryptionKey"),
    AliasName={ "Fn::Sub": "alias/${AWS::StackName}" },
    Condition="UseDatabaseEncryption",
))

EFSMountAz1 = t.add_resource(MountTarget(
    "EFSMountAz1",
    SubnetId=Select(0, { "Fn::Split": [",", { "Fn::ImportValue": "ATL-PriNets" }] }),
    FileSystemId=Ref(ElasticFileSystem),
    SecurityGroups=[Ref(SecurityGroup)],
))

LoadBalancer = t.add_resource(LoadBalancer(
    "LoadBalancer",
    AppCookieStickinessPolicy=[{ "PolicyName": "JSessionIdStickiness", "CookieName": "JSESSIONID" }],
    ConnectionDrainingPolicy=ConnectionDrainingPolicy(
        Enabled=True,
        Timeout=30,
    ),
    Subnets={ "Fn::Split": [",", { "Fn::ImportValue": "ATL-PubNets" }] },
    HealthCheck=HealthCheck(
        HealthyThreshold=2,
        Interval=30,
        Target=If("UseContextPath", Join("", ["HTTP:", Ref(TomcatDefaultConnectorPort), Ref(TomcatContextPath), "/status"]), Join("", ["HTTP:", Ref(TomcatDefaultConnectorPort), "/status"])),
        Timeout=29,
        UnhealthyThreshold=2,
    ),
    Tags=Tags(
        Name={ "Fn::Sub": ["${StackName}-LoadBalancer", { "StackName": Ref("AWS::StackName") }] },
        Cluster=Ref("AWS::StackName"),
    ),
    Listeners=[{ "InstancePort": Ref(TomcatDefaultConnectorPort), "PolicyNames": ["JSessionIdStickiness"], "LoadBalancerPort": 80, "Protocol": "HTTP", "InstanceProtocol": "HTTP" }, If("DoSSL", { "InstancePort": Ref(TomcatDefaultConnectorPort), "Protocol": "HTTPS", "InstanceProtocol": "HTTP", "LoadBalancerPort": "443", "PolicyNames": ["JSessionIdStickiness"], "SSLCertificateId": Ref(SSLCertificateARN) }, Ref("AWS::NoValue"))],
    CrossZone=True,
    SecurityGroups=[Ref(SecurityGroup)],
    ConnectionSettings={ "IdleTimeout": 3600 },
    Scheme=If("UsePublicIp", "internet-facing", "internal"),
))

EFSMountAz2 = t.add_resource(MountTarget(
    "EFSMountAz2",
    SubnetId=Select(1, { "Fn::Split": [",", { "Fn::ImportValue": "ATL-PriNets" }] }),
    FileSystemId=Ref(ElasticFileSystem),
    SecurityGroups=[Ref(SecurityGroup)],
))

JiraClusterNodeInstanceProfile = t.add_resource(InstanceProfile(
    "JiraClusterNodeInstanceProfile",
    Path="/",
    Roles=[Ref(JiraClusterNodeRole)],
))

EncryptionKey = t.add_resource(Key(
    "EncryptionKey",
    KeyPolicy={ "Version": "2012-10-17", "Id": { "Fn::Sub": "${AWS::StackName}" }, "Statement": [{ "Action": "kms:*", "Resource": "*", "Effect": "Allow", "Principal": { "AWS": [{ "Fn::Sub": "arn:aws:iam::${AWS::AccountId}:root" }] } }] },
    Tags=Tags(
        Name={ "Fn::Sub": ["${StackName} Encryption Key", { "StackName": Ref("AWS::StackName") }] },
    ),
    Condition="UseDatabaseEncryption",
))

ClusterNodeLaunchConfig = t.add_resource(LaunchConfiguration(
    "ClusterNodeLaunchConfig",
    Comment="",
    Metadata=Init(
        { "config": { "files": { "/opt/atlassian/bin/clone_deployment_repo": { "content": { "Fn::Sub": "#!/bin/bash\nkey_location=/root/.ssh/deployment_repo_key\nkey_name=\"${DeploymentAutomationKeyName}\"\n\nyum install -y git\nif [[ ! -z \"$key_name\" ]]; then\n    # Ensure awscli is up to date\n    yum install -y awscli jq\n    key_val=$(aws --region=${AWS::Region} ssm get-parameters --names \"$key_name\" --with-decryption | jq --raw-output '.Parameters[0] .Value')\n    echo -e $key_val > $key_location\n    chmod 600 $key_location\n    export GIT_SSH_COMMAND=\"ssh -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -i $key_location\"\nelse\n    export GIT_SSH_COMMAND=\"ssh -o IdentitiesOnly=yes -o StrictHostKeyChecking=no\"\nfi\n\ngit clone \"${DeploymentAutomationRepository}\" -b \"${DeploymentAutomationBranch}\" /opt/atlassian/dc-deployments-automation/\n" }, "owner": "root", "group": "root", "mode": "000750" }, "/etc/atl": { "owner": "root", "content": Join("\n", ["ATL_PRODUCT_FAMILY=jira", "ATL_DB_DRIVER=org.postgresql.Driver", "ATL_JDBC_DB_NAME=jira", "ATL_JDBC_USER=atljira", "ATL_APP_DATA_MOUNT_ENABLED=false", "ATL_ENABLED_PRODUCTS=Jira", "ATL_ENABLED_SHARED_HOMES=", "ATL_NGINX_ENABLED=false", "ATL_POSTGRES_ENABLED=false", "ATL_RELEASE_S3_BUCKET=atlassian-software", "ATL_RELEASE_S3_PATH=releases", "ATL_SSL_SELF_CERT_ENABLED=false", "", { "Fn::Sub": ["ATL_PRODUCT_EDITION=${Edition}", { "Edition": Ref(JiraProduct) }] }, { "Fn::Sub": ["ATL_PRODUCT_VERSION=${ProductVersion}", { "ProductVersion": Ref(JiraVersion) }] }, { "Fn::Sub": ["ATL_EFS_ID=${ElasticFileSystem}", { "ElasticFileSystem": Ref(ElasticFileSystem) }] }, If("SSLScheme", "ATL_SSL_PROXY=true", Ref("AWS::NoValue")), { "Fn::Sub": ["ATL_AWS_STACK_NAME=${StackName}", { "StackName": Ref("AWS::StackName") }] }, { "Fn::Sub": ["ATL_CATALINA_OPTS=\"${CatalinaOpts} ${MailOpts}\"", { "CatalinaOpts": Ref(CatalinaOpts), "MailOpts": If("DisableMail", "-Datlassian.mail.senddisabled=true -Datlassian.mail.fetchdisabled=true -Datlassian.mail.popdisabled=true", "") }] }, { "Fn::Sub": ["ATL_DB_HOST=${DBEndpointAddress}", { "DBEndpointAddress": GetAtt(DB, "Endpoint.Address") }] }, { "Fn::Sub": ["ATL_DB_MAXIDLE=${DBMaxIdle}", { "DBMaxIdle": Ref(DBMaxIdle) }] }, { "Fn::Sub": ["ATL_DB_MAXWAITMILLIS=${DBMaxWaitMillis}", { "DBMaxWaitMillis": Ref(DBMaxWaitMillis) }] }, { "Fn::Sub": ["ATL_DB_MINEVICTABLEIDLETIMEMILLIS=${DBMinEvictableIdleTimeMillis}", { "DBMinEvictableIdleTimeMillis": Ref(DBMinEvictableIdleTimeMillis) }] }, { "Fn::Sub": ["ATL_DB_MINIDLE=${DBMinIdle}", { "DBMinIdle": Ref(DBMinIdle) }] }, { "Fn::Sub": ["ATL_DB_ROOT_PASSWORD='${DBMasterUserPassword}'", { "DBMasterUserPassword": Ref(DBMasterUserPassword) }] }, { "Fn::Sub": ["ATL_DB_POOLMAXSIZE=${DBPoolMaxSize}", { "DBPoolMaxSize": Ref(DBPoolMaxSize) }] }, { "Fn::Sub": ["ATL_DB_POOLMINSIZE=${DBPoolMinSize}", { "DBPoolMinSize": Ref(DBPoolMinSize) }] }, { "Fn::Sub": ["ATL_DB_PORT=${DBEndpointPort}", { "DBEndpointPort": GetAtt(DB, "Endpoint.Port") }] }, { "Fn::Sub": ["ATL_DB_REMOVEABANDONED=${DBRemoveAbandoned}", { "DBRemoveAbandoned": Ref(DBRemoveAbandoned) }] }, { "Fn::Sub": ["ATL_DB_REMOVEABANDONEDTIMEOUT=${DBRemoveAbandonedTimeout}", { "DBRemoveAbandonedTimeout": Ref(DBRemoveAbandonedTimeout) }] }, { "Fn::Sub": ["ATL_DB_TESTONBORROW=${DBTestOnBorrow}", { "DBTestOnBorrow": Ref(DBTestOnBorrow) }] }, { "Fn::Sub": ["ATL_DB_TESTWHILEIDLE=${DBTestWhileIdle}", { "DBTestWhileIdle": Ref(DBTestWhileIdle) }] }, { "Fn::Sub": ["ATL_DB_TIMEBETWEENEVICTIONRUNSMILLIS=${DBTimeBetweenEvictionRunsMillis}", { "DBTimeBetweenEvictionRunsMillis": Ref(DBTimeBetweenEvictionRunsMillis) }] }, { "Fn::Sub": ["ATL_HOSTEDZONE=${HostedZone}", { "HostedZone": Ref(HostedZone) }] }, { "Fn::Sub": ["ATL_JDBC_PASSWORD='${DBPassword}'", { "DBPassword": Ref(DBPassword) }] }, { "Fn::Sub": ["ATL_JDBC_URL=jdbc:postgresql://${DBEndpointAddress}:${DBEndpointPort}/jira", { "DBEndpointPort": GetAtt(DB, "Endpoint.Port"), "DBEndpointAddress": GetAtt(DB, "Endpoint.Address") }] }, { "Fn::Sub": ["ATL_JIRA_FULL_DISPLAY_NAME=${JiraFullDisplayName}", { "JiraFullDisplayName": FindInMap("JIRAProduct2NameAndVersion", Ref(JiraProduct), "fulldisplayname") }] }, { "Fn::Sub": ["ATL_JIRA_NAME=${JiraProductName}", { "JiraProductName": FindInMap("JIRAProduct2NameAndVersion", Ref(JiraProduct), "name") }] }, { "Fn::Sub": ["ATL_JIRA_SHORT_DISPLAY_NAME=${JiraShortDisplayName}", { "JiraShortDisplayName": FindInMap("JIRAProduct2NameAndVersion", Ref(JiraProduct), "shortdisplayname") }] }, { "Fn::Sub": ["ATL_JVM_HEAP=${AtlJvmHeap}", { "AtlJvmHeap": If("OverrideHeap", Ref(JvmHeapOverride), FindInMap("AWSInstanceType2Arch", Ref(ClusterNodeInstanceType), "Jvmheap")) }] }, { "Fn::Sub": ["ATL_PROXY_NAME=${AtlProxyName}", { "AtlProxyName": If("UseCustomDnsName", Ref(CustomDnsName), If("UseHostedZone", Ref(LoadBalancerCname), GetAtt(LoadBalancer, "DNSName"))) }] }, { "Fn::Sub": ["ATL_TOMCAT_ACCEPTCOUNT=${TomcatAcceptCount}", { "TomcatAcceptCount": Ref(TomcatAcceptCount) }] }, { "Fn::Sub": ["ATL_TOMCAT_CONNECTIONTIMEOUT=${TomcatConnectionTimeout}", { "TomcatConnectionTimeout": Ref(TomcatConnectionTimeout) }] }, { "Fn::Sub": ["ATL_TOMCAT_CONTEXTPATH=${TomcatContextPath}", { "TomcatContextPath": Ref(TomcatContextPath) }] }, { "Fn::Sub": ["ATL_TOMCAT_DEFAULTCONNECTORPORT=${TomcatDefaultConnectorPort}", { "TomcatDefaultConnectorPort": Ref(TomcatDefaultConnectorPort) }] }, { "Fn::Sub": ["ATL_TOMCAT_ENABLELOOKUPS=${TomcatEnableLookups}", { "TomcatEnableLookups": Ref(TomcatEnableLookups) }] }, { "Fn::Sub": ["ATL_TOMCAT_MAXTHREADS=${TomcatMaxThreads}", { "TomcatMaxThreads": Ref(TomcatMaxThreads) }] }, { "Fn::Sub": ["ATL_TOMCAT_MINSPARETHREADS=${TomcatMinSpareThreads}", { "TomcatMinSpareThreads": Ref(TomcatMinSpareThreads) }] }, { "Fn::Sub": ["ATL_TOMCAT_PROTOCOL=${TomcatProtocol}", { "TomcatProtocol": Ref(TomcatProtocol) }] }, { "Fn::Sub": ["ATL_TOMCAT_PROXYPORT=${TomcatProxyPort}", { "TomcatProxyPort": If("SSLScheme", 443, 80) }] }, { "Fn::Sub": ["ATL_TOMCAT_REDIRECTPORT=${TomcatRedirectPort}", { "TomcatRedirectPort": Ref(TomcatRedirectPort) }] }, { "Fn::Sub": ["ATL_TOMCAT_SCHEME=${TomcatScheme}", { "TomcatScheme": If("SSLScheme", "https", "http") }] }, { "Fn::Sub": ["ATL_TOMCAT_SECURE=${TomcatSecure}", { "TomcatSecure": If("SSLScheme", True, False) }] }, { "Fn::Sub": ["ATL_DEPLOYMENT_REPOSITORY=${DeployRepository}", { "DeployRepository": Ref(DeploymentAutomationRepository) }] }, { "Fn::Sub": ["ATL_DEPLOYMENT_REPOSITORY_BRANCH=${DeployRepositoryBranch}", { "DeployRepositoryBranch": Ref(DeploymentAutomationBranch) }] }, { "Fn::Sub": ["ATL_DEPLOYMENT_REPOSITORY_PLAYBOOK=${DeployRepositoryPlaybook}", { "DeployRepositoryPlaybook": Ref(DeploymentAutomationPlaybook) }] }, { "Fn::Sub": ["ATL_DEPLOYMENT_REPOSITORY_KEYNAME=${DeployRepositoryKeyName}", { "DeployRepositoryKeyName": Ref(DeploymentAutomationKeyName) }] }]), "group": "root", "mode": "000640" } }, "commands": { "071_install_packages": { "ignoreErrors": True, "command": "yum install -y git python-virtualenv" }, "072_clone_atl_scripts": { "test": "test ! -d /opt/atlassian/dc-deployments-automation/", "ignoreErrors": True, "command": "/opt/atlassian/bin/clone_deployment_repo" }, "070_create_atl_dir": { "test": "test ! -d /opt/atlassian/", "ignoreErrors": False, "command": "mkdir -p /opt/atlassian" }, "080_run_atl_init_node": { "ignoreErrors": True, "command": { "Fn::Sub": "cd /opt/atlassian/dc-deployments-automation/ && ./bin/install-ansible && ./bin/ansible-with-atl-env inv/aws_node_local ${DeploymentAutomationPlaybook} /var/log/ansible-bootstrap.log\n" } } } } },
    ),
    UserData=Base64(Join("", ["#!/bin/bash -xe\n", "yum update -y aws-cfn-bootstrap\n", { "Fn::Sub": ["/opt/aws/bin/cfn-init -v --stack ${StackName}", { "StackName": Ref("AWS::StackName") }] }, { "Fn::Sub": [" --resource ClusterNodeLaunchConfig --region ${Region}\n", { "Region": Ref("AWS::Region") }] }, { "Fn::Sub": ["/opt/aws/bin/cfn-signal -e $? --stack ${StackName}", { "StackName": Ref("AWS::StackName") }] }, { "Fn::Sub": [" --resource ClusterNodeLaunchConfig --region ${Region}", { "Region": Ref("AWS::Region") }] }])),
    ImageId=FindInMap("AWSRegionArch2AMI", Ref("AWS::Region"), FindInMap("AWSInstanceType2Arch", Ref(ClusterNodeInstanceType), "Arch")),
    BlockDeviceMappings=[{ "DeviceName": "/dev/xvda", "Ebs": { "VolumeSize": Ref(ClusterNodeVolumeSize) } }, { "DeviceName": "/dev/xvdf", "NoDevice": True, "Ebs": {  } }],
    KeyName=If("KeyProvided", Ref(KeyPairName), { "Fn::ImportValue": "ATL-DefaultKey" }),
    SecurityGroups=[Ref(SecurityGroup)],
    IamInstanceProfile=Ref(JiraClusterNodeInstanceProfile),
    InstanceType=Ref(ClusterNodeInstanceType),
    AssociatePublicIpAddress=False,
    DependsOn=["EFSMountAz1", "EFSMountAz2", "DB"],
))

DBEncryptionKey = t.add_output(Output(
    "DBEncryptionKey",
    Value=Ref(EncryptionKeyAlias),
    Description="The alias of the encryption key created for RDS",
    Condition="UseDatabaseEncryption",
))

EFSCname = t.add_output(Output(
    "EFSCname",
    Export={ "Name": Join("", [Ref("AWS::StackName"), "-EFSCname"]) },
    Description="The cname of the EFS",
    Value=If("UseHostedZone", Ref(EFSCname), Ref(ElasticFileSystem)),
))

SGname = t.add_output(Output(
    "SGname",
    Export={ "Name": Join("", [Ref("AWS::StackName"), "-SGname"]) },
    Description="The name of the SecurityGroup",
    Value=Ref(SecurityGroup),
))

DBEndpointAddress = t.add_output(Output(
    "DBEndpointAddress",
    Description="The Database Connection String",
    Value=GetAtt(DB, "Endpoint.Address"),
))

LoadBalancerURL = t.add_output(Output(
    "LoadBalancerURL",
    Description="The Load Balancer URL",
    Value={ "Fn::Sub": ["${HTTP}://${LoadBalancerDNSName}", { "HTTP": If("SSLScheme", "https", "http"), "LoadBalancerDNSName": GetAtt(LoadBalancer, "DNSName") }] },
))

ServiceURL = t.add_output(Output(
    "ServiceURL",
    Description="The URL to access this Atlassian service",
    Value=If("UseCustomDnsName", { "Fn::Sub": ["${HTTP}://${CustomDNSName}${ContextPath}", { "CustomDNSName": Ref(CustomDnsName), "HTTP": If("SSLScheme", "https", "http"), "ContextPath": Ref(TomcatContextPath) }] }, If("UseHostedZone", { "Fn::Sub": ["${HTTP}://${LBCName}${ContextPath}", { "ContextPath": Ref(TomcatContextPath), "HTTP": If("SSLScheme", "https", "http"), "LBCName": Ref(LoadBalancerCname) }] }, { "Fn::Sub": ["${HTTP}://${LoadBalancerDNSName}${ContextPath}", { "HTTP": If("SSLScheme", "https", "http"), "LoadBalancerDNSName": GetAtt(LoadBalancer, "DNSName"), "ContextPath": Ref(TomcatContextPath) }] })),
))

print(t.to_json())
