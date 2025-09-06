"""
Network module skeleton.

Defines VNet, subnets, NSGs, and NAT Gateway according to VNetConfig.
"""

from typing import NoReturn

from infra.types import VNetConfig


def provision_network(config: VNetConfig) -> NoReturn:
    """Provision network resources (placeholder)."""
    raise NotImplementedError("Implement network resources via CDKTF Azurerm provider")
