# Cosmos DB Account for event sourcing and document storage
resource "azurerm_cosmosdb_account" "main" {
  name                = "${local.prefix}-cosmos"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  # Serverless configuration
  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 10
    max_staleness_prefix    = 200
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  # Enable change feed for event sourcing
  analytical_storage_enabled = false
  
  # Disable public network access for production security
  public_network_access_enabled = true
}

# Database for the email processing system
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "email-processing"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Events container for event sourcing
resource "azurerm_cosmosdb_sql_container" "events" {
  name                = "events"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/submissionId"]
}

# Documents container for processed document results
resource "azurerm_cosmosdb_sql_container" "documents" {
  name                = "documents"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/submissionId"]
}

# Submissions container for submission records
resource "azurerm_cosmosdb_sql_container" "submissions" {
  name                = "submissions"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/userId"]
}

# Generate UUIDs for role assignments to ensure uniqueness
resource "random_uuid" "cosmosdb_role_assignment_guid_self" {}

# Custom role definition for Cosmos DB data plane operations
resource "azurerm_cosmosdb_sql_role_definition" "data_contributor" {
  name                = "EmailProcessingDataContributor"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  type                = "CustomRole"
  assignable_scopes   = [azurerm_cosmosdb_account.main.id]

  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/readChangeFeed",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"
    ]
  }
}

# Role assignment for current user (local development)
resource "azurerm_cosmosdb_sql_role_assignment" "current_user" {
  name                = random_uuid.cosmosdb_role_assignment_guid_self.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = data.azurerm_client_config.current.object_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for submission-intake role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_submission_intake" {}

# Role assignment for submission-intake service
resource "azurerm_cosmosdb_sql_role_assignment" "submission_intake" {
  name                = random_uuid.cosmosdb_role_assignment_guid_submission_intake.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.submission_intake.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for docproc-parser-foundry role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_docproc_parser_foundry" {}

# Role assignment for docproc-parser-foundry service
resource "azurerm_cosmosdb_sql_role_assignment" "docproc_parser_foundry" {
  name                = random_uuid.cosmosdb_role_assignment_guid_docproc_parser_foundry.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for docproc-data-extractor role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_docproc_data_extractor" {}

# Role assignment for docproc-data-extractor service
resource "azurerm_cosmosdb_sql_role_assignment" "docproc_data_extractor" {
  name                = random_uuid.cosmosdb_role_assignment_guid_docproc_data_extractor.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for docproc-classifier role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_docproc_classifier" {}

# Role assignment for docproc-classifier service
resource "azurerm_cosmosdb_sql_role_assignment" "docproc_classifier" {
  name                = random_uuid.cosmosdb_role_assignment_guid_docproc_classifier.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.docproc_classifier.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}
