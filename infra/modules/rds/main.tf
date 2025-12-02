# ----------------------------
# Random Password Generation
# ----------------------------
resource "random_password" "db_password" {
  length  = 16
  special = true
  override_special = "!#$%&*()-_=+[]{}"
  min_lower   = 1
  min_upper   = 1
  min_numeric = 1
  min_special = 1
}

# ----------------------------
# RDS Subnet Group
# ----------------------------
resource "aws_db_subnet_group" "rds_subnet_group" {
  name        = "rds-subnet-group"
  description = "Subnet group for RDS"
  subnet_ids  = var.private_subnets

  tags = {
    Name = "rds-subnet-group"
  }
}

# ----------------------------
# RDS Security Group
# ----------------------------
resource "aws_security_group" "rds_sg" {
  name        = "rds-sg"
  description = "Security Group for RDS MySQL"
  vpc_id      = var.vpc_id
  tags = {
    Name = "rds-sg"
  }
}

resource "aws_security_group_rule" "allow_vpc_to_rds" {
  type              = "ingress"
  from_port         = 3306
  to_port           = 3306
  protocol          = "tcp"
  description       = "Allow MySQL from VPC (EKS Pods + Nodes)"
  security_group_id = aws_security_group.rds_sg.id
  cidr_blocks       = [var.cidr_blocks]
}

# ----------------------------
# Secrets Manager Secret
# ----------------------------
resource "aws_secretsmanager_secret" "rds_credentials" {
  name        = var.secret_name
  description = "RDS MySQL credentials"
  recovery_window_in_days    = 0  # Immediate deletion
  tags = {
    Name = "rds-credentials"
  }
}

# Initial secret version (without host)
resource "aws_secretsmanager_secret_version" "rds_credentials_version" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id

  secret_string = jsonencode({
    username = var.DB_USER
    password = random_password.db_password.result  # ✅ Auto-generated password
    dbname   = var.DB_NAME
    engine   = "mysql"
  })
}

# ----------------------------
# RDS MySQL Instance
# ----------------------------
resource "aws_db_instance" "mysql" {
  identifier           = "mydb"
  engine               = "mysql"
  engine_version       = "8.0.39"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  
  db_name  = var.DB_NAME
  username = var.DB_USER
  password = random_password.db_password.result  # ✅ Auto-generated password
  
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  
  backup_retention_period         = 7
  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]
  
  skip_final_snapshot = true
  publicly_accessible = false
  
  tags = {
    Name = "mydb"
  }
}

# ----------------------------
# Update Secret with RDS Endpoint
# ----------------------------
resource "aws_secretsmanager_secret_version" "rds_credentials_final" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id

  secret_string = jsonencode({
    username = var.DB_USER
    password = random_password.db_password.result  # ✅ Same password
    host     = aws_db_instance.mysql.address
    dbname   = var.DB_NAME
    port     = 3306
    engine   = "mysql"
  })

  depends_on = [aws_db_instance.mysql]
}

# ----------------------------
# Data Source for Reading Secret
# ----------------------------
data "aws_secretsmanager_secret_version" "rds_credentials" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id

  depends_on = [aws_secretsmanager_secret_version.rds_credentials_final]
}