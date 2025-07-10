# Common Errors and Solutions

This document tracks common errors encountered during development, grouped by category for quick reference.

---

## 1. Azure Authentication & Permissions

**Description**: Issues authenticating with Azure services or lacking required permissions.

**Common Errors**:
- **DefaultAzureCredential failed to retrieve a token**
  - *Cause*: Not logged in, wrong subscription.
  - *Fix*: `az login`, `az account set --subscription <id>`
- **AuthorizationFailed - This request is not authorized**
  - *Cause*: Missing RBAC roles.
  - *Fix*: Check role assignments, re-apply Terraform.

**Prevention**: Always verify authentication and RBAC before running the app.

---

## 2. Environment & Configuration

**Description**: Problems due to missing or incorrect environment variables.

**Common Errors**:
- **Missing required environment variables**
  - *Symptoms*: App fails accessing Azure resources.
  - *Fix*: Update `.env` with Terraform outputs.

**Prevention**: Validate environment at startup.

---

## 3. Dependency & Package Management

**Description**: Python package import errors or missing dependencies.

**Common Errors**:
- **Import could not be resolved**
  - *Cause*: Dependencies not installed or venv not activated.
  - *Fix*: `uv sync`, use `uv run`.

**Prevention**: Always sync and activate environment.

---

## 4. Terraform & Azure Resource Management

**Description**: Issues with resource creation, state, or configuration.

**Common Errors**:
- **Resource already exists**
  - *Fix*: Import resource or destroy/recreate.
- **RBAC not applied**
  - *Fix*: Check `terraform plan`, re-apply if needed.

**Prevention**: Use consistent naming and manage state carefully.

---

## 5. File Upload & Blob Storage

**Description**: File uploads not appearing in Azure Storage.

**Common Errors**:
- **File upload fails silently**
  - *Causes*: Input mishandling, permissions, file size.
  - *Fix*: Check input handling, permissions, add logging.

**Prevention**: Add logging and error handling for uploads.

---

## 6. Containerization & Docker

**Description**: Docker build or run failures.

**Common Errors**:
- **Container build fails**
  - *Causes*: Missing lock file, platform issues, network.
  - *Fix*: Ensure `uv.lock` exists, check connectivity.

**Prevention**: Commit lock files, test builds locally.

---

## 7. Service Bus Messaging

**Description**: Issues sending or receiving Service Bus messages.

**Common Errors**:
- **Message publishing fails**
  - *Causes*: Permissions, missing topic, bad format.
  - *Fix*: Verify topic, permissions, message format.

**Prevention**: Health checks for Service Bus.

---

## 8. Development Environment

**Description**: Local development issues.

**Common Errors**:
- **Port already in use**
  - *Fix*: Kill process or use different port.

**Prevention**: Check port before starting app.

---

## 9. FastHTML Framework Usage

**Description**: Type errors in route parameters.

**Common Errors**:
- **Type List cannot be instantiated**
  - *Cause*: Using `typing.List` instead of `list`.
  - *Fix*: Use built-in `list` or manual form parsing.

**Example**:
```python
# Wrong
async def post(attachments: Optional[List] = None):
# Correct
async def post(attachments: Optional[list] = None):
```

**Prevention**: Use built-in types for FastHTML routes.

---

## 10. Cosmos DB Issues

**Description**: Document creation/read errors due to misconfigured keys, invalid IDs, or SDK usage.

**Common Errors**:
- **Entity with specified id already exists (409)**
  - *Cause*: Unique key constraint mismatch.
  - *Fix*: Match unique key paths to schema.
- **Entity with specified id does not exist (404)**
  - *Cause*: Wrong partition key used in read.
  - *Fix*: Use correct partition key from container config.
- **Invalid characters in document ID**
  - *Cause*: Using URLs/strings with `/` as IDs.
  - *Fix*: Use UUIDs or URL-encode.
- **Unexpected keyword argument 'partition_key'**
  - *Cause*: Passing partition_key in async SDK.
  - *Fix*: Remove explicit partition_key, let SDK extract from body.

**Examples**:
```python
# Partition key mismatch
container.read_item(item=id, partition_key=wrong_value)  # Wrong
container.read_item(item=id, partition_key=correct_value)  # Correct

# Invalid ID
doc_id = str(uuid.uuid4())  # Good
doc_id = urllib.parse.quote(url, safe='')  # If needed

# Async SDK
await container.create_item(body=data)  # Correct
```

**Prevention**: Sync schema, Terraform, and code; never use raw URLs as IDs; check SDK docs.

---

## 11. Document Intelligence API

**Description**: File format or output issues with Document Intelligence.

**Common Errors**:
- **Invalid request - file format unsupported**
  - *Cause*: Unsupported file type (e.g., `.txt`).
  - *Fix*: Check extension before processing.
- **Markdown output contains HTML tags**
  - *Note*: This is expected for complex structures.

**Example**:
```python
def _is_supported_document_format(url): ...
```

**Reference**: [Document Intelligence Markdown Elements](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/markdown-elements?view=doc-intel-4.0.0)

---

## 12. Architecture & Event Design

**Description**: Data duplication due to missing context in events.

**Common Errors**:
- **Duplicate records instead of updates**
  - *Cause*: Event missing document ID.
  - *Fix*: Include documentId in events for direct updates.

**Example**:
```python
class DocumentUploadedEventData(BaseModel):
    documentUrl: str
    documentId: str  # Needed for updates
```

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
