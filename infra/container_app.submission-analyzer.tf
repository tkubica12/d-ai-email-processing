resource "azapi_resource" "submission_analyzer" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "submission-analyzer-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    identity = {
      type = "UserAssigned"
      userAssignedIdentities = {
        "${azurerm_user_assigned_identity.submission_analyzer.id}" = {}
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
            name  = "submission-analyzer"
            image = "ghcr.io/${var.github_repository}/submission-analyzer:latest"
            resources = {
              cpu    = 1.0  # More CPU for AI processing
              memory = "2Gi" # More memory for AI processing
            }
            env = [
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.submission_analyzer.client_id
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
                name  = "AZURE_STORAGE_ACCOUNT_NAME"
                value = azapi_resource.storage_account.name
              },
              {
                name  = "AZURE_TABLE_STORAGE_ENABLED"
                value = "false"
              },
              {
                name  = "AZURE_TABLE_STORAGE_TABLE_NAME"
                value = "continuationtokens"
              },
              {
                name  = "AZURE_FOUNDRY_PROJECT_ENDPOINT"
                value = "https://${azapi_resource.ai_foundry.name}.services.ai.azure.com/api/projects/${azapi_resource.ai_project.name}"
              },
              {
                name  = "AZURE_OPENAI_MODEL"
                value = "gpt-4.1"
              },
              {
                name  = "BING_CONNECTION_ID"
                value = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.main.name}/providers/Microsoft.CognitiveServices/accounts/${azapi_resource.ai_foundry.name}/projects/${azapi_resource.ai_project.name}/connections/bing-grounding-connection"
              },
              {
                name  = "COMPANY_API_BASE_URL"
                value = "https://company-apis-${random_string.suffix.result}.${azurerm_container_app_environment.main.default_domain}"
              },
              {
                name  = "COMPANY_API_AUDIENCE"
                value = "fake-audience"
              },
              {
                name  = "AZURE_SEARCH_SERVICE_NAME"
                value = azurerm_search_service.main.name
              },
              {
                name  = "AZURE_SEARCH_INDEX_NAME"
                value = "documents-index"
              },
              {
                name  = "AZURE_SEARCH_CONNECTION_ID"
                value = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.main.name}/providers/Microsoft.CognitiveServices/accounts/${azapi_resource.ai_foundry.name}/projects/${azapi_resource.ai_project.name}/connections/ai-search-connection"
              },
              {
                name  = "LOG_LEVEL"
                value = "WARNING"
              },
              {
                name  = "PRETTY_PRINT"
                value = "true"
              },
              {
                name  = "AZURE_SERVICE_BUS_FQDN"
                value = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
              },
              {
                name  = "AZURE_SERVICE_BUS_TOPIC_NAME"
                value = azurerm_servicebus_topic.processed_submissions.name
              }
            ]
          }
        ]
      }
    }
  }
}
