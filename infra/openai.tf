resource "azurerm_cognitive_account" "openai" {
  name                          = "openai-${local.prefix}"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.main.name
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = "openai-${local.prefix}"
  public_network_access_enabled = true
}

resource "azurerm_cognitive_deployment" "text_embedding_3_large" {
  name                 = "text-embedding-3-large"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }

  scale {
    type = "GlobalStandard"
    capacity = 100
  }
}

resource "azurerm_cognitive_deployment" "gpt_41" {
  name                 = "gpt-4.1"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14"
  }

  scale {
    type     = "GlobalStandard"
    capacity = 100
  }
}
