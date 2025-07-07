# Common Errors and Solutions

## Email Processing System - Client Web Application

This document tracks common errors encountered during development and their solutions.

---

## Azure Authentication Issues

### Error: DefaultAzureCredential failed to retrieve a token
**Description**: Application fails to authenticate with Azure services during local development.

**Symptoms**:
```
azure.core.exceptions.ClientAuthenticationError: DefaultAzureCredential failed to retrieve a token from the included credentials.
```

**Root Cause**: User not authenticated with Azure CLI or using wrong subscription.

**Solution**:
1. Run `az login` to authenticate
2. Verify subscription: `az account show`
3. Set correct subscription: `az account set --subscription <subscription-id>`

**Prevention**: Include authentication check in application startup

---

## Environment Configuration

### Error: Missing required environment variables
**Description**: Application starts but fails when trying to access Azure services.

**Symptoms**:
```
ValueError: Missing required environment variables: AZURE_STORAGE_ACCOUNT_NAME, AZURE_SERVICE_BUS_FQDN
```

**Root Cause**: `.env` file not configured with Azure resource names.

**Solution**:
1. Manually update `.env` file with values from Terraform outputs
2. Verify Terraform outputs: `terraform output -json`
3. Verify `.env` file has correct values

**Prevention**: Include environment validation in application startup

---

## Permission Issues

### Error: AuthorizationFailed - This request is not authorized
**Description**: Azure services reject requests due to insufficient permissions.

**Symptoms**:
```
azure.core.exceptions.HttpResponseError: (AuthorizationFailed) This request is not authorized to perform this operation.
```

**Root Cause**: RBAC role assignments not applied or user lacks permissions.

**Solution**:
1. Verify Terraform applied RBAC: `terraform plan` should show no changes
2. Check role assignments: `az role assignment list --assignee $(az account show --query user.name -o tsv)`
3. Re-apply Terraform: `terraform apply`

**Prevention**: Include RBAC verification in infrastructure deployment

---

## Dependency and Package Issues

### Error: Import could not be resolved
**Description**: Python imports fail for Azure or FastHTML packages.

**Symptoms**:
```
Import "fasthtml.common" could not be resolved
Import "azure.storage.blob" could not be resolved
```

**Root Cause**: Dependencies not installed or virtual environment not activated.

**Solution**:
1. Install dependencies: `uv sync`
2. Verify installation: `uv pip list`
3. Use `uv run` to ensure correct environment: `uv run python main.py`

---

## Terraform Issues

### Error: Resource already exists
**Description**: Terraform fails because resources already exist in Azure.

**Symptoms**:
```
Error: A resource with the ID already exists
```

**Root Cause**: Previous deployment not properly cleaned up or state file issues.

**Solution**:
1. Import existing resource: `terraform import <resource_type>.<name> <azure_resource_id>`
2. Or destroy and recreate: `terraform destroy` then `terraform apply`
3. Check state file: `terraform state list`

**Prevention**: Use consistent resource naming and proper state management

---

## File Upload Issues

### Error: File upload fails silently
**Description**: Form submission works but files don't appear in blob storage.

**Symptoms**: Success message shown but no blobs created in Azure Storage.

**Root Cause**: 
- File input not properly handled in FastHTML
- Blob storage permissions
- File size limitations

**Solution**:
1. Check file input handling in `main.py`
2. Verify blob storage permissions
3. Check file size limits in Azure Storage
4. Add logging to track upload process

**Prevention**: Add comprehensive logging and error handling for file operations

---

## Container and Docker Issues

### Error: Container build fails
**Description**: Docker build process fails when creating container image.

**Symptoms**:
```
ERROR: failed to solve: process "/bin/sh -c uv sync --frozen" did not complete successfully
```

**Root Cause**: 
- Missing `uv.lock` file
- Platform-specific dependencies
- Network issues during build

**Solution**:
1. Ensure `uv.lock` exists: `uv lock`
2. Use multi-stage build for platform compatibility
3. Check network connectivity during build

**Prevention**: Include lock file in version control and test builds locally

---

## Service Bus Message Issues

### Error: Message publishing fails
**Description**: Blob storage works but Service Bus messages not sent.

**Symptoms**: Containers created but no messages in Service Bus topic.

**Root Cause**:
- Service Bus permissions
- Topic doesn't exist
- Message format issues

**Solution**:
1. Verify topic exists: `az servicebus topic show --name new-submissions --namespace-name <namespace>`
2. Check Service Bus permissions in Azure Portal
3. Validate message JSON format
4. Add error handling for Service Bus operations

**Prevention**: Include Service Bus verification in health checks

---

## Development Environment Issues

### Error: Port already in use
**Description**: Application fails to start because port 8000 is occupied.

**Symptoms**:
```
OSError: [Errno 48] Address already in use
```

**Root Cause**: Another process using port 8000 or previous application instance still running.

**Solution**:
1. Kill existing process: `netstat -ano | findstr :8000` then `taskkill /F /PID <pid>`
2. Use different port: Set `PORT=8001` in `.env`
3. Check for background processes

**Prevention**: Check port availability before starting application

---

## FastHTML Framework Issues

### Error: Type List cannot be instantiated
**Description**: FastHTML application crashes with type instantiation error during form submission with file uploads.

**Symptoms**:
```
TypeError: Type List cannot be instantiated; use list() instead
```

**Root Cause**: Using `typing.List` instead of built-in `list` in route function parameters. FastHTML's request parameter injection tries to instantiate the type annotation directly.

**Solution**:
```python
# ❌ Wrong - causes instantiation error
@rt("/submit", methods=["POST"])
async def post(email: str, message: str, attachments: Optional[List] = None):

# ✅ Correct - use built-in list type
@rt("/submit", methods=["POST"])  
async def post(email: str, message: str, attachments: Optional[list] = None):

# ✅ Better - use manual form parsing for complex uploads
@rt("/submit", methods=["POST"])
async def post(request):
    form = await request.form()
    attachments = form.getlist("attachments")
```

**Prevention**: 
- Use built-in types (`list`, `dict`) instead of `typing` module types for FastHTML routes
- For complex file uploads, use manual form parsing with `request.form()`

---

## Cosmos DB Configuration Issues

### Error: Entity with the specified id already exists in the system
**Description**: Cosmos DB returns conflict error (409) when creating documents, even though document IDs are unique UUIDs.

**Symptoms**:
```
azure.core.exceptions.HttpResponseError: (Conflict) Entity with the specified id already exists in the system.
RequestStartTime: 2025-07-07T15:19:16.3732535Z, RequestEndTime: 2025-07-07T15:19:16.3747973Z, Number of regions attempted:1
Code: Conflict
Message: Entity with the specified id already exists in the system.
```

**Root Cause**: Misconfigured unique key constraints in Terraform Cosmos DB container configuration. The container had a unique key constraint on a field that doesn't exist in the document schema.

**Example Problem**:
```terraform
resource "azurerm_cosmosdb_sql_container" "events" {
  name                = "events"
  partition_key_paths = ["/submissionId"]
  
  # ❌ Wrong - field doesn't exist in documents
  unique_key {
    paths = ["/eventId"]  # This field doesn't exist!
  }
}
```

**Solution**:
1. Review Cosmos DB container configuration in Terraform
2. Verify unique key constraints match actual document schema
3. Remove invalid unique key constraints
4. Apply Terraform changes: `terraform plan` and `terraform apply`

**Correct Configuration**:
```terraform
resource "azurerm_cosmosdb_sql_container" "events" {
  name                = "events"
  partition_key_paths = ["/submissionId"]
  
  # No unique key constraints needed for events container
  # Documents use random UUIDs as IDs which are inherently unique
}
```

**Prevention**: 
- Always verify unique key paths exist in document schema before configuring
- Test container configuration with sample documents
- Use descriptive field names that match the actual data model
- Review Design.md schema when configuring Cosmos DB containers

**Key Insight**: Cosmos DB conflict errors can be caused by infrastructure configuration issues, not just application code. Always check Terraform configuration when debugging "entity already exists" errors, especially unique key constraints and partition key configuration.

---

## Troubleshooting Checklist

When encountering issues, check in this order:

### 1. Authentication
- [ ] `az login` completed successfully
- [ ] Correct Azure subscription selected
- [ ] User has appropriate permissions

### 2. Environment Configuration
- [ ] `.env` file exists and populated
- [ ] Required environment variables set
- [ ] Terraform outputs match `.env` values

### 3. Dependencies
- [ ] `uv sync` completed successfully
- [ ] Virtual environment activated
- [ ] All required packages installed

### 4. Azure Resources
- [ ] Storage account exists and accessible
- [ ] Service Bus namespace and topic exist
- [ ] RBAC role assignments applied

### 5. Application
- [ ] Port 8000 available
- [ ] No syntax errors in code
- [ ] Proper error handling in place

---

## Debug Commands

### Azure Resource Verification
```powershell
# Check storage account
az storage account show --name <storage-account-name> --resource-group <rg-name>

# Check service bus
az servicebus namespace show --name <namespace-name> --resource-group <rg-name>

# Check role assignments
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

### Application Debug
```powershell
# Check dependencies
uv pip list

# Test Azure connection
uv run python -c "from azure.identity import DefaultAzureCredential; DefaultAzureCredential().get_token('https://storage.azure.com/.default')"

# Check environment
uv run python -c "import os; print(os.getenv('AZURE_STORAGE_ACCOUNT_NAME'))"
```

### Network and Process Debug
```powershell
# Check port usage
netstat -ano | findstr :8000

# Check running Python processes
tasklist | findstr python
```
