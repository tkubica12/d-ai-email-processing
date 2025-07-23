# Required blob containers for Logic App in existing storage account
resource "azapi_resource" "logic_app_blob_container_hosts" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = "azure-webjobs-hosts"
  parent_id = "${azapi_resource.storage_account.id}/blobServices/default"

  body = {
    properties = {
      publicAccess = "None"
    }
  }
}

# Service Plan for Logic App Standard
resource "azapi_resource" "logic_app_service_plan" {
  type      = "Microsoft.Web/serverFarms@2023-12-01"
  name      = "asp-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "elastic"
    sku = {
      capacity = 1
      family   = "WS"
      name     = "WS1"
      size     = "WS1"
      tier     = "WorkflowStandard"
    }
    properties = {
      elasticScaleEnabled       = true
      maximumElasticWorkerCount = 20
    }
  }
}

# Logic App Standard
resource "azapi_resource" "logic_app" {
  type      = "Microsoft.Web/sites@2023-12-01"
  name      = "logic-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "functionapp,workflowapp"
    properties = {
      clientAffinityEnabled = false
      httpsOnly             = true
      serverFarmId          = azapi_resource.logic_app_service_plan.id
      siteConfig = {
        appSettings = [
          {
            name  = "FUNCTIONS_EXTENSION_VERSION"
            value = "~4"
          },
          {
            name  = "FUNCTIONS_WORKER_RUNTIME"
            value = "node"
          },
          {
            name  = "WEBSITE_NODE_DEFAULT_VERSION"
            value = "~20"
          },
          {
            name  = "AzureWebJobsStorage__managedIdentityResourceId"
            value = azurerm_user_assigned_identity.logic_app.id
          },
          {
            name  = "AzureWebJobsStorage__blobServiceUri"
            value = "https://${azapi_resource.storage_account.name}.blob.core.windows.net"
          },
          {
            name  = "AzureWebJobsStorage__queueServiceUri"
            value = "https://${azapi_resource.storage_account.name}.queue.core.windows.net"
          },
          {
            name  = "AzureWebJobsStorage__tableServiceUri"
            value = "https://${azapi_resource.storage_account.name}.table.core.windows.net"
          },
          {
            name  = "AzureWebJobsStorage__credential"
            value = "managedIdentity"
          },
          {
            name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
            value = azurerm_application_insights.main.instrumentation_key
          },
          {
            name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
            value = azurerm_application_insights.main.connection_string
          },
          {
            name  = "APP_KIND"
            value = "workflowApp"
          },
          {
            name  = "serviceBus_fullyQualifiedNamespace"
            value = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
          },
          {
            name  = "AzureBlob_blobStorageEndpoint"
            value = "https://${azapi_resource.storage_account.name}.blob.core.windows.net"
          }
        ]
        minimumElasticInstanceCount = 1
        use32BitWorkerProcess       = false
      }
    }
  }

  identity {
    type = "SystemAssigned, UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.logic_app.id
    ]
  }
}

# Logic App connection to Azure AI Document Intelligence
resource "azapi_resource" "logic_app_connection_document_intelligence" {
  type      = "Microsoft.Web/connections@2018-07-01-preview"
  name      = "document-intelligence-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "V2"
    properties = {
      displayName           = "document-intelligence"
      customParameterValues = {}
      parameterValues = {
        siteUrl = azurerm_cognitive_account.document_intelligence.endpoint
        api_key = azurerm_cognitive_account.document_intelligence.primary_access_key
      }
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${var.location}/managedApis/formrecognizer"
      }
    }
  }

  schema_validation_enabled = false
}

# Logic App connection to Azure OpenAI
resource "azapi_resource" "logic_app_connection_openai" {
  type      = "Microsoft.Web/connections@2018-07-01-preview"
  name      = "openai-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "V2"
    properties = {
      displayName           = "openai"
      customParameterValues = {}
      parameterValueSet = {
        name = "managedIdentityAuth"
        values = {
          azureOpenAIResourceName = {
            value = azapi_resource.ai_foundry.name
          }
        }
      }
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${var.location}/managedApis/azureopenai"
      }
    }
  }

  schema_validation_enabled = false
}

# Logic App connection to Azure AI Foundry Agent Service
resource "azapi_resource" "logic_app_connection_foundry_agent" {
  type      = "Microsoft.Web/connections@2018-07-01-preview"
  name      = "foundry-agent-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "V2"
    properties = {
      displayName           = "foundry-agent"
      customParameterValues = {}
      parameterValueSet = {
        name = "managedIdentityAuth"
        values = {
          azureAgentAIResourceName = {
            value = "https://${azapi_resource.ai_foundry.name}.services.ai.azure.com/api/projects/${azapi_resource.ai_project.name}"
          }
        }
      }
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${var.location}/managedApis/azureagentservice"
      }
    }
  }

  schema_validation_enabled = false
}

# Logic App connection to Microsoft Teams
resource "azapi_resource" "logic_app_connection_teams" {
  type      = "Microsoft.Web/connections@2018-07-01-preview"
  name      = "teams-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "V2"
    properties = {
      displayName = var.operator_user_name
      authenticatedUser = {
        name = var.operator_user_name
      }
      parameterValues       = {}
      customParameterValues = {}
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${var.location}/managedApis/teams"
      }
    }
  }

  schema_validation_enabled = false
}

# Logic App connection to Office 365 Outlook
resource "azapi_resource" "logic_app_connection_office365" {
  type      = "Microsoft.Web/connections@2018-07-01-preview"
  name      = "office365-${local.prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "V2"
    properties = {
      displayName = var.operator_user_name
      authenticatedUser = {
        name = var.operator_user_name
      }
      parameterValues       = {}
      customParameterValues = {}
      api = {
        id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Web/locations/${var.location}/managedApis/office365"
      }
    }
  }

  schema_validation_enabled = false
}


