resource "azapi_resource" "docproc_search_indexer" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "docproc-search-indexer-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    identity = {
      type = "UserAssigned"
      userAssignedIdentities = {
        "${azurerm_user_assigned_identity.docproc_search_indexer.id}" = {}
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
          minReplicas    = 1  # Keep at least 1 replica for change feed processing
          maxReplicas    = 3  # Limited replicas since change feed processing is stateful
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
            name  = "docproc-search-indexer"
            image = "ghcr.io/${var.github_repository}/docproc-search-indexer:latest"
            resources = {
              cpu    = 0.75
              memory = "1.5Gi"
            }
            env = [
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.docproc_search_indexer.client_id
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
                name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
                value = azurerm_cognitive_account.document_intelligence.endpoint
              },
              {
                name  = "AZURE_STORAGE_ACCOUNT_NAME"
                value = azapi_resource.storage_account.name
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
                name  = "AZURE_OPENAI_ENDPOINT"
                value = azurerm_cognitive_account.openai.endpoint
              },
              {
                name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
                value = azurerm_cognitive_deployment.text_embedding_3_large.name
              },
              {
                name  = "AZURE_OPENAI_API_VERSION"
                value = "2024-06-01"
              },
              {
                name  = "AZURE_OPENAI_EMBEDDING_DIMENSIONS"
                value = "3072"
              },
              {
                name  = "AZURE_OPENAI_CHUNK_SIZE"
                value = "2000"
              },
              {
                name  = "AZURE_OPENAI_CHUNK_OVERLAP"
                value = "200"
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
              },
              {
                name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                value = azurerm_application_insights.main.connection_string
              },
              {
                name  = "OTEL_SERVICE_NAME"
                value = "docproc-search-indexer"
              }
            ]
          }
        ]
      }
    }
  }
  response_export_values = ["*"]
}
