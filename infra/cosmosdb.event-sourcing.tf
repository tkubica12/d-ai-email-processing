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

# Submission trigger container for tracking document processing status
resource "azurerm_cosmosdb_sql_container" "submission_trigger" {
  name                = "submissionstrigger"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/submissionId"]
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

# Generate UUID for docproc-search-indexer role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_docproc_search_indexer" {}

# Role assignment for docproc-search-indexer service
resource "azurerm_cosmosdb_sql_role_assignment" "docproc_search_indexer" {
  name                = random_uuid.cosmosdb_role_assignment_guid_docproc_search_indexer.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for submission-trigger role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_submission_trigger" {}

# Role assignment for submission-trigger service
resource "azurerm_cosmosdb_sql_role_assignment" "submission_trigger" {
  name                = random_uuid.cosmosdb_role_assignment_guid_submission_trigger.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.submission_trigger.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# Generate UUID for submission-analyzer role assignment
resource "random_uuid" "cosmosdb_role_assignment_guid_submission_analyzer" {}

# Role assignment for submission-analyzer service
resource "azurerm_cosmosdb_sql_role_assignment" "submission_analyzer" {
  name                = random_uuid.cosmosdb_role_assignment_guid_submission_analyzer.result
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.data_contributor.id
  principal_id        = azurerm_user_assigned_identity.submission_analyzer.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}
