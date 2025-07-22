# RBAC assignments for Azure Storage services

# Current user storage permissions for local development
resource "azurerm_role_assignment" "current_user_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Company APIs service storage permissions
resource "azurerm_role_assignment" "company_apis_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

resource "azurerm_role_assignment" "company_apis_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

# Client Web service storage permissions
resource "azurerm_role_assignment" "client_web_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

resource "azurerm_role_assignment" "client_web_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

# Submission Intake service storage permissions
resource "azurerm_role_assignment" "submission_intake_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

resource "azurerm_role_assignment" "submission_intake_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

# Document Parser Foundry service storage permissions
resource "azurerm_role_assignment" "docproc_parser_foundry_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

resource "azurerm_role_assignment" "docproc_parser_foundry_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

# Document Data Extractor service storage permissions
resource "azurerm_role_assignment" "docproc_data_extractor_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

resource "azurerm_role_assignment" "docproc_data_extractor_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

# Document Classifier service storage permissions
resource "azurerm_role_assignment" "docproc_classifier_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}

resource "azurerm_role_assignment" "docproc_classifier_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}

# Document Search Indexer service storage permissions
resource "azurerm_role_assignment" "docproc_search_indexer_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
}

resource "azurerm_role_assignment" "docproc_search_indexer_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
}

# Submission Trigger service storage permissions
resource "azurerm_role_assignment" "submission_trigger_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

resource "azurerm_role_assignment" "submission_trigger_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

resource "azurerm_role_assignment" "submission_trigger_storage_blob_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

resource "azurerm_role_assignment" "submission_trigger_storage_account_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

# Submission Analyzer storage permissions
resource "azurerm_role_assignment" "submission_analyzer_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_storage_blob_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_storage_account_reader" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

# Logic App storage permissions
resource "azurerm_role_assignment" "logic_app_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_storage_queue_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_storage_account_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

# Logic App system-assigned identity storage permissions
# Required for built-in connectors (Blob, Queue, Table)
resource "azurerm_role_assignment" "logic_app_system_storage_blob_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

resource "azurerm_role_assignment" "logic_app_system_storage_queue_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

resource "azurerm_role_assignment" "logic_app_system_storage_table_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

resource "azurerm_role_assignment" "logic_app_system_storage_account_contributor" {
  scope                = azapi_resource.storage_account.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}
