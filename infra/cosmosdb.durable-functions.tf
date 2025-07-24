# Cosmos DB database for durable functions orchestration
resource "azurerm_cosmosdb_sql_database" "durable_functions" {
  name                = "email-processing-durable-functions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Documents container for durable functions workflow
resource "azurerm_cosmosdb_sql_container" "durable_functions_documents" {
  name                = "documents"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.durable_functions.name
  partition_key_paths = ["/submissionId"]
}

# Submissions container for durable functions workflow
resource "azurerm_cosmosdb_sql_container" "durable_functions_submissions" {
  name                = "submissions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.durable_functions.name
  partition_key_paths = ["/userId"]
}

# Generate UUID for durable functions role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_durable_functions" {}

# Role assignment for durable functions service (future deployment)
resource "azurerm_cosmosdb_sql_role_assignment" "durable_functions" {
  name                = random_uuid.cosmosdb_role_assignment_guid_durable_functions.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.durable_functions.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}
