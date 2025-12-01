### variables rds ###
variable "DB_NAME" {}
variable "DB_USER" {}
variable "vpc_id" {}
variable "secret_name" {}
variable "DB_HOST" {}
variable "cidr_blocks" {}
variable "private_subnets" {
  type = list(string)
}
