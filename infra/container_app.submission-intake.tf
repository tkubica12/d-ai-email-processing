resource "azapi_resource" "submission_intake" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "submission-intake-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    identity = {
      type = "UserAssigned"
      userAssignedIdentities = {
        "${azurerm_user_assigned_identity.submission_intake.id}" = {}
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
          minReplicas    = 1  # Keep at least 1 replica for message processing
          maxReplicas    = 5
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
            name  = "submission-intake"
            image = "ghcr.io/${var.github_repository}/submission-intake:latest"
            resources = {
              cpu    = 0.5
              memory = "1Gi"
            }
            env = [
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.submission_intake.client_id
              },
              {
                name  = "AZURE_SERVICE_BUS_FQDN"
                value = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
              },
              {
                name  = "AZURE_SERVICE_BUS_TOPIC_NAME"
                value = azurerm_servicebus_topic.new_submissions.name
              },
              {
                name  = "AZURE_SERVICE_BUS_SUBSCRIPTION_NAME"
                value = azurerm_servicebus_subscription.submission_intake.name
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
                name  = "AZURE_COSMOS_DB_SUBMISSIONS_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.submissions.name
              },
              {
                name  = "AZURE_COSMOS_DB_DOCUMENTS_CONTAINER_NAME"
                value = azurerm_cosmosdb_sql_container.documents.name
              },
              {
                name  = "AZURE_STORAGE_ACCOUNT_NAME"
                value = azapi_resource.storage_account.name
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
                value = "submission-intake"
              }
            ]
          }
        ]
      }
    }
  }
  response_export_values = ["*"]
}
