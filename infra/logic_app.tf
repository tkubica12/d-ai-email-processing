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
        #   {
        #     name  = "WEBSITE_SKIP_CONTENTSHARE_VALIDATION"
        #     value = "1"
        #   },
          {
            name  = "APP_KIND"
            value = "workflowApp"
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

