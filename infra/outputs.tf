output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "AZURE_RESOURCE_GROUP" {
  description = "The name of the resource group for AZD environment variable"
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_connection_string" {
  description = "The connection string for the storage account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "service_bus_namespace_name" {
  description = "The name of the Service Bus namespace"
  value       = azurerm_servicebus_namespace.main.name
}

output "service_bus_connection_string" {
  description = "The connection string for the Service Bus namespace"
  value       = azurerm_servicebus_namespace.main.default_primary_connection_string
  sensitive   = true
}

output "service_bus_topic_name" {
  description = "The name of the Service Bus topic for email events"
  value       = azurerm_servicebus_topic.email_events.name
}

output "logic_app_name" {
  description = "The name of the Logic App Standard"
  value       = azurerm_logic_app_standard.main.name
}

output "logic_app_id" {
  description = "The ID of the Logic App Standard"
  value       = azurerm_logic_app_standard.main.id
}

output "logic_app_identity_principal_id" {
  description = "The principal ID of the Logic App's managed identity"
  value       = azurerm_logic_app_standard.main.identity[0].principal_id
}

output "logic_app_default_hostname" {
  description = "The default hostname of the Logic App Standard"
  value       = azurerm_logic_app_standard.main.default_hostname
}

output "office365_connection_id" {
  description = "The ID of the Office 365 API connection"
  value       = azurerm_api_connection.office365.id
}

output "office365_connection_name" {
  description = "The name of the Office 365 API connection"
  value       = azurerm_api_connection.office365.name
}
