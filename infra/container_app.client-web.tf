resource "azapi_resource" "client_web" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-client-web-${local.base_name}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    identity = {
      type = "UserAssigned"
      userAssignedIdentities = {
        "${azurerm_user_assigned_identity.client_web.id}" = {}
      }
    }
    properties = {
      managedEnvironmentId = azurerm_container_app_environment.main.id
      configuration = {
        activeRevisionsMode = "Single"
        ingress = {
          external   = true
          targetPort = 8000
          transport  = "Http"
          traffic = [
            {
              latestRevision = true
              weight         = 100
            }
          ]
        }
      }
      template = {
        scale = {
          minReplicas    = var.container_app_min_replicas
          maxReplicas    = 10
          rules = [
            {
              name = "http-scale-rule"
              http = {
                metadata = {
                  concurrentRequests = "20"
                }
              }
            }
          ]
        }
        containers = [
          {
            name  = "client-web"
            image = "ghcr.io/${var.github_repository}/client-web:latest"
            resources = {
              cpu    = 0.5
              memory = "1Gi"
            }
            env = [
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.client_web.client_id
              },
              {
                name  = "AZURE_STORAGE_ACCOUNT_NAME"
                value = azapi_resource.main.name
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
                name  = "LOG_LEVEL"
                value = "INFO"
              },
              {
                name  = "PORT"
                value = "8000"
              },
              {
                name  = "HOST"
                value = "0.0.0.0"
              },
              {
                name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                value = azurerm_application_insights.main.connection_string
              },
              {
                name  = "OTEL_SERVICE_NAME"
                value = "client-web"
              }
            ]
          }
        ]
      }
    }
  }
  response_export_values = ["*"]
}
