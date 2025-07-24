# Managed identities for all services

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

# Managed Identity for Document Search Indexer service
resource "azurerm_user_assigned_identity" "docproc_search_indexer" {
  name                = "docproc-search-indexer-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Submission Trigger service
resource "azurerm_user_assigned_identity" "submission_trigger" {
  name                = "submission-trigger-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Submission Analyzer service
resource "azurerm_user_assigned_identity" "submission_analyzer" {
  name                = "submission-analyzer-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Logic App
resource "azurerm_user_assigned_identity" "logic_app" {
  name                = "logic-app-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Managed Identity for Durable Functions
resource "azurerm_user_assigned_identity" "durable_functions" {
  name                = "durable-functions-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}
