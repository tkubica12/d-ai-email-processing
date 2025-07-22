resource "azapi_resource" "submission_trigger" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "submission-trigger-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    identity = {
      type = "UserAssigned"
      userAssignedIdentities = {
        "${azurerm_user_assigned_identity.submission_trigger.id}" = {}
      }
    }
    properties = {
      managedEnvironmentId = azurerm_container_app_environment.main.id
      configuration = {
        activeRevisionsMode = "Single"
        # No ingress configuration since this is a background service
      }
      template = {
        scale = {
          minReplicas    = 1  # Keep at least 1 replica for event processing
          maxReplicas    = 3
          rules = [
            {
              name = "cpu-scale-rule"
              custom = {
                type = "cpu"
                metadata = {
                  type = "Utilization"
                  value = "70"
                }
              }
            }
          ]
        }
        containers = [
          {
            name  = "submission-trigger"
            image = "ghcr.io/${var.github_repository}/submission-trigger:latest"
            resources = {
              cpu    = 0.5
              memory = "1Gi"
            }
            env = [
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.submission_trigger.client_id
              },
              {
                name  = "AZURE_COSMOS_DB_ENDPOINT"
                value = azurerm_cosmosdb_account.main.endpoint
              },
              {
                name  = "AZURE_COSMOS_DB_DATABASE_NAME"
                value = azurerm_cosmosdb_sql_database.main.name
              },
              {
                name  = "AZURE_COSMOS_DB_EVENTS_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.events.name
              },
              {
                name  = "AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.documents.name
              },
              {
                name  = "AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.submissions.name
              },
              {
                name  = "AZURE_COSMOS_DB_SUBMISSIONS_TRIGGER_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.submission_trigger.name
              },
              {
                name  = "AZURE_STORAGE_ACCOUNT_NAME"
                value = azapi_resource.storage_account.name
              },
              {
                name  = "AZURE_TABLE_STORAGE_ENABLED"
                value = "true"
              },
              {
                name  = "AZURE_TABLE_STORAGE_TABLE_NAME"
                value = "continuationtokens"
              },
              {
                name  = "LOG_LEVEL"
                value = "INFO"
              }
            ]
          }
        ]
      }
    }
  }
}
