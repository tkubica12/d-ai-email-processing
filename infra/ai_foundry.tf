# AI Foundry Hub - replaces the traditional OpenAI account
resource "azapi_resource" "ai_foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = "ai-foundry-${local.prefix}"
  location  = var.location
  parent_id = azurerm_resource_group.main.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = "ai-foundry-${local.prefix}"
      disableLocalAuth       = true
      publicNetworkAccess    = "Enabled"
    }
  }

  schema_validation_enabled = false
}

# AI Project for development teams
resource "azapi_resource" "ai_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = "${local.prefix}-project"
  location  = var.location
  parent_id = azapi_resource.ai_foundry.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      displayName = "AI Email Processing Project"
      description = "AI project for document processing and analysis"
    }
  }

  schema_validation_enabled = false
}

# GPT-4.1 model deployment
resource "azapi_resource" "gpt_41_deployment" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2024-06-01-preview"
  name      = "gpt-4.1"
  parent_id = azapi_resource.ai_foundry.id

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
    properties = {
      model = {
        name   = "gpt-4.1"
        format = "OpenAI"
      }
    }
  }
}

# Text embedding model deployment
resource "azapi_resource" "text_embedding_deployment" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2024-06-01-preview"
  name      = "text-embedding-3-large"
  parent_id = azapi_resource.ai_foundry.id

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
    properties = {
      model = {
        name    = "text-embedding-3-large"
        format  = "OpenAI"
        version = "1"
      }
    }
  }
}
