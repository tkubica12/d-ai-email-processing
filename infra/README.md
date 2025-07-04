# Infrastructure

This directory contains the Terraform infrastructure code for the Email Processing System.

## Resources Created

- **Resource Group**: Contains all resources for the project
- **Storage Account**: Stores email content and attachments in blob containers
- **Service Bus Namespace & Topic**: Handles event messaging for email processing
- **App Service Plan**: Hosts the Logic App with Workflow Standard tier
- **Logic App Standard**: Processes incoming emails and orchestrates the workflow
- **Managed Identity & Role Assignments**: Provides secure access between services

## Deployment

### Prerequisites

1. Azure CLI installed and authenticated
2. Terraform installed (version >= 1.0)
3. Azure Developer CLI (azd) installed

### Using Azure Developer CLI (Recommended)

The infrastructure is deployed automatically when using `azd up`:

```bash
azd up
```

### Manual Terraform Deployment

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your desired values

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Plan the deployment:
   ```bash
   terraform plan
   ```

5. Apply the infrastructure:
   ```bash
   terraform apply
   ```

## Configuration

### Variables

- `environment_name`: Environment identifier (dev, staging, prod)
- `location`: Azure region for resource deployment
- `project_name`: Project name used for resource naming
- `email_mailbox`: Email address to monitor for incoming emails

### Outputs

The infrastructure outputs important resource information that can be used by the Logic App and other components:

- Storage account connection string
- Service Bus connection string and topic name
- Logic App URL and managed identity details

## Security

- Managed Identity is used for secure authentication between services
- Role assignments follow principle of least privilege
- Connection strings are marked as sensitive outputs
- Storage account includes versioning and soft delete for data protection
