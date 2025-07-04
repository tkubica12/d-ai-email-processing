# Common Errors and Pitfalls

## Azure Developer CLI (azd) Issues

### Error: Invalid host type "logicapp"
**Issue**: When configuring `azure.yaml`, using `host: logicapp` causes validation errors.

**Error Message**: 
```
Value is not accepted. Valid values: "appservice", "containerapp", "function", "springapp", "staticwebapp", "aks", "ai.endpoint".
```

**Solution**: Use `host: function` instead, as it's the closest match for Logic App workflows in AZD.

**Root Cause**: AZD doesn't have native support for Logic App Standard as a host type yet.

### Error: Invalid language "javascript"
**Issue**: Using `language: javascript` in `azure.yaml` causes validation errors.

**Error Message**:
```
Value is not accepted. Valid values: "dotnet", "csharp", "fsharp", "py", "python", "js", "ts", "java", "docker".
```

**Solution**: Use `language: js` instead of `language: javascript`.

### Error: Command "azd auth status" not found
**Issue**: Attempting to check Azure Developer CLI authentication status using `azd auth status` command.

**Error Message**:
```
azd: 'auth status' is not a valid command
```

**Solution**: Use `azd auth login --check-status` instead to check authentication status.

**Root Cause**: The correct AZD command includes the `--check-status` flag with the login command, not a separate `status` subcommand.

### Error: Missing main.tfvars.json file
**Issue**: When running `azd up`, deployment fails with error about missing parameter file.

**Error Message**:
```
ERROR: error executing step command 'provision': deployment failed: error deploying infrastructure: creating parameters file: reading parameter file template: open C:\git\azure-workshops\d-ai-email-processing\infra\main.tfvars.json: The system cannot find the file specified.
```

**Solution**: Create `infra/main.tfvars.json` file with required Terraform variables in JSON format.

**Example**:
```json
{
  "environment_name": "dev",
  "location": "swedencentral", 
  "project_name": "email",
  "email_mailbox": "user@example.com"
}
```

**Root Cause**: AZD expects a JSON-formatted parameters file to pass variables to Terraform, even when variables have default values defined.

### Error: AZD deploy looking in wrong resource group
**Issue**: When running `azd deploy`, AZD searches for resources in the wrong resource group, even though the correct resource group exists and has properly tagged resources.

**Error Message**:
```
ERROR: getting target resource: resource not found: unable to find a resource tagged with 'azd-service-name: logic-app'. Ensure the service resource is correctly tagged in your infrastructure configuration, and rerun provision
```

**Debug Output Shows**:
```
GET https://management.azure.com/subscriptions/.../resourceGroups/rg-sharepoint/resources?...
```
(Instead of the correct resource group like `rg-email-dev-srng`)

**Solution**: Explicitly set the `AZURE_RESOURCE_GROUP` environment variable to force AZD to look in the correct resource group:

```bash
azd env set AZURE_RESOURCE_GROUP rg-email-dev-srng
azd deploy
```

**Root Cause**: This is a known AZD bug (GitHub Issue #689) where AZD gets confused when there are multiple resource groups in the subscription and may cache or search in the wrong resource group.

**Additional Notes**:
- The issue occurs even when the target resource has correct tags (`azd-service-name: logic-app`)
- The problem is intermittent and depends on the presence of other resource groups
- Setting `AZURE_RESOURCE_GROUP` explicitly resolves the issue permanently

## Best Practices Learned
- Always use the short form of language names in AZD configuration
- Test AZD configuration after each change to catch validation errors early
- Keep environment-specific values in `.azure/[env]/.env.json` files
- When working with multiple resource groups, explicitly set `AZURE_RESOURCE_GROUP` environment variable to avoid AZD confusion
- For Logic App Standard deployment, use `host: function` in azure.yaml and deploy using zip deploy mechanism
