# RBAC assignments for Azure AI services (OpenAI, Document Intelligence)

# Current user AI services permissions for local development
resource "azurerm_role_assignment" "current_user_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_ai_developer" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Azure AI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Document Parser Foundry service AI permissions
resource "azurerm_role_assignment" "docproc_parser_foundry_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

# Document Data Extractor service AI permissions
resource "azurerm_role_assignment" "docproc_data_extractor_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

# Document Classifier service AI permissions
resource "azurerm_role_assignment" "docproc_classifier_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}

# Document Search Indexer service AI permissions
resource "azurerm_role_assignment" "docproc_search_indexer_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.docproc_search_indexer.principal_id
}

# Submission Trigger service AI permissions
resource "azurerm_role_assignment" "submission_trigger_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

resource "azurerm_role_assignment" "submission_trigger_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

# Submission Analyzer AI permissions
resource "azurerm_role_assignment" "submission_analyzer_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_ai_developer" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Azure AI User"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

# Logic App AI permissions
resource "azurerm_role_assignment" "logic_app_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_system_identity_openai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

resource "azurerm_role_assignment" "logic_app_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_ai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Azure AI User"
  principal_id         = azurerm_user_assigned_identity.logic_app.principal_id
}

resource "azurerm_role_assignment" "logic_app_system_identity_ai_user" {
  scope                = azapi_resource.ai_foundry.id
  role_definition_name = "Azure AI User"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}
