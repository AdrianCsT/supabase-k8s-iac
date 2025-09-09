"""
Config loader for tfvars -> typed config used by the CDKTF stack.

Functional, pure helpers that parse a minimal subset of .tfvars syntax
for the variables used by this repo. No external dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from iac_types import (
    AKSConfig,
    AzureInfrastructureConfig,
    BlobStorageConfig,
    KeyVaultConfig,
    NodePoolConfig,
    NSGConfig,
    NSGRule,
    PostgreSQLConfig,
    SubnetConfig,
    VNetConfig,
)


def _strip_quotes(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("')"):
        return value[1:-1]
    return value


def _parse_tfvars(content: str) -> Dict[str, str]:
    """Very small tfvars parser for simple key = value pairs.

    Supports strings, integers, booleans on single lines.
    Lines starting with '#' are ignored.
    """
    vars_map: Dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        # Remove potential trailing comments
        if " #" in val:
            val = val.split(" #", 1)[0].strip()
        vars_map[key] = val
    return vars_map


def _to_bool(value: str) -> bool:
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _to_int(value: str) -> int:
    try:
        return int(value)
    except Exception as ex:  # noqa: BLE001 - rethrow with context
        raise ValueError(f"Invalid int value: {value}") from ex


def _required(vars_map: Dict[str, str], key: str) -> str:
    if key not in vars_map:
        raise KeyError(f"Missing required var: {key}")
    return vars_map[key]


def _build_names(prefix: str, env: str) -> Tuple[str, str, str]:
    rg = f"{prefix}-{env}-rg"
    vnet = f"{prefix}-{env}-vnet"
    aks = f"{prefix}-{env}-aks"
    return rg, vnet, aks


def _build_vnet_config(
    name: str,
    vnet_cidr: str,
    public_cidr: str,
    aks_cidr: str,
    db_cidr: str,
) -> VNetConfig:
    subnets = {
        "public": SubnetConfig(
            name=f"{name}-public",
            address_prefix=public_cidr,
            nsg_name=f"{name}-nsg-public",
        ),
        "aks": SubnetConfig(
            name=f"{name}-aks", address_prefix=aks_cidr, nsg_name=f"{name}-nsg-private"
        ),
        "db": SubnetConfig(
            name=f"{name}-db", address_prefix=db_cidr, nsg_name=f"{name}-nsg-private"
        ),
    }
    # Minimal NSG rules; can be extended per environment needs
    allow_vnet_inbound = NSGRule(
        name="allow-vnet-inbound",
        priority=200,
        direction="Inbound",
        access="Allow",
        protocol="Tcp",
        source="VirtualNetwork",
        destination="VirtualNetwork",
        source_port="*",
        destination_port="*",
    )
    nsgs = {
        "public": NSGConfig(name=f"{name}-nsg-public", rules=[allow_vnet_inbound]),
        "private": NSGConfig(name=f"{name}-nsg-private", rules=[allow_vnet_inbound]),
    }
    return VNetConfig(
        name=name,
        address_space=[vnet_cidr],
        subnets=subnets,
        network_security_groups=nsgs,
    )


def _build_aks_config(aks_name: str, vars_map: Dict[str, str]) -> AKSConfig:
    vm_size = _strip_quotes(_required(vars_map, "aks_vm_size"))
    system_count = _to_int(_required(vars_map, "aks_system_node_count"))
    user_count = _to_int(_required(vars_map, "aks_user_node_count"))
    # System pool count is set at cluster level; user pool defined in node_pools
    return AKSConfig(
        cluster_name=aks_name,
        node_count=system_count,
        vm_size=vm_size,
        node_pools=[
            NodePoolConfig(
                name="user",
                vm_size=vm_size,
                node_count=user_count,
                availability_zones=["1", "2", "3"],
            )
        ],
        network_plugin="azure",
        network_policy="azure",
        availability_zones=["1", "2", "3"],
        enable_cluster_autoscaler=True,
    )


def _build_pg_config(vars_map: Dict[str, str], pg_name: str) -> PostgreSQLConfig:
    return PostgreSQLConfig(
        server_name=pg_name,
        version=_strip_quotes(_required(vars_map, "pg_version")),
        storage_mb=_to_int(_required(vars_map, "pg_storage_mb")),
        sku_name=_strip_quotes(_required(vars_map, "pg_sku_name")),
        backup_retention_days=_to_int(_required(vars_map, "pg_backup_retention_days")),
        geo_redundant_backup=_to_bool(_required(vars_map, "pg_geo_redundant_backup")),
        high_availability=_strip_quotes(_required(vars_map, "pg_high_availability")),
    )


def _build_storage_config(
    vars_map: Dict[str, str], prefix: str, env: str
) -> BlobStorageConfig:
    return BlobStorageConfig(
        account_name=f"{prefix}{env}stg".replace("-", ""),
        container_name=_strip_quotes(_required(vars_map, "storage_container_name")),
        access_tier=_strip_quotes(_required(vars_map, "storage_access_tier")),
        replication_type=_strip_quotes(_required(vars_map, "storage_replication_type")),
    )


def _build_kv_config(vars_map: Dict[str, str], prefix: str, env: str) -> KeyVaultConfig:
    return KeyVaultConfig(
        vault_name=f"{prefix}-{env}-kv",
        sku=_strip_quotes(_required(vars_map, "kv_sku")),
        enabled_for_deployment=_to_bool(
            _required(vars_map, "kv_enabled_for_deployment")
        ),
        enabled_for_template_deployment=_to_bool(
            _required(vars_map, "kv_enabled_for_template_deployment")
        ),
    )



def load_tfvars_config(*, repo_root: Path) -> AzureInfrastructureConfig:
    # Use default if env var is missing or empty
    tfvars_file_env = os.getenv("TFVARS_FILE")
    tfvars_file = (
        tfvars_file_env
        if (tfvars_file_env and tfvars_file_env.strip())
        else "vars/dev.tfvars"
    )
    vars_path = (repo_root / tfvars_file).resolve()
    if not vars_path.exists():
        raise FileNotFoundError(f"tfvars file not found: {vars_path}")

    content = vars_path.read_text(encoding="utf-8")
    vars_map = _parse_tfvars(content)

    env = _strip_quotes(_required(vars_map, "env"))
    location = _strip_quotes(_required(vars_map, "location"))
    prefix = _strip_quotes(_required(vars_map, "name_prefix"))

    rg_name, vnet_name, aks_name = _build_names(prefix, env)

    vnet_cfg = _build_vnet_config(
        name=vnet_name,
        vnet_cidr=_strip_quotes(_required(vars_map, "vnet_cidr")),
        public_cidr=_strip_quotes(_required(vars_map, "subnet_public_cidr")),
        aks_cidr=_strip_quotes(_required(vars_map, "subnet_aks_cidr")),
        db_cidr=_strip_quotes(_required(vars_map, "subnet_db_cidr")),
    )

    aks_cfg = _build_aks_config(aks_name=aks_name, vars_map=vars_map)
    pg_cfg = _build_pg_config(vars_map=vars_map, pg_name=f"{prefix}-{env}-pg")
    stg_cfg = _build_storage_config(vars_map=vars_map, prefix=prefix, env=env)
    kv_cfg = _build_kv_config(vars_map=vars_map, prefix=prefix, env=env)

    return AzureInfrastructureConfig(
        resource_group_name=rg_name,
        location=location,
        vnet_config=vnet_cfg,
        aks_config=aks_cfg,
        postgres_config=pg_cfg,
        storage_config=stg_cfg,
        key_vault_config=kv_cfg,
    )
