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

## Best Practices Learned
- Always use the short form of language names in AZD configuration
- Test AZD configuration after each change to catch validation errors early
- Keep environment-specific values in `.azure/[env]/.env.json` files
