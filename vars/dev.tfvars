# Environment identity
env = "dev"
location = "centralus"
name_prefix = "supabase"

# Network CIDRs
vnet_cidr = "10.0.0.0/16"
subnet_public_cidr = "10.0.0.0/24"
subnet_aks_cidr = "10.0.1.0/24"
subnet_db_cidr = "10.0.2.0/24"

# AKS
aks_vm_size = "Standard_B2s"
aks_system_node_count = 1
aks_user_node_count = 1

# PostgreSQL
pg_version = "15"
pg_storage_mb = 65536
pg_sku_name = "GP_Standard_D2s_v3"
pg_backup_retention_days = 7
pg_geo_redundant_backup = false
pg_high_availability = "SameZone"

# Storage
storage_account_name = "supabasedevstorage"
storage_container_name = "supabase"
storage_access_tier = "Hot"
storage_replication_type = "LRS"

# Key Vault
kv_sku = "standard"
kv_enabled_for_deployment = false
kv_enabled_for_template_deployment = false

