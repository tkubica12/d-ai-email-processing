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
  value       = azapi_resource.storage_account.name
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
  value       = azapi_resource.storage_account.output.properties.primaryEndpoints.blob
}

output "service_bus_fqdn" {
  description = "The fully qualified domain name of the Service Bus namespace"
  value       = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
}

# Cosmos DB outputs
output "cosmosdb_account_name" {
  description = "The name of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_endpoint" {
  description = "The endpoint URL for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_primary_key" {
  description = "The primary key for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "cosmosdb_connection_strings" {
  description = "The connection strings for the Cosmos DB account"
  value       = azurerm_cosmosdb_account.main.connection_strings
  sensitive   = true
}

output "cosmosdb_database_name" {
  description = "The name of the Cosmos DB database"
  value       = azurerm_cosmosdb_sql_database.main.name
}

output "cosmosdb_events_container_name" {
  description = "The name of the events container"
  value       = azurerm_cosmosdb_sql_container.events.name
}

output "cosmosdb_documents_container_name" {
  description = "The name of the documents container"
  value       = azurerm_cosmosdb_sql_container.documents.name
}

output "cosmosdb_submissions_container_name" {
  description = "The name of the submissions container"
  value       = azurerm_cosmosdb_sql_container.submissions.name
}

output "document_intelligence_endpoint" {
  description = "The endpoint URL for the Document Intelligence service"
  value       = azurerm_cognitive_account.document_intelligence.endpoint
}

# Azure OpenAI outputs
output "azure_openai_endpoint" {
  description = "The endpoint URL for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.endpoint
}

# Azure AI Search outputs
output "azure_search_service_name" {
  description = "The name of the Azure AI Search service"
  value       = azurerm_search_service.main.name
}

output "azure_search_endpoint" {
  description = "The endpoint URL for the Azure AI Search service"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

# output "company_apis_url" {
#   description = "The URL for the Company APIs service"
#   value       = "https://${azapi_resource.company_apis.output.fqdn}"
# }

output "client_web_url" {
  description = "The URL for the Client Web service"
  value       = "https://${azapi_resource.client_web.output.properties.configuration.ingress.fqdn}"
}

# Logic App outputs
output "logic_app_name" {
  description = "The name of the Logic App"
  value       = azapi_resource.logic_app.name
}

output "logic_app_managed_identity_id" {
  description = "The resource ID of the Logic App managed identity"
  value       = azurerm_user_assigned_identity.logic_app.id
}

output "logic_app_managed_identity_principal_id" {
  description = "The principal ID of the Logic App managed identity"
  value       = azurerm_user_assigned_identity.logic_app.principal_id
}
