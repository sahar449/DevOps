#######################################
# Random String Generator for unique names
#######################################
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

#######################################
# EKS Cluster IAM Role
#######################################
resource "aws_iam_role" "eks_cluster_role" {
  name = "${var.cluster_name}-eks-cluster-role-${random_string.suffix.result}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_AmazonEKSClusterPolicy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

#######################################
# EKS Cluster
#######################################
resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.33"

  vpc_config {
    subnet_ids = var.private_subnet_ids
  }

  lifecycle {
    ignore_changes = [name]
  }
}

#######################################
# Worker Node IAM Role
#######################################
resource "aws_iam_role" "node_group_role" {
  name = "${var.cluster_name}-eks-nodegroup-role-${random_string.suffix.result}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_node_AmazonEKSWorkerNodePolicy" {
  role       = aws_iam_role.node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "worker_node_AmazonEC2ContainerRegistryReadOnly" {
  role       = aws_iam_role.node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "worker_node_AmazonEKS_CNI_Policy" {
  role       = aws_iam_role.node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

#######################################
# EKS Node Group
#######################################
resource "aws_eks_node_group" "private_nodes" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-ng-${random_string.suffix.result}"
  node_role_arn   = aws_iam_role.node_group_role.arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = 2
    max_size     = 4
    min_size     = 2
  }

  instance_types = ["t3.medium"]
}

#######################################
# OIDC Provider for IRSA
#######################################
data "tls_certificate" "eks" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

#######################################
# Fluent Bit IAM Role + Policy + SA + Addon
#######################################
resource "aws_iam_policy" "fluent_bit_policy" {
  name        = "FluentBitCloudWatchPolicy"
  description = "IAM policy for Fluent Bit to write logs to CloudWatch"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "fluent_bit_role" {
  name = "eks-fluent-bit-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = "sts:AssumeRoleWithWebIdentity",
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      },
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url,"https://","")}:sub" = "system:serviceaccount:amazon-cloudwatch:fluent-bit"
          "${replace(aws_iam_openid_connect_provider.eks.url,"https://","")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "fluent_bit_attach" {
  role       = aws_iam_role.fluent_bit_role.name
  policy_arn = aws_iam_policy.fluent_bit_policy.arn
}

resource "kubernetes_service_account" "fluent_bit" {
  metadata {
    name      = "fluent-bit"
    namespace = "amazon-cloudwatch"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.fluent_bit_role.arn
    }
  }
  depends_on = [aws_eks_cluster.this]
}

resource "aws_eks_addon" "fluent_bit" {
  cluster_name = aws_eks_cluster.this.name
  addon_name   = "fluent-bit"
  addon_version = "v4.2.0-eksbuild.1"
  service_account_role_arn = aws_iam_role.fluent_bit_role.arn
  depends_on = [aws_eks_cluster.this]
}
#######################################
# CloudWatch Agent IAM Role + Policy + SA + Addon
#######################################
resource "aws_iam_policy" "cloudwatch_agent_policy" {
  name        = "CloudWatchAgentPolicy"
  description = "IAM policy for CloudWatch Agent to publish metrics and logs"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "cloudwatch:PutMetricData",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags",
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "cloudwatch_agent_role" {
  name = "eks-cloudwatch-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = "sts:AssumeRoleWithWebIdentity",
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      },
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url,"https://","")}:sub" = "system:serviceaccount:amazon-cloudwatch:cloudwatch-agent"
          "${replace(aws_iam_openid_connect_provider.eks.url,"https://","")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent_attach" {
  role       = aws_iam_role.cloudwatch_agent_role.name
  policy_arn = aws_iam_policy.cloudwatch_agent_policy.arn
}

resource "kubernetes_service_account" "cloudwatch_agent" {
  metadata {
    name      = "cloudwatch-agent"
    namespace = "amazon-cloudwatch"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.cloudwatch_agent_role.arn
    }
  }
  depends_on = [aws_eks_cluster.this]
}

resource "aws_eks_addon" "cloudwatch_agent" {
  cluster_name = aws_eks_cluster.this.name
  addon_name   = "amazon-cloudwatch-observability"
  addon_version = "v4.7.0-eksbuild.1"
  service_account_role_arn = aws_iam_role.cloudwatch_agent_role.arn
  depends_on = [aws_eks_cluster.this]
}