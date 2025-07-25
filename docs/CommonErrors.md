# Common Errors Reference

Quick troubleshooting guide for development issues, organized by category.

## 1. Azure Authentication & Resources

**DefaultAzureCredential failed**
```powershell
az login
az account set --subscription <subscription-id>
```

**AuthorizationFailed (403)**
- Check RBAC roles in Azure portal
- Re-apply Terraform: `terraform apply`
- Verify service principal scope

**Resource already exists**
```powershell
terraform import <resource_type>.<name> <azure_resource_id>
# OR
terraform destroy -target=<resource>
```

## 2. Environment Setup

**Missing environment variables**
```powershell
terraform output  # Get current values
# Update .env file
```

**Import/dependency errors**
```powershell
uv sync && uv run python
```

**Missing Azure SDK packages** - Add to `pyproject.toml`:
```toml
azure-cosmos = "^4.0"
azure-identity = "^1.15" 
azure-data-tables = "^12.0"
```

**Type hints** - Use built-in types: `list`, `dict` (not `typing.List`, `typing.Dict`)

## 3. Azure Durable Functions

### Silent Function Failures ⚠️ CRITICAL
**Symptoms**: Function logs show completion but no application code executes
**Cause**: Module-level import failures during Azure Functions cold start

```python
# ❌ WRONG - Module-level imports cause silent crashes
from models import SubmissionMessage
from actions import DocumentParser

@app.activity_trigger(input_name="data")  
async def my_activity(data):
    # Code never executes - crashed during import

# ✅ CORRECT - Import inside function
@app.activity_trigger(input_name="data")
async def my_activity(data):
    from models import SubmissionMessage
    from actions import DocumentParser
    # Function executes properly
```

### Storage Permissions
**DurableTaskStorageException** - Requires ALL three storage roles:
```terraform
"Storage Blob Data Reader"
"Storage Table Data Contributor"  
"Storage Queue Data Contributor"  # Often forgotten
```

### Document Intelligence Integration
**'begin_analyze_document() missing argument: body'**
```python
# ❌ Wrong parameter name
poller = await client.begin_analyze_document(
    model_id="prebuilt-layout",
    analyze_request=request  # Wrong
)

# ✅ Correct parameter name  
poller = await client.begin_analyze_document(
    model_id="prebuilt-layout",
    body=request  # Correct
)
```

### Orchestrator Issues
**Orchestrator completes immediately (104ms) without calling activities**
**Cause**: Missing `yield` keywords

```python
# ❌ Wrong - activities never execute
def orchestrator(context):
    context.call_activity("my_activity", data)  # Missing yield
    return result

# ✅ Correct - proper yield usage
def orchestrator(context):
    result = yield context.call_activity("my_activity", data)
    return result
```

### Activity Function Parameters
**Method signature mismatches**
```python
# Debug technique - log parameters before calls
print(f"Calling with: submission_id={submission_id}, url={document_url}")
result = await parser.parse_document_async(submission_id, document_url, user_id)
```

## 4. Cosmos DB Operations

### Basic CRUD Operations
**Entity already exists (409)** - Use `upsert_item()` instead of `create_item()`
**Entity not found (404)** - Verify partition key and document ID format (use UUIDs)

### Async SDK Parameter Issues
**ClientSession._request() unexpected keyword 'partition_key'**
```python
# ❌ Wrong - explicit partition_key on create/replace
await container.create_item(body=data, partition_key=key)
await container.replace_item(item=id, body=data, partition_key=key)

# ✅ Correct - SDK handles partition key automatically
await container.create_item(body=data)
await container.replace_item(item=id, body=data)
```

**read_item() missing partition_key argument**
```python
# ❌ Wrong - missing partition key on read
await container.read_item(item=id)

# ✅ Correct - read operations require explicit partition key
await container.read_item(item=id, partition_key=key)
```

### Change Feed Processing
**No events despite data exists**
```python
# Use start_time when no continuation token
feed_iterator = container.query_items_change_feed(start_time="Beginning")

# Iterate directly over items
async for event_data in feed_iterator:
    await self._process_event(event_data)
    
# Check continuation token after iteration
if hasattr(feed_iterator, 'continuation_token'):
    self.continuation_token = feed_iterator.continuation_token
```

### Serialization Issues
**datetime not JSON serializable**
```python
# ❌ Wrong - causes datetime serialization error
await container.create_item(body=projection.model_dump())

# ✅ Correct - properly serializes datetime objects
await container.create_item(body=projection.model_dump(mode='json'))
```

## 5. API Development

### FastAPI Issues
**422 Unprocessable Entity**
- Use camelCase parameter names to match OpenAPI spec
- Ensure all enum values have dictionary entries

**Timezone issues on Windows**
```python
# Use timezone.utc instead of ZoneInfo
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

### OpenAI API
**400 BadRequest with empty body**
- Flatten nested Pydantic models (avoid `$ref` in schema)
- Use stable API versions: `2024-06-01`

### Data Model Issues
**'LLMDataExtractionResponse' object has no attribute 'type'**
```python
# ❌ Wrong - attribute doesn't exist
extraction_result.type

# ✅ Correct - use document metadata
document_record.type or 'unknown'
```

## 6. Development Environment

**Port already in use**
```powershell
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

**Container build fails**
- Ensure `uv.lock` exists before building
- Check network connectivity for package downloads

**File corruption recovery**
```powershell
git log --oneline                    # Check history
git checkout HEAD~1 -- <file>       # Restore from backup
git stash                            # Backup before risky edits
```

## Quick Debug Commands
```powershell
# Test Azure auth
uv run python -c "from azure.identity import DefaultAzureCredential; DefaultAzureCredential().get_token('https://storage.azure.com/.default')"

# Check environment variables
uv run python -c "import os; print(os.getenv('AZURE_STORAGE_ACCOUNT_NAME'))"

# Test imports
python -c "from module import Class"

# Cosmos DB query
SELECT TOP 5 c.eventType FROM c
```
