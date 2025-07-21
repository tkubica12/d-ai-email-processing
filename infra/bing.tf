# Bing Grounding for AI Search enhancement
resource "azapi_resource" "bing_grounding" {
  type      = "Microsoft.Bing/accounts@2020-06-10"
  name      = "bing-grounding-${local.prefix}"
  location  = "global"
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "Bing.Grounding"
    sku = {
      name = "G1"
    }
    properties = {
      statisticsEnabled = false
    }
  }

  schema_validation_enabled = false
}

# Get API keys for the Bing Grounding resource (required for connection)
data "azapi_resource_action" "bing_grounding_keys" {
  type                   = "Microsoft.Bing/accounts@2020-06-10"
  resource_id            = azapi_resource.bing_grounding.id
  action                 = "listKeys"
  response_export_values = ["*"]
}

# Connection from AI Foundry to Bing Grounding using API Key
resource "azapi_resource" "bing_grounding_connection" {
  type      = "Microsoft.CognitiveServices/accounts/connections@2025-06-01"
  name      = "bing-grounding-connection"
  parent_id = azapi_resource.ai_foundry.id

  body = {
    properties = {
      category      = "GroundingWithBingSearch"
      target        = "https://api.bing.microsoft.com/"
      authType      = "ApiKey"
      metadata = {
        ApiType    = "Azure"
        ResourceId = azapi_resource.bing_grounding.id
        type       = "bing_grounding"
      }
      credentials = {
        key = jsondecode(data.azapi_resource_action.bing_grounding_keys.output).key1
      }
    }
  }

  schema_validation_enabled = false
}

# Connection from AI Foundry to AI Search using API Key
resource "azapi_resource" "ai_search_connection" {
  type      = "Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview"
  name      = "ai-search-connection"
  parent_id = azapi_resource.ai_foundry.id

  body = {
    properties = {
      category      = "CognitiveSearch"
      target        = "https://${azurerm_search_service.main.name}.search.windows.net/"
      authType      = "ApiKey"
      metadata = {
        ApiType              = "Azure"
        ApiVersion           = "2024-05-01-preview"
        DeploymentApiVersion = "2023-11-01"
        ResourceId           = azurerm_search_service.main.id
        type                 = "azure_ai_search"
      }
      credentials = {
        key = azurerm_search_service.main.primary_key
      }
    }
  }

  schema_validation_enabled = false
}