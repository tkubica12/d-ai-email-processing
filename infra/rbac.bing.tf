# RBAC assignments for Bing Grounding service
# Note: Bing connections in AI Foundry currently use API keys, not managed identity
# These permissions are for administrative access to the Bing resource itself

# Current user Bing permissions for local development and management
resource "azurerm_role_assignment" "current_user_bing_user" {
  scope                = azapi_resource.bing_grounding.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# AI Foundry system identity permissions for resource management (optional)
resource "azurerm_role_assignment" "ai_foundry_bing_user" {
  scope                = azapi_resource.bing_grounding.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azapi_resource.ai_foundry.identity[0].principal_id
}