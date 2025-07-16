# Required blob containers for Logic App in existing storage account
resource "azapi_resource" "logic_app_blob_container_hosts" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = "azure-webjobs-hosts"
  parent_id = "${azapi_resource.main.id}/blobServices/default"

  body = {
    properties = {
      publicAccess = "None"
    }
  }
}

# resource "azapi_resource" "logic_app_blob_container_secrets" {
#   type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
#   name      = "azure-webjobs-secrets"
#   parent_id = "${azapi_resource.main.id}/blobServices/default"

#   body = {
#     properties = {
#       publicAccess = "None"
#     }
#   }
# }

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
            value = "https://${azurerm_storage_account.main.name}.blob.core.windows.net"
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
            name  = "WEBSITE_SKIP_CONTENTSHARE_VALIDATION"
            value = "1"
          },
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

  #   tags = {
  #     "hidden-link: /app-insights-resource-id" = azurerm_application_insights.main.id
  #   }
}

# # Disable basic publishing credentials for FTP
# resource "azapi_resource" "logic_app_ftp_policy" {
#   type      = "Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01"
#   name      = "ftp"
#   parent_id = azapi_resource.logic_app.id

#   body = {
#     properties = {
#       allow = false
#     }
#   }
# }

# # Disable basic publishing credentials for SCM
# resource "azapi_resource" "logic_app_scm_policy" {
#   type      = "Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01"
#   name      = "scm"
#   parent_id = azapi_resource.logic_app.id

#   body = {
#     properties = {
#       allow = false
#     }
#   }
# }

