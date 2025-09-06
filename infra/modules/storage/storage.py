"""
Storage module skeleton.

Creates Storage Account and Blob container with private endpoint.
"""

from typing import NoReturn

from infra.types import BlobStorageConfig


def provision_storage(config: BlobStorageConfig) -> NoReturn:
    """Provision storage resources (placeholder)."""
    raise NotImplementedError("Implement Storage Account via CDKTF Azurerm provider")
