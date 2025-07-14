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
- **Change Feed returns no events** → Use `start_time="Beginning"` for initial processing
- **Query parameter errors** → `enable_cross_partition_query=True` goes in query_items call, not as query parameter

**Examples**:
```python
# Correct partition key usage
container.read_item(item=id, partition_key=correct_value)

# Valid document ID
doc_id = str(uuid.uuid4())

# Async SDK - let SDK extract partition key
await container.create_item(body=data)

# Correct Change Feed initialization
if continuation_token:
    feed_iterator = container.query_items_change_feed(continuation=continuation_token)
else:
    feed_iterator = container.query_items_change_feed(start_time="Beginning")

# Correct cross-partition query
items = container.query_items(query=sql, enable_cross_partition_query=True)
```

---

## Cosmos DB Change Feed Processing

**Errors**:
- **Change Feed returns no events despite events in container** → Use `start_time="Beginning"` when no continuation token
- **`enable_cross_partition_query` unexpected keyword** → Use in query options, not as parameter: `query_items(query=sql, enable_cross_partition_query=True)`
- **Change Feed iterator returns empty batches** → Don't iterate over batches, iterate directly over items with `async for event_data in feed_iterator:`
- **Continuation token stays None** → Check if `feed_iterator.continuation_token` exists after iteration
- **File completely empty after manual edits** → Always backup files before manual editing; recreate from template if corrupted

**Correct Change Feed Pattern**:
```python
# Correct approach
if self.continuation_token:
    feed_iterator = container.query_items_change_feed(
        continuation=self.continuation_token,
        max_item_count=100
    )
else:
    feed_iterator = container.query_items_change_feed(
        start_time="Beginning",  # Important for initial processing
        max_item_count=100
    )

# Process items directly, not batches
async for event_data in feed_iterator:
    await self._process_event(event_data)

# Update continuation token after processing
if hasattr(feed_iterator, 'continuation_token'):
    self.continuation_token = feed_iterator.continuation_token
```

**Wrong Patterns**:
```python
# Wrong - iterating over batches
async for batch in feed_iterator:
    for event_data in batch:  # This won't work

# Wrong - missing start_time for initial processing
feed_iterator = container.query_items_change_feed(
    continuation=None,  # This won't get historical events
    max_item_count=100
)

# Wrong - query parameter placement
container.query_items(query=sql, enable_cross_partition_query=True)  # Correct
container.query_items(query=sql, enable_cross_partition_query=True)  # This was the error
```

**Debugging Tips**:
- Use `SELECT TOP 5 c.eventType FROM c` to verify events exist in container
- Check container properties with `await container.read()` to verify change feed is enabled
- Add debug logging for continuation token changes
- Test with `LOG_LEVEL=DEBUG` to see detailed processing flow

**Prevention**: Always test change feed processing with existing data before deploying to production.

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

## FastAPI Development

**Errors**:
- **422 Unprocessable Entity with "Field required"** → Parameter name mismatch between URL and function signature
  - **Solution**: Use camelCase parameter names (startDate, endDate) to match OpenAPI spec and client expectations
  - **Example**: `startDate: datetime = Query(...)` not `start_date: datetime = Query(...)`

- **Missing ProductType in mock data** → KeyError when accessing dictionary with enum key
  - **Solution**: Ensure all enum values have corresponding entries in data dictionaries
  - **Example**: Add `ProductType.other` to both `PRODUCT_NAMES` and `PRODUCT_FEATURES`

- **Timezone issues on Windows** → `zoneinfo.ZoneInfoNotFoundError: No time zone found with key UTC`
  - **Solution**: Use `datetime.timezone.utc` instead of `ZoneInfo("UTC")` for cross-platform compatibility
  - **Alternative**: Add `tzdata` package to dependencies

**Prevention**: Test all enum values, use cross-platform datetime handling, maintain consistent parameter naming.

---

## File Corruption & Code Recovery

**Errors**:
- **File becomes completely empty after manual edits** → Always backup before manual editing
- **Import errors after file corruption** → `ImportError: cannot import name 'Class' from 'module'`
- **Lost implementation after editing conflicts** → No version control or backup

**Recovery Strategies**:
```python
# Check if file is corrupted
try:
    from module import Class
except ImportError as e:
    print(f"Import failed: {e}")
    # File likely corrupted, needs recreation
```

**Prevention**:
- Always commit working code before major changes
- Use `git stash` before risky manual edits
- Test imports after file modifications: `python -c "from module import Class"`
- Copy working files to `.bak` before manual editing
- Use IDE's local history feature as backup

**File Recreation Process**:
1. Check git history for last working version
2. Identify required imports and class structure
3. Recreate from template or copy from similar service
4. Test imports before proceeding with implementation

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
