env = "prod"
location = "centralus"
name_prefix = "supabase"

# Network CIDRs
vnet_cidr = "10.1.0.0/16"
subnet_public_cidr = "10.1.0.0/24"
subnet_aks_cidr = "10.1.1.0/24"
subnet_db_cidr = "10.1.2.0/24"

# AKS
aks_vm_size = "Standard_D4s_v5"
aks_system_node_count = 3
aks_user_node_count = 3

# PostgreSQL
pg_version = "15"
pg_storage_mb = 131072
pg_sku_name = "GP_Standard_D4s_v5"
pg_backup_retention_days = 7
pg_geo_redundant_backup = true
pg_high_availability = "ZoneRedundant"

# Storage
storage_account_name = "supabaseprodstorage"
storage_container_name = "supabase"
storage_access_tier = "Hot"
storage_replication_type = "ZRS"

# Key Vault
kv_sku = "standard"
kv_enabled_for_deployment = false
kv_enabled_for_template_deployment = false
