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

# Logic App Standard - Using AzAPI Provider
resource "azapi_resource" "logic_app_standard" {
  type      = "Microsoft.Web/sites@2022-09-01"
  name      = "logic-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "functionapp,workflowapp"
    properties = {
      serverFarmId = azurerm_service_plan.main.id
      siteConfig = {
        netFrameworkVersion                    = "v4.0"
        functionsRuntimeScaleMonitoringEnabled = false
        appSettings = [
          {
            name  = "FUNCTIONS_WORKER_RUNTIME"
            value = "dotnet"
          },
          {
            name  = "FUNCTIONS_EXTENSION_VERSION"
            value = "~4"
          },
          {
            name  = "AzureWebJobsStorage"
            value = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.main.name};AccountKey=${azurerm_storage_account.main.primary_access_key};EndpointSuffix=core.windows.net"
          },
          {
            name  = "WEBSITE_CONTENTAZUREFILECONNECTIONSTRING"
            value = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.main.name};AccountKey=${azurerm_storage_account.main.primary_access_key};EndpointSuffix=core.windows.net"
          },
          {
            name  = "WEBSITE_CONTENTSHARE"
            value = "logic-${local.prefix}"
          },
          {
            name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
            value = azurerm_application_insights.main.instrumentation_key
          },
          {
            name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
            value = azurerm_application_insights.main.connection_string
          }
        ]
      }
      clientAffinityEnabled = false
      httpsOnly             = true
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    "azd-service-name" = "logic-app"
    environment        = local.environment
  }
}

# Office 365 API Connection - Using AzAPI Provider
resource "azapi_resource" "office365_connection" {
  type      = "Microsoft.Web/connections@2016-06-01"
  name      = "office365-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    properties = {
      displayName = "Office 365 Connection"
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${azurerm_resource_group.main.location}/managedApis/office365"
      }
      parameterValues = {}
    }
  }

  tags = {
    environment = local.environment
  }
}
