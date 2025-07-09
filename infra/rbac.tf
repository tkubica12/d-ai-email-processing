# RBAC assignments for local development and service identities

# Allow current user (for local development) to read/write blobs in the storage account
resource "azurerm_role_assignment" "current_user_storage_blob_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
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
