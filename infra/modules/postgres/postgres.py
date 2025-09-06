"""
PostgreSQL Flexible Server module skeleton.

Configures zone-redundant HA, backups, and private endpoint.
"""

from typing import NoReturn

from infra.types import PostgreSQLConfig


def provision_postgres(config: PostgreSQLConfig) -> NoReturn:
    """Provision PostgreSQL resources (placeholder)."""
    raise NotImplementedError("Implement PostgreSQL Flexible Server via CDKTF Azurerm provider")
