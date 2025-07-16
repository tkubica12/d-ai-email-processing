# Common Errors Reference

Quick troubleshooting guide for development issues, organized by category.

## 1. Azure & Authentication
**Purpose**: Common authentication and Azure resource deployment issues.

**DefaultAzureCredential failed**
```powershell
az login
az account set --subscription <subscription-id>
```

**AuthorizationFailed (403)**
- Check RBAC roles in Azure portal
- Re-apply Terraform to update permissions
- Verify service principal has correct scope

**Resource already exists**
- Import existing resource: `terraform import <resource_type>.<name> <azure_resource_id>`
- Or destroy and recreate: `terraform destroy -target=<resource>`

## 2. Environment & Dependencies
**Purpose**: Development environment setup and package management.

**Missing environment variables**
- Update `.env` with Terraform outputs
- Check `terraform output` for current values

**Import could not be resolved**
```powershell
uv sync          # Install dependencies
uv run python    # Run with proper environment
```

**Missing Azure SDK packages**
Add to `pyproject.toml`:
```toml
[dependencies]
azure-cosmos = "^4.0"
azure-identity = "^1.15"
azure-data-tables = "^12.0"
```

**Type hints errors**
- Use `list` instead of `typing.List`
- Use `dict` instead of `typing.Dict`

## 3. Cosmos DB Issues
**Purpose**: Database operations and change feed processing.

### Basic Operations
**Entity already exists (409)**
- Match unique key paths to container schema
- Use `upsert_item()` instead of `create_item()`

**Entity not found (404)**
- Verify partition key matches container definition
- Check document ID format (avoid URLs with `/`)

**Invalid partition key**
- Use UUIDs for document IDs
- Remove explicit `partition_key` parameter in async SDK

**Async SDK partition key error**
```
ClientSession._request() got an unexpected keyword argument 'partition_key'
```
This occurs when explicitly passing partition_key to create/replace operations:
```python
# Wrong - causes the error above
await container.create_item(body=data, partition_key=key)
await container.replace_item(item=id, body=data, partition_key=key)

# Correct - SDK handles partition key automatically for create/replace
await container.create_item(body=data)
await container.replace_item(item=id, body=data)
```

**Missing partition key error**
```
ContainerProxy.read_item() missing 1 required positional argument: 'partition_key'
```
This occurs when NOT passing partition_key to read operations:
```python
# Wrong - causes the error above
await container.read_item(item=id)

# Correct - read operations require explicit partition key
await container.read_item(item=id, partition_key=key)
```

### Change Feed Processing
**No events despite data exists**
```python
# Use start_time when no continuation token
feed_iterator = container.query_items_change_feed(start_time="Beginning")
```

**Iterator returns empty batches**
```python
# Correct pattern - iterate directly over items
async for event_data in feed_iterator:
    await self._process_event(event_data)
```

**Continuation token stays None**
```python
# Check token after iteration
if hasattr(feed_iterator, 'continuation_token'):
    self.continuation_token = feed_iterator.continuation_token
```

### Query Issues
**`enable_cross_partition_query` unexpected keyword**
```python
items = container.query_items(
    query=sql, 
    enable_cross_partition_query=True
)
```

## 4. Data Processing & Models
**Purpose**: Data extraction and model attribute errors.

**'LLMDataExtractionResponse' object has no attribute 'type'**
- Extraction response only contains data fields (invoiceNumber, totalAmount)
- Document metadata is in DocumentRecord

```python
# Wrong
extraction_result.type  # AttributeError

# Correct
document_record.type or 'unknown'  # Safe access
```

## 5. API Development
**Purpose**: FastAPI, OpenAI, and serialization issues.

### FastAPI
**422 Unprocessable Entity**
- Use camelCase parameter names to match OpenAPI spec
- Ensure all enum values have dictionary entries

**Timezone issues on Windows**
```python
# Use timezone.utc instead of ZoneInfo
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

### OpenAI
**400 BadRequest with empty body**
- Flatten nested Pydantic models
- Avoid nested objects with `$ref` in schema
- Use stable API versions: `2024-06-01`

### Serialization
**datetime not JSON serializable**
```python
# Use model_dump(mode='json') instead of model_dump()
response = model.model_dump(mode='json')

# Or for older Pydantic versions
response = model.model_dump_json()
```

**Common in Cosmos DB operations**
```python
# Wrong - causes datetime serialization error
await container.create_item(body=projection.model_dump())

# Correct - properly serializes datetime objects
await container.create_item(body=projection.model_dump(mode='json'))
```

## 6. Development Environment
**Purpose**: Local development and deployment issues.

**Port already in use**
```powershell
netstat -ano | findstr :8000  # Find process
taskkill /PID <process_id> /F  # Kill process
```

**Container build fails**
- Ensure `uv.lock` exists before building
- Check network connectivity for package downloads

## 7. File & Code Management
**Purpose**: Code corruption and recovery.

**File becomes empty after manual edits**
- Always backup before risky edits: `git stash`
- Test imports: `python -c "from module import Class"`

**Recovery steps**:
1. Check git history: `git log --oneline`
2. Restore from backup: `git checkout HEAD~1 -- <file>`
3. Recreate from template if needed

## Quick Debug Commands
```powershell
# Azure auth check
uv run python -c "from azure.identity import DefaultAzureCredential; DefaultAzureCredential().get_token('https://storage.azure.com/.default')"

# Port usage
netstat -ano | findstr :8000

# Environment variables
uv run python -c "import os; print(os.getenv('AZURE_STORAGE_ACCOUNT_NAME'))"

# Cosmos DB data check
SELECT TOP 5 c.eventType FROM c
```
