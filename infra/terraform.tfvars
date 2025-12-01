vpc_cidr = "10.0.0.0/16"

public_subnet_cidrs = [
  "10.0.1.0/24",
  "10.0.2.0/24"
]

private_subnet_cidrs = [
  "10.0.3.0/24",
  "10.0.4.0/24"
]

availability_zones = [
  "us-west-2a",
  "us-west-2b"
]


name_prefix = "eksdemo"
cluster_name = "eksdemo-cluster"
region = "us-west-2"
repo_name = "eksdemo"

# RDS config
DB_NAME="mydb"
DB_USER="db_user"
DB_HOST = ""
DB_PASS=""
secret_name = "rds-creds"


