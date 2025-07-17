# Storage Account for email content and attachments
resource "azapi_resource" "storage_account" {
  type      = "Microsoft.Storage/storageAccounts@2023-05-01"
  name      = "st${local.storage_prefix}email"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id

  body = {
    kind = "StorageV2"
    sku = {
      name = "Standard_LRS"
    }
    properties = {
      publicNetworkAccess = "Enabled"
      networkAcls = {
        defaultAction = "Allow"
        bypass        = "AzureServices"
      }
      supportsHttpsTrafficOnly = true
    }
    tags = {
      environment = local.environment
    }
  }
  
  response_export_values = ["*"]
}

