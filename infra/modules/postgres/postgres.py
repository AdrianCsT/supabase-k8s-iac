"""
PostgreSQL Flexible Server module.

Creates a private PostgreSQL Flexible Server and links a Private DNS zone.
"""

from __future__ import annotations

import os
from typing import Optional

from constructs import Construct

from cdktf_cdktf_provider_azurerm.postgresql_flexible_server import (
    PostgresqlFlexibleServer,
)
from cdktf_cdktf_provider_azurerm.postgresql_flexible_server_configuration import (
    PostgresqlFlexibleServerConfiguration,
)
from cdktf_cdktf_provider_azurerm.private_dns_zone import PrivateDnsZone
from cdktf_cdktf_provider_azurerm.private_dns_zone_virtual_network_link import (
    PrivateDnsZoneVirtualNetworkLink,
)

from iac_types import AzureInfrastructureConfig


def _base_prefix_from_rg(rg_name: str) -> str:
    return rg_name[:-3] if rg_name.endswith("-rg") else rg_name


def provision_postgres(
    *,
    scope: Construct,
    cfg: AzureInfrastructureConfig,
    rg_name: str,
    location: str,
    subnet_db,
    vnet,
) -> PostgresqlFlexibleServer:
    """Provision PostgreSQL Flexible Server and return the server resource."""
    admin_login: Optional[str] = os.getenv("PG_ADMIN_LOGIN")
    admin_password: Optional[str] = os.getenv("PG_ADMIN_PASSWORD")
    if not admin_login or not admin_password:
        raise ValueError(
            "PG_ADMIN_LOGIN and PG_ADMIN_PASSWORD must be set as environment variables."
        )

    pdns = PrivateDnsZone(
        scope,
        "pdnsPg",
        name="privatelink.postgres.database.azure.com",
        resource_group_name=rg_name,
    )

    PrivateDnsZoneVirtualNetworkLink(
        scope,
        "pdnsVnetLink",
        name=f"{_base_prefix_from_rg(rg_name)}-pdns-link",
        resource_group_name=rg_name,
        private_dns_zone_name=pdns.name,
        virtual_network_id=vnet.id,
        registration_enabled=False,
    )

    pg = PostgresqlFlexibleServer(
        scope,
        "pg",
        name=cfg.postgres_config.server_name,
        location=location,
        resource_group_name=rg_name,
        version=cfg.postgres_config.version,
        storage_mb=cfg.postgres_config.storage_mb,
        sku_name=cfg.postgres_config.sku_name,
        administrator_login=admin_login,
        administrator_password=admin_password,
        backup_retention_days=cfg.postgres_config.backup_retention_days,
        geo_redundant_backup_enabled=cfg.postgres_config.geo_redundant_backup,
        high_availability={"mode": cfg.postgres_config.high_availability},
        delegated_subnet_id=subnet_db.id,
        private_dns_zone_id=pdns.id,
        public_network_access_enabled=False,
        zone="1",
    )

    PostgresqlFlexibleServerConfiguration(
        scope,
        "pgConfigLogConnections",
        name="log_connections",
        server_id=pg.id,
        value="on",
    )

    return pg
