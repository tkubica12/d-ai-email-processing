# Storage Account for email content and attachments
resource "azurerm_storage_account" "main" {
  name                     = "st${local.storage_prefix}email"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  public_network_access_enabled = true
  
  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  tags = {
    environment = local.environment
  }
}
