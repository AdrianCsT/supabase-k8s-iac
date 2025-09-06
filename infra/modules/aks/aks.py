"""
AKS module skeleton.

Provisions private AKS with zonal node pools and cluster autoscaler.
"""

from typing import NoReturn

from infra.types import AKSConfig


def provision_aks(config: AKSConfig) -> NoReturn:
    """Provision AKS resources (placeholder)."""
    raise NotImplementedError("Implement AKS via CDKTF Azurerm provider")
