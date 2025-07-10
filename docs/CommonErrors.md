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

## Cosmos DB Document ID Issues

### Error: Invalid characters in document ID
**Description**: Cosmos DB rejects document creation with error about invalid characters in the document ID, even when the ID appears to be a valid string.

**Symptoms**:
```
azure.core.exceptions.HttpResponseError: (BadRequest) Invalid characters in document id
```

**Root Cause**: Forward slashes (`/`) and other special characters are illegal in Cosmos DB document IDs. Using URLs directly as document IDs will fail because URLs contain forward slashes.

**Solution**:
```python
import uuid

# ❌ Wrong - URL contains illegal forward slashes
doc_id = "https://storage.blob.core.windows.net/submission-guid/document1.pdf"

# ✅ Correct - Use generated GUID as document ID
doc_id = str(uuid.uuid4())

# Store documentUrl as separate field for queries
doc_record = DocumentRecord(
    id=doc_id,
    documentUrl=document_url,  # Original URL for partition key and queries
    # ...other fields
)

# Alternative: URL encode if you need the URL as the ID
doc_id = urllib.parse.quote(document_url, safe='')
```

**Prevention**: 
- Use generated GUIDs for Cosmos DB document IDs when the original string contains special characters
- Store the original string (URL, path, etc.) as a separate field for queries
- If you must use the original string as ID, URL encode it with `urllib.parse.quote(string, safe='')`

**Key Insight**: Cosmos DB document IDs have strict character restrictions. URLs, file paths, and other strings with special characters must be encoded before use as document IDs.

---

## Document Intelligence Markdown Output Format

### Issue: Output looks like HTML instead of pure markdown

**Problem**: When using Document Intelligence with `output_content_format=DocumentContentFormat.MARKDOWN`, the output contains HTML-like elements such as `<table>`, `<tr>`, `<th>`, `<td>`, and `<figure>` tags.

**Root Cause**: This is the **correct and expected behavior**. Document Intelligence intentionally uses HTML table syntax and figure tags within its markdown output to preserve complex document structures that standard markdown cannot handle.

**Solution**: No fix needed. According to Microsoft documentation:
- **Tables**: Uses full HTML table markup (`<table>`, `<tr>`, `<th>`, `<td>`) rather than standard Markdown tables for maximum fidelity
- **Figures**: Uses `<figure>` tags to maintain semantic distinction from surrounding text  
- **Complex structures**: HTML elements preserve merged cells, table captions, and other complex formatting

**Reference**: [Document Intelligence Markdown Elements Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/markdown-elements?view=doc-intel-4.0.0)

**Example Output** (correct format):
```markdown
<figure>
PUMA Europe
</figure>

<table>
<tr>
<th>Header</th>
<th>Value</th>
</tr>
<tr>
<td>Date</td>
<td>05 Jul 2025</td>
</tr>
</table>
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

---

## Azure Document Intelligence API Issues

### Error: Invalid request - file format unsupported

**Problem**: Document Intelligence returns HTTP 400 error with message "The file is corrupted or format is unsupported" when processing certain file types like `.txt` files.

**Root Cause**: Document Intelligence only supports specific file formats (PDF, images, Office documents, HTML) and cannot process plain text files.

**Solution**: Implement format detection and handle unsupported formats separately:
```python
def _is_supported_document_format(self, document_url: str) -> bool:
    """Check if document format is supported by Document Intelligence."""
    supported_extensions = {
        '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', 
        '.heif', '.docx', '.xlsx', '.pptx', '.html'
    }
    
    file_path = urlparse(document_url).path.lower()
    return any(file_path.endswith(ext) for ext in supported_extensions)

# Process supported formats with Document Intelligence
if self._is_supported_document_format(document_url):
    markdown_content = await self._process_document_with_intelligence(document_content)
else:
    # Handle text files directly
    markdown_content = document_content.decode('utf-8')
```

**Prevention**: Always validate file formats before sending to Document Intelligence. Handle unsupported formats with alternative processing methods.

---

## Cosmos DB Partition Key Mismatches

### Error: Entity with specified id does not exist (404)

**Problem**: Cosmos DB returns "NotFound" error when trying to read documents that definitely exist in the container.

**Root Cause**: Using incorrect partition key value when reading documents. The partition key used in the read operation must exactly match the partition key of the stored document.

**Common Scenarios**:
- Design documentation specifies one partition key but infrastructure uses another
- Application code uses wrong field as partition key value

**Example Error**:
```
(NotFound) Entity with the specified id does not exist in the system
Code: NotFound
```

**Solution**: Verify the actual partition key configuration and use correct field:
```python
# ❌ Wrong - using documentUrl when container uses submissionId as partition key
existing_doc = await container.read_item(
    item=document_id,
    partition_key=event.data.documentUrl  # Wrong partition key!
)

# ✅ Correct - match the container's actual partition key configuration
existing_doc = await container.read_item(
    item=document_id,
    partition_key=event.submissionId  # Correct partition key
)
```

**Debug Steps**:
1. Check Terraform configuration for actual partition key:
   ```terraform
   resource "azurerm_cosmosdb_sql_container" "documents" {
     partition_key_paths = ["/submissionId"]  # Actual partition key
   }
   ```
2. Verify document structure in Azure Portal
3. Update application code to use correct partition key field

**Prevention**: 
- Keep Design.md documentation in sync with Terraform infrastructure
- Test document operations with actual container configuration
- Add logging to show partition key values being used

---

## Azure SDK Async API Usage Issues

### Error: Unexpected keyword argument 'partition_key'

**Problem**: Cosmos DB operations fail with error about unexpected `partition_key` parameter.

**Root Cause**: In the async version of Azure Cosmos DB SDK, partition keys are automatically extracted from the document body based on container configuration, not passed as separate parameters.

**Solution**: Remove explicit partition_key parameters from create_item calls:
```python
# ❌ Wrong - explicit partition key parameter
await container.create_item(
    body=document_data,
    partition_key=partition_value  # This causes the error
)

# ✅ Correct - partition key extracted from document body
await container.create_item(
    body=document_data  # Partition key auto-extracted from body
)
```

**Key Insight**: The async Cosmos DB SDK behaves differently from the sync version regarding partition key handling. Always check SDK documentation for the specific version being used.

---

## Document Processing Architecture Patterns

### Issue: Creating duplicate records instead of updating existing ones

**Problem**: Document processing service creates new document records instead of updating existing ones, leading to data duplication and inconsistency.

**Root Cause**: Missing document ID in event data, forcing services to either search for existing records (inefficient) or create new ones (incorrect).

**Solution**: Include document ID in events for direct record updates:
```python
# ❌ Wrong - event only contains URL, requires search or creates duplicate
class DocumentUploadedEventData(BaseModel):
    documentUrl: str

# ✅ Correct - event includes document ID for direct updates
class DocumentUploadedEventData(BaseModel):
    documentUrl: str
    documentId: str  # Enables direct document updates

# Update existing document instead of creating new one
existing_doc = await container.read_item(
    item=event.data.documentId,
    partition_key=event.submissionId
)
existing_doc['content'] = extracted_content
await container.replace_item(item=event.data.documentId, body=existing_doc)
```

**Architectural Flow**:
1. submission-intake creates initial DocumentRecord with empty content
2. submission-intake emits DocumentUploadedEvent with documentId
3. docproc-parser-foundry updates existing DocumentRecord with extracted content
4. Other services continue updating the same record

**Prevention**: Design events to include sufficient context for efficient operations. Avoid forcing downstream services to search for related records.

---
