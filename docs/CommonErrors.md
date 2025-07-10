# Common Errors and Solutions

Quick reference for common development errors, grouped by category.

---

## Azure Authentication & Permissions

**Errors**:
- **DefaultAzureCredential failed** → `az login`, `az account set --subscription <id>`
- **AuthorizationFailed** → Check RBAC roles, re-apply Terraform

**Prevention**: Verify authentication and RBAC before app startup.

---

## Environment & Configuration

**Errors**:
- **Missing environment variables** → Update `.env` with Terraform outputs
- **Config field name mismatch** → Ensure field names match between model and access

**Prevention**: Validate environment at startup.

---

## Dependencies & Imports

**Errors**:
- **Import could not be resolved** → `uv sync`, use `uv run`
- **Missing Azure SDK packages** → Add to `pyproject.toml` (azure-cosmos, azure-identity, azure-data-tables)

**Prevention**: Always sync dependencies and activate environment.

---

## Terraform & Azure Resources

**Errors**:
- **Resource already exists** → Import resource or destroy/recreate
- **RBAC not applied** → Check `terraform plan`, re-apply if needed

**Prevention**: Use consistent naming and manage state carefully.

---

## Azure Storage & File Handling

**Errors**:
- **File upload fails silently** → Check input handling, permissions, add logging
- **Invalid file format** → Validate file extensions before processing

**Prevention**: Add logging and error handling for uploads.

---

## Service Bus & Messaging

**Errors**:
- **Message publishing fails** → Verify topic, permissions, message format
- **Event missing document ID** → Include documentId in events for direct updates

**Example**:
```python
class DocumentUploadedEventData(BaseModel):
    documentUrl: str
    documentId: str  # Required for updates
```

---

## Cosmos DB Operations

**Errors**:
- **Entity already exists (409)** → Match unique key paths to schema
- **Entity not found (404)** → Use correct partition key from container config
- **Invalid document ID** → Use UUIDs, not URLs with `/`
- **Unexpected keyword 'partition_key'** → Remove explicit partition_key in async SDK

**Examples**:
```python
# Correct partition key usage
container.read_item(item=id, partition_key=correct_value)

# Valid document ID
doc_id = str(uuid.uuid4())

# Async SDK - let SDK extract partition key
await container.create_item(body=data)
```

---

## FastHTML Framework

**Errors**:
- **Type List cannot be instantiated** → Use `list` instead of `typing.List`

**Example**:
```python
# Correct
async def post(attachments: Optional[list] = None):
```

---

## OpenAI Structured Outputs

**Errors**:
- **400 BadRequest with empty body** → Flatten nested Pydantic models to avoid schema issues
- **Schema additionalProperties error** → Avoid nested objects with `$ref`

**Example**:
```python
# Problem - Nested structure
class LLMResponse(BaseModel):
    type: DocumentType
    extractedData: ExtractedData  # Causes schema issues

# Solution - Flattened structure
class LLMResponse(BaseModel):
    invoiceNumber: Optional[str] = Field(None, description="Invoice number")
    totalAmount: Optional[float] = Field(None, description="Total amount")
```

**API Usage**: Use stable versions like `2024-06-01` instead of preview versions.

---

## Document Classification Service

**Errors**:
- **datetime not JSON serializable** → Use `model_dump_json()` instead of `model_dump()`

**Example**:
```python
# Correct
event_json = event.model_dump_json()
event_dict = json.loads(event_json)
await container.create_item(body=event_dict)
```

---

## Development Environment

**Errors**:
- **Port already in use** → Kill process or use different port
- **Container build fails** → Ensure `uv.lock` exists, check connectivity

**Prevention**: Check port availability, commit lock files.

---

## Quick Troubleshooting

1. **Authentication**: `az login`, check subscription and RBAC
2. **Environment**: Verify `.env` matches Terraform outputs
3. **Dependencies**: `uv sync`, activate virtual environment
4. **Resources**: Check storage account, Service Bus, role assignments

**Debug Commands**:
```powershell
# Check Azure connection
uv run python -c "from azure.identity import DefaultAzureCredential; DefaultAzureCredential().get_token('https://storage.azure.com/.default')"

# Check port usage
netstat -ano | findstr :8000

# Verify environment
uv run python -c "import os; print(os.getenv('AZURE_STORAGE_ACCOUNT_NAME'))"
```
