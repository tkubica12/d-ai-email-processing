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

## Best Practices Learned
- Always use the short form of language names in AZD configuration
- Test AZD configuration after each change to catch validation errors early
- Keep environment-specific values in `.azure/[env]/.env.json` files
