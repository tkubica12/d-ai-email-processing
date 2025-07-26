# Common Errors & Solutions

Quick reference for critical issues encountered during development.

## Azure Authentication & Resources

### Authentication Failures
**DefaultAzureCredential failed**
```powershell
az login
az account set --subscription <subscription-id>
```

**AuthorizationFailed (403)**
- Check RBAC roles in Azure portal
- Re-apply Terraform: `terraform apply`

**Resource conflicts**
```powershell
terraform import <resource_type>.<name> <azure_resource_id>
terraform destroy -target=<resource>  # Alternative
```

## Environment & Dependencies

### Missing Dependencies
**Environment variables**: `terraform output` → update `.env`
**Python packages**: `uv sync && uv run python`
**Azure SDK**: Add to `pyproject.toml`:
```toml
azure-cosmos = "^4.0"
azure-identity = "^1.15"
azure-data-tables = "^12.0"
```

**Type hints**: Use `list`, `dict` (not `typing.List`, `typing.Dict`)

## Azure Functions Critical Issues ⚠️

### Silent Function Failures
**Cause**: Module-level imports crash during cold start
```python
# ❌ NEVER do module-level imports
from models import SubmissionMessage

@app.activity_trigger(input_name="data")
async def my_activity(data):
    # Code never executes - import crashed

# ✅ ALWAYS import inside functions
@app.activity_trigger(input_name="data")
async def my_activity(data):
    from models import SubmissionMessage
    # Function works properly
```

### Storage Permissions
**DurableTaskStorageException** - Requires ALL three roles:
- `Storage Blob Data Reader`
- `Storage Table Data Contributor`
- `Storage Queue Data Contributor` ← Often missed

### Orchestrator Issues
**Immediate completion (104ms)** - Missing `yield`:
```python
# ❌ Missing yield
def orchestrator(context):
    context.call_activity("my_activity", data)

# ✅ Proper yield
def orchestrator(context):
    result = yield context.call_activity("my_activity", data)
```

## Cosmos DB Issues

### Parameter Errors
**Unexpected keyword 'partition_key'**
```python
# ❌ Wrong - Don't specify partition_key for create/replace
await container.create_item(body=data, partition_key=key)

# ✅ Correct - SDK handles automatically
await container.create_item(body=data)
```

**Missing partition_key for reads**
```python
# ❌ Wrong
await container.read_item(item=id)

# ✅ Correct - Reads need explicit partition key
await container.read_item(item=id, partition_key=key)
```

### ETag Operations ⚠️ CRITICAL
**Unexpected keyword 'if_match_etag'** - Parameter doesn't exist in Python SDK
```python
# ❌ WRONG - 'if_match_etag' doesn't exist
await container.patch_item(..., if_match_etag=etag)

# ✅ CORRECT - Use 'etag' and 'match_condition'
from azure.core import MatchConditions

kwargs = {}
if etag:
    kwargs["etag"] = etag
    kwargs["match_condition"] = MatchConditions.IfNotModified

await container.patch_item(item=id, partition_key=key, patch_operations=ops, **kwargs)
```

### Serialization
**datetime not JSON serializable**
```python
# ❌ Wrong
await container.create_item(body=projection.model_dump())

# ✅ Correct
await container.create_item(body=projection.model_dump(mode='json'))
```

## API Development

### Azure OpenAI Issues
**400 BadRequest** - Use structured outputs:
```python
# ❌ Wrong - Standard API
response = await client.chat.completions.create(...)

# ✅ Correct - Beta API with structured outputs
response = await client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[...],
    response_format=MyPydanticModel,
    temperature=0
)
```

**Authentication** - Use Azure AD, not API keys:
```python
client = AsyncAzureOpenAI(
    azure_endpoint=endpoint,
    azure_ad_token_provider=self._get_azure_ad_token,
    api_version="2024-08-01-preview"
)
```

### Document Intelligence
**Missing argument: body**
```python
# ❌ Wrong parameter name
poller = await client.begin_analyze_document(model_id="...", analyze_request=request)

# ✅ Correct parameter name
poller = await client.begin_analyze_document(model_id="...", body=request)
```

### Architecture Misunderstanding ⚠️
**Data Extraction Logic**: Run extraction on ALL documents, not just invoices
```python
# ❌ Wrong - Don't filter by type
if document_type == "invoice":
    result = await extract_data(document)

# ✅ Correct - Always extract, LLM handles type
result = await extract_data(document)  # Returns nulls for non-invoice fields
```

## Development Tools

### Port Issues
```powershell
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### File Recovery
```powershell
git stash                    # Backup before risky edits
git checkout HEAD~1 -- <file>  # Restore from history
```

## Quick Diagnostics
```powershell
# Test Azure auth
uv run python -c "from azure.identity import DefaultAzureCredential; DefaultAzureCredential().get_token('https://storage.azure.com/.default')"

# Test imports
python -c "from module import Class"

# Debug function calls with prints
print(f'DEBUG: About to call function with {param}')
result = await function_call(param)
print(f'DEBUG: Function returned {result}')
```
