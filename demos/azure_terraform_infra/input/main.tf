terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "myapp-resources"
  location = "East US"

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
