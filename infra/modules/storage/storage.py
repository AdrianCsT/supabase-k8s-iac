"""
Storage module for Azure Blob Storage with private endpoint for Supabase integration.

Provisions Storage Account, Container, Management Policy, Private Endpoint, and Private DNS Zone.
"""

from constructs import Construct

from cdktf import TerraformOutput
from cdktf_cdktf_provider_azurerm.storage_account import StorageAccount
from cdktf_cdktf_provider_azurerm.storage_container import StorageContainer
from cdktf_cdktf_provider_azurerm.storage_management_policy import (
    StorageManagementPolicy,
    StorageManagementPolicyRule,
    StorageManagementPolicyRuleActions,
    StorageManagementPolicyRuleActionsBaseBlob,
    StorageManagementPolicyRuleFilters,
)
from cdktf_cdktf_provider_azurerm.private_endpoint import PrivateEndpoint
from cdktf_cdktf_provider_azurerm.private_dns_zone import PrivateDnsZone
from cdktf_cdktf_provider_azurerm.private_dns_zone_virtual_network_link import (
    PrivateDnsZoneVirtualNetworkLink,
)
from iac_types import BlobStorageConfig


def provision_storage(
    scope: Construct,
    config: BlobStorageConfig,
    rg_name: str,
    location: str,
    vnet,
    subnet_aks,
) -> StorageAccount:
    """Provision storage resources with private connectivity."""
    # Parse performance_tier to tier and replication
    if config.performance_tier == "Standard_LRS":
        account_tier = "Standard"
        account_replication_type = "LRS"
    else:
        # Default or extend for other tiers if needed
        account_tier = "Standard"
        account_replication_type = config.replication_type.upper()

    # Storage Account with network rules restricting to VNet, versioning, soft-delete
    storage_account = StorageAccount(
        scope,
        "storageAccount",
        name=config.account_name,
        resource_group_name=rg_name,
        location=location,
        account_kind="StorageV2",
        account_tier=account_tier,
        account_replication_type=account_replication_type,
        access_tier=config.access_tier,
        https_traffic_only_enabled=True,
        min_tls_version="TLS1_2",
        shared_access_key_enabled=True,
        public_network_access_enabled=False,
        allow_nested_items_to_be_public=False,
        network_rules={
            "default_action": "Deny",
            "bypass": ["AzureServices"],
            "virtual_network_subnet_ids": [subnet_aks.id],
        },
        blob_properties={
            "versioning_enabled": config.enable_versioning,
            "delete_retention_policy": {
                "days": config.soft_delete_days,
            },
            "change_feed_enabled": True,  # Recommended for versioning
        },
        static_website=(
            {
                "index_document": "index.html",
                "error_404_document": "error.html",
            }
            if config.enable_static_website
            else None
        ),
        tags={"Environment": "Supabase"},
    )

    # Storage Container for Supabase

    container = StorageContainer(
        scope,
        "storageContainer",
        name=config.container_name,
        storage_account_id=storage_account.id,
        container_access_type="private",
    )

    if config.enable_versioning:
        # Create a simple management policy with base blob delete rule using typed objects
        # Ensures proper CDKTF -> Terraform JSON mapping for nested actions
        StorageManagementPolicy(
            scope,
            "storageManagementPolicy",
            storage_account_id=storage_account.id,
            rule=[
                StorageManagementPolicyRule(
                    name="DefaultRule",
                    enabled=True,
                    filters=StorageManagementPolicyRuleFilters(
                        blob_types=["blockBlob"],
                    ),
                    actions=StorageManagementPolicyRuleActions(
                        base_blob=StorageManagementPolicyRuleActionsBaseBlob(
                            delete_after_days_since_modification_greater_than=365,
                        ),
                    ),
                )
            ],
        )

    # Private DNS Zone for blob
    pdns_zone = PrivateDnsZone(
        scope,
        "pdnsZoneBlob",
        name="privatelink.blob.core.windows.net",
        resource_group_name=rg_name,
    )

    # Link VNet to Private DNS Zone
    PrivateDnsZoneVirtualNetworkLink(
        scope,
        "pdnsVnetLinkBlob",
        name=f"{config.account_name}-blob-link",
        resource_group_name=rg_name,
        private_dns_zone_name=pdns_zone.name,
        virtual_network_id=vnet.id,
        registration_enabled=False,
    )

    # Private Endpoint for Blob service
    private_endpoint = PrivateEndpoint(
        scope,
        "privateEndpointBlob",
        name=f"{config.account_name}-blob-pe",
        resource_group_name=rg_name,
        location=location,
        subnet_id=subnet_aks.id,
        private_service_connection={
            "name": "blob-connection",
            "private_connection_resource_id": storage_account.id,
            "is_manual_connection": False,
            "subresource_names": ["blob"],
        },
        private_dns_zone_group={
            "name": "blob-dns-group",
            "private_dns_zone_ids": [pdns_zone.id],
        },
    )

    # Output the storage account for main stack
    TerraformOutput(scope, "storage_account_name_output", value=storage_account.name)
    TerraformOutput(
        scope,
        "storage_blob_endpoint_output",
        value=storage_account.primary_blob_endpoint,
    )

    return storage_account
