# 🚀 DevOps: AWS EKS with Terraform & ArgoCD

Complete DevOps infrastructure: Terraform for AWS provisioning, ArgoCD for GitOps, and GitHub Actions for CI/CD automation.

## 📐 Architecture

![AWS EKS Infrastructure](picture.png)

## 🧾 Project Structure

```
.
├── ArgoCD/                     # ArgoCD configurations and Helm charts
│   ├── externalCharts/         # External resources (ALB, Secrets)
│   │   ├── alb_dns.yaml
│   │   └── secrets.yaml
│   └── myChart/                # Custom Helm chart with ArgoCD config
│       ├── argo.yaml
│       └── helm_chart/
│           ├── Chart.yaml
│           ├── templates/
│           │   ├── deployment.yaml
│           │   ├── ingress.yaml
│           │   ├── secret-provider-class.yaml
│           │   ├── serviceaccount.yaml
│           │   └── service.yaml
│           └── values.yaml
├── infra/                      # Terraform infrastructure as code
│   ├── main.tf
│   ├── providers.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   └── modules/
│       ├── ecr/                # Elastic Container Registry
│       │   ├── main.tf
│       │   ├── outputs.tf
│       │   └── variables.tf
│       ├── eks/                # Elastic Kubernetes Service
│       │   ├── main.tf
│       │   ├── outputs.tf
│       │   └── variables.tf
│       ├── iam/                # IAM roles and policies
│       │   ├── main.tf
│       │   ├── outputs.tf
│       │   └── variables.tf
│       ├── rds/                # Relational Database Service
│       │   ├── main.tf
│       │   ├── outputs.tf
│       │   └── variables.tf
│       ├── ssl/                # SSL/TLS certificates
│       │   ├── main.tf
│       │   └── outputs.tf
│       └── vpc/                # Virtual Private Cloud
│           ├── main.tf
│           ├── outputs.tf
│           └── variabels.tf
├── src/                        # Application source code
│   ├── app.py                  # Flask application
│   ├── Dockerfile              # Container image definition
│   └── requirements.txt        # Python dependencies
├── picture.png                 # Architecture diagram
└── README.md
```

## 🛠 Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/sahar449/DevOps.git
cd DevOps
```

**GitHub Secrets Required:**
- `AWS_ACCOUNT_ID`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` **OR** use OpenID Connect (OIDC) for secure authentication without long-term credentials

### 2. Deploy Infrastructure
```bash
cd infra
terraform init
terraform apply -auto-approve

# Configure kubectl
aws eks update-kubeconfig --name my-eks-cluster --region us-west-2
```

### 3. CI/CD Pipeline with Tests

The GitHub Actions workflow automatically runs:

**Security & Quality Checks:**
```yaml
# Trivy security scan
- Filesystem vulnerability scanning
- Configuration misconfigurations
- Secret detection

# Terraform validation
- terraform fmt -check
- terraform validate
- terraform plan
```

**Build & Push:**
```yaml
# Docker build and push to ECR
- Build container image
- Tag with commit SHA
- Push to Amazon ECR
```

**Testing:**
```yaml
# Application tests
- Unit tests
- Integration tests
- Container image tests
```

### 4. Install ArgoCD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 5. Deploy Application
```bash
# Apply ArgoCD application
kubectl apply -f ArgoCD/myChart/argo.yaml

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open: https://localhost:8080
```

## 🔐 Security Features

- **Trivy** - Container & IaC vulnerability scanning
- **IAM** - Least privilege roles with IRSA
- **VPC** - Private subnets for EKS nodes
- **SSL/TLS** - ACM certificates
- **Secrets** - AWS Secrets Manager integration

## 📊 Infrastructure Modules

| Module | Purpose |
|--------|---------|
| **VPC** | Network with public/private subnets |
| **EKS** | Managed Kubernetes cluster |
| **ECR** | Container registry |
| **RDS** | Managed database |
| **IAM** | Roles and policies |
| **SSL** | ACM certificates |

## 🔄 CI/CD Pipeline

1. **Code Push** → GitHub Actions triggered
2. **Trivy Scan** → Security vulnerability check
3. **Docker Build** → Push to ECR
4. **ArgoCD Sync** → Automated deployment to EKS

## 🧪 Testing

```bash
# Check deployment
kubectl get pods
kubectl get svc
kubectl get ingress

# View logs
kubectl logs -f <pod-name>

# Port forward
kubectl port-forward service/myapp-service 8080:80
curl http://localhost:8080
```

## 🧹 Cleanup

```bash
# Delete application
kubectl delete -f ArgoCD/myChart/argo.yaml

# Destroy infrastructure
cd infra
terraform destroy -auto-approve
```

## 📈 Features

✅ Infrastructure as Code (Terraform)  
✅ GitOps with ArgoCD  
✅ CI/CD with GitHub Actions  
✅ Security scanning with Trivy  
✅ Multi-AZ EKS cluster  
✅ RDS database  
✅ SSL/TLS encryption  
✅ Secrets management  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 📧 Contact

**Sahar** - [@sahar449](https://github.com/sahar449)

Project Link: [https://github.com/sahar449/DevOps](https://github.com/sahar449/DevOps)

---

⭐ **Star this repo if it helped you!**