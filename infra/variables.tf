variable "vpc_cidr" {}
variable "public_subnet_cidrs" { type = list(string) }
variable "private_subnet_cidrs" { type = list(string) }
variable "availability_zones" { type = list(string) }
variable "name_prefix" {}
variable "cluster_name" {}
variable "region" {}
variable "repo_name" {}
variable "DB_NAME" {}
variable "DB_USER" {}
variable "DB_HOST" {}
variable "secret_name" {}
variable "DB_PASS" {}