# RBAC assignments for Azure AI Search service

# Current user AI Search permissions for local development
resource "azurerm_role_assignment" "current_user_search_service_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Service Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_search_index_data_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Azure AI Search service permissions to access other resources
resource "azurerm_role_assignment" "search_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "search_storage_blob_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "search_storage_account_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Reader"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

# Logic App system identity AI Search permissions
resource "azurerm_role_assignment" "logic_app_system_identity_search_service_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Service Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

resource "azurerm_role_assignment" "logic_app_system_identity_search_index_data_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

# Document Search Indexer service AI Search permissions
resource "azurerm_role_assignment" "docproc_search_indexer_search_service_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Service Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
}

resource "azurerm_role_assignment" "docproc_search_indexer_search_index_data_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
}
