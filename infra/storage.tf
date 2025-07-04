# Storage Account for email content and attachments
resource "azurerm_storage_account" "main" {
  name                     = "st${local.storage_prefix}email"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # Enable blob versioning and soft delete for better data protection
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
  }
}
