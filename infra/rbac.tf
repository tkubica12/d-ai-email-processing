# RBAC assignments for local development and service identities

# Allow current user (for local development) to read/write blobs in the storage account
resource "azurerm_role_assignment" "current_user_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow current user (for local development) to read/write tables in the storage account
resource "azurerm_role_assignment" "current_user_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
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

# Allow current user (for local development) to manage AI Search service
resource "azurerm_role_assignment" "current_user_search_service_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Service Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_search_index_data_contributor" {
  scope                = azurerm_search_service.main.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Managed Identity for Company APIs service
resource "azurerm_user_assigned_identity" "company_apis" {
  name                = "company-apis-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Client Web service
resource "azurerm_user_assigned_identity" "client_web" {
  name                = "client-web-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Submission Intake service
resource "azurerm_user_assigned_identity" "submission_intake" {
  name                = "submission-intake-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Document Parser Foundry service
resource "azurerm_user_assigned_identity" "docproc_parser_foundry" {
  name                = "docproc-parser-foundry-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Document Classifier service
resource "azurerm_user_assigned_identity" "docproc_classifier" {
  name                = "docproc-classifier-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Document Data Extractor service
resource "azurerm_user_assigned_identity" "docproc_data_extractor" {
  name                = "docproc-data-extractor-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Allow Company APIs service to read/write blobs in the storage account
resource "azurerm_role_assignment" "company_apis_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

# Allow Company APIs service to read/write tables in the storage account
resource "azurerm_role_assignment" "company_apis_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.company_apis.principal_id
}

# Allow current user (for local development) to use Azure OpenAI service
resource "azurerm_role_assignment" "current_user_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Allow Azure AI Search service to use Azure OpenAI for vectorization
resource "azurerm_role_assignment" "search_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

# Allow Azure AI Search service to read blob storage for data source
resource "azurerm_role_assignment" "search_storage_blob_reader" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

# Allow Azure AI Search service to read storage account for data source
resource "azurerm_role_assignment" "search_storage_account_reader" {
  scope                = azapi_resource.main.id
  role_definition_name = "Reader"
  principal_id         = azurerm_search_service.main.identity[0].principal_id
}

# Allow Client Web service to read/write blobs in the storage account
resource "azurerm_role_assignment" "client_web_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

# Allow Client Web service to read/write tables in the storage account
resource "azurerm_role_assignment" "client_web_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

# Allow Client Web service to send messages to Service Bus
resource "azurerm_role_assignment" "client_web_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

# Allow Submission Intake service to receive messages from Service Bus
resource "azurerm_role_assignment" "submission_intake_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

# Allow Submission Intake service to read/write blobs in the storage account
resource "azurerm_role_assignment" "submission_intake_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

# Allow Submission Intake service to read/write tables in the storage account
resource "azurerm_role_assignment" "submission_intake_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

# Allow Document Parser Foundry service to read/write blobs in the storage account
resource "azurerm_role_assignment" "docproc_parser_foundry_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

# Allow Document Parser Foundry service to read/write tables in the storage account
resource "azurerm_role_assignment" "docproc_parser_foundry_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

# Allow Document Parser Foundry service to use Document Intelligence service
resource "azurerm_role_assignment" "docproc_parser_foundry_document_intelligence_user" {
  scope                = azurerm_cognitive_account.document_intelligence.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.docproc_parser_foundry.principal_id
}

# Allow Document Data Extractor service to read/write blobs in the storage account
resource "azurerm_role_assignment" "docproc_data_extractor_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

# Allow Document Data Extractor service to read/write tables in the storage account
resource "azurerm_role_assignment" "docproc_data_extractor_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

# Allow Document Data Extractor service to use Azure OpenAI service
resource "azurerm_role_assignment" "docproc_data_extractor_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.docproc_data_extractor.principal_id
}

# Allow Document Classifier service to read/write blobs in the storage account
resource "azurerm_role_assignment" "docproc_classifier_storage_blob_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}

# Allow Document Classifier service to read/write tables in the storage account
resource "azurerm_role_assignment" "docproc_classifier_storage_table_contributor" {
  scope                = azapi_resource.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}

# Allow Document Classifier service to use Azure OpenAI service
resource "azurerm_role_assignment" "docproc_classifier_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.docproc_classifier.principal_id
}
