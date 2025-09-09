"""
Key Vault module.

Creates Azure Key Vault with RBAC enabled.
"""

from __future__ import annotations

import os
from typing import Tuple

from constructs import Construct

from cdktf_cdktf_provider_azurerm.key_vault import KeyVault

from iac_types import AzureInfrastructureConfig


def provision_key_vault(
    *, scope: Construct, cfg: AzureInfrastructureConfig, rg_name: str, location: str
) -> Tuple[KeyVault, str]:
    """Provision Key Vault and return (vault, tenant_id)."""
    tenant_id = os.getenv("ARM_TENANT_ID")
    if not tenant_id:
        raise ValueError("ARM_TENANT_ID must be set for Key Vault tenant binding")
    kv = KeyVault(
        scope,
        "keyVault",
        name=cfg.key_vault_config.vault_name,
        location=location,
        resource_group_name=rg_name,
        tenant_id=tenant_id,
        sku_name=cfg.key_vault_config.sku,
        soft_delete_retention_days=7,
        purge_protection_enabled=False,
        enabled_for_deployment=cfg.key_vault_config.enabled_for_deployment,
        enabled_for_template_deployment=cfg.key_vault_config.enabled_for_template_deployment,
        rbac_authorization_enabled=True,
        public_network_access_enabled=True,
    )
    return kv, tenant_id
