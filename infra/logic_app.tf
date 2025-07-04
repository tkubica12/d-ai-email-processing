# Log Analytics Workspace for Application Insights
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = local.environment
  }
}

# Application Insights for monitoring
resource "azurerm_application_insights" "main" {
  name                = "ai-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id

  tags = {
    environment = local.environment
  }
}

# App Service Plan for Logic App Standard
resource "azurerm_service_plan" "main" {
  name                = "asp-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Windows"
  sku_name            = "WS1"

  tags = {
    environment = local.environment
  }
}

# Logic App Standard - Minimal Configuration
resource "azurerm_logic_app_standard" "main" {
  name                       = "logic-${local.prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  app_service_plan_id        = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"     = "node"
    "WEBSITE_NODE_DEFAULT_VERSION" = "~18"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    "azd-service-name" = "logic-app"
    environment        = local.environment
  }
}

# Office 365 API Connection
resource "azurerm_api_connection" "office365" {
  name                = "office365-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  managed_api_id      = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${azurerm_resource_group.main.location}/managedApis/office365"
  display_name        = "Office 365 Connection"
  
  tags = {
    environment = local.environment
  }
}
