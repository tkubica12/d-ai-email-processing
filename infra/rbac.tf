# Managed Identity role assignments for Logic App

# Allow Logic App to read/write blobs in the storage account
resource "azurerm_role_assignment" "logic_app_storage_blob_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_logic_app_workflow.main.identity[0].principal_id
}

# Allow Logic App to send messages to Service Bus
resource "azurerm_role_assignment" "logic_app_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_logic_app_workflow.main.identity[0].principal_id
}
