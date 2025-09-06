from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SubnetConfig:
    name: str
    address_prefix: str
    nsg_name: str


@dataclass(frozen=True)
class NSGRule:
    name: str
    priority: int
    direction: str  # Inbound or Outbound
    access: str  # Allow or Deny
    protocol: str  # Tcp/Udp/Asterisk
    source: str
    destination: str
    source_port: str
    destination_port: str


@dataclass(frozen=True)
class NSGConfig:
    name: str
    rules: List[NSGRule]


@dataclass(frozen=True)
class VNetConfig:
    name: str
    address_space: List[str]
    subnets: Dict[str, SubnetConfig]
    network_security_groups: Dict[str, NSGConfig]


@dataclass(frozen=True)
class NodePoolConfig:
    name: str
    vm_size: str
    node_count: int
    availability_zones: List[str]


@dataclass(frozen=True)
class AKSConfig:
    cluster_name: str
    node_count: int
    vm_size: str
    node_pools: List[NodePoolConfig]
    network_plugin: str  # e.g., "azure"
    network_policy: str  # e.g., "azure"
    availability_zones: List[str]
    enable_cluster_autoscaler: bool


@dataclass(frozen=True)
class PostgreSQLConfig:
    server_name: str
    version: str
    storage_mb: int
    sku_name: str
    backup_retention_days: int
    geo_redundant_backup: bool
    high_availability: str  # "ZoneRedundant" or "SameZone"


@dataclass(frozen=True)
class BlobStorageConfig:
    account_name: str
    container_name: str
    access_tier: str  # Hot/Cool/Archive
    replication_type: str  # LRS/ZRS/GRS


@dataclass(frozen=True)
class KeyVaultConfig:
    vault_name: str
    sku: str
    enabled_for_deployment: bool
    enabled_for_template_deployment: bool


@dataclass(frozen=True)
class AzureInfrastructureConfig:
    resource_group_name: str
    location: str
    vnet_config: VNetConfig
    aks_config: AKSConfig
    postgres_config: PostgreSQLConfig
    storage_config: BlobStorageConfig
    key_vault_config: KeyVaultConfig
