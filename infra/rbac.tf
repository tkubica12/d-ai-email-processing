# RBAC assignments for local development and service identities

# Allow current user (for local development) to read/write blobs in the storage account
resource "azurerm_role_assignment" "current_user_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to read/write tables in the storage account
resource "azurerm_role_assignment" "current_user_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to send messages to Service Bus
resource "azurerm_role_assignment" "current_user_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to receive messages from Service Bus
resource "azurerm_role_assignment" "current_user_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to use Document Intelligence service
resource "azurerm_role_assignment" "current_user_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to manage AI Search service
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

# Managed Identity for Company APIs service
resource "azurerm_user_assigned_identity" "company_apis" {
  location            = azurerm_resource_group.main.location
  name                = "id-company-apis-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
}

# Allow Company APIs service to read/write blobs in the storage account
resource "azurerm_role_assignment" "company_apis_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

# Allow Company APIs service to read/write tables in the storage account
resource "azurerm_role_assignment" "company_apis_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

# Allow current user (for local development) to use Azure OpenAI service
resource "azurerm_role_assignment" "current_user_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow Azure AI Search service to use Azure OpenAI for vectorization
resource "azurerm_role_assignment" "search_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}
