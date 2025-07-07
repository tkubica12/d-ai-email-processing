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
  value       = azurerm_servicebus_topic.new_submissions.name
}

output "service_bus_subscription_name" {
  description = "The name of the Service Bus subscription for submission-intake service"
  value       = azurerm_servicebus_subscription.submission_intake.name
}

# Additional outputs for client application
output "storage_account_blob_endpoint" {
  description = "The blob endpoint URL for the storage account"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "service_bus_fqdn" {
  description = "The fully qualified domain name of the Service Bus namespace"
  value       = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
}
