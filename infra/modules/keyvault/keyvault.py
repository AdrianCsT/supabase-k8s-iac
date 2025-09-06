"""
Key Vault module skeleton.

Creates Azure Key Vault and configures RBAC for secrets usage.
"""

from typing import NoReturn

from infra.types import KeyVaultConfig


def provision_key_vault(config: KeyVaultConfig) -> NoReturn:
    """Provision Key Vault resources (placeholder)."""
    raise NotImplementedError("Implement Key Vault via CDKTF Azurerm provider")
