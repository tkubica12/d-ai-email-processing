# Common Errors Reference

Quick troubleshooting guide for development issues, organized by category.

## Azure & Authentication
**DefaultAzureCredential failed** → `az login`, `az account set --subscription <id>`  
**AuthorizationFailed** → Check RBAC roles, re-apply Terraform  
**Resource already exists** → Import resource or destroy/recreate

## Environment & Dependencies
**Missing environment variables** → Update `.env` with Terraform outputs  
**Import could not be resolved** → `uv sync`, use `uv run`  
**Missing Azure SDK packages** → Add to `pyproject.toml` (azure-cosmos, azure-identity, azure-data-tables)

## Cosmos DB

### Basic Operations
**Entity already exists (409)** → Match unique key paths to schema  
**Entity not found (404)** → Use correct partition key from container  
**Invalid document ID** → Use UUIDs, not URLs with `/`  
**Unexpected keyword 'partition_key'** → Remove explicit partition_key in async SDK

### Change Feed Processing
**No events despite data exists** → Use `start_time="Beginning"` when no continuation token  
**Iterator returns empty batches** → Iterate directly over items: `async for event_data in feed_iterator:`  
**Continuation token stays None** → Check `feed_iterator.continuation_token` after iteration

```python
# Correct Change Feed pattern
if self.continuation_token:
    feed_iterator = container.query_items_change_feed(continuation=self.continuation_token)
else:
    feed_iterator = container.query_items_change_feed(start_time="Beginning")

async for event_data in feed_iterator:  # Direct iteration, not batches
    await self._process_event(event_data)

if hasattr(feed_iterator, 'continuation_token'):
    self.continuation_token = feed_iterator.continuation_token
```

### Query Issues
**`enable_cross_partition_query` unexpected keyword** → Use in query_items call:
```python
items = container.query_items(query=sql, enable_cross_partition_query=True)
```

## Data Extraction Service

### Model Attribute Errors
**'LLMDataExtractionResponse' object has no attribute 'type'** → The data extraction response model only contains extracted data fields (invoiceNumber, totalAmount, etc.), not document metadata. Access document type from DocumentRecord:

```python
# Wrong - accessing type from extraction result
extraction_result.type  # AttributeError

# Correct - accessing type from document record
document_record.type or 'unknown'  # Safe access with fallback
```

**Resolution:** Use `document_record.type` for document classification info, `extraction_result` for extracted data fields.

## API Development

### FastAPI
**422 Unprocessable Entity** → Use camelCase parameter names to match OpenAPI spec  
**Missing enum values in mock data** → Ensure all enum values have dictionary entries  
**Timezone issues on Windows** → Use `datetime.timezone.utc` instead of `ZoneInfo("UTC")`

### OpenAI
**400 BadRequest with empty body** → Flatten nested Pydantic models  
**Schema additionalProperties error** → Avoid nested objects with `$ref`  
Use stable API versions like `2024-06-01`

### Serialization
**datetime not JSON serializable** → Use `model_dump_json()` instead of `model_dump()`

## Development Environment
**Port already in use** → Kill process or use different port  
**Container build fails** → Ensure `uv.lock` exists, check connectivity  
**Type List cannot be instantiated** → Use `list` instead of `typing.List`

## File & Code Management
**File becomes empty after manual edits** → Always backup before editing  
**Import errors after corruption** → Check git history, recreate from template  

**Recovery**: Test imports `python -c "from module import Class"`, use `git stash` before risky edits

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
