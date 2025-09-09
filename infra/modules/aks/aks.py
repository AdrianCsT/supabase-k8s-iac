"""
AKS module.

Creates a private AKS cluster with a system pool and an optional user pool.
The function is pure with respect to inputs and returns the created cluster.
"""

from __future__ import annotations

from typing import Optional

from constructs import Construct

from cdktf_cdktf_provider_azurerm.kubernetes_cluster import KubernetesCluster
from cdktf_cdktf_provider_azurerm.kubernetes_cluster_node_pool import (
    KubernetesClusterNodePool,
)

from iac_types import AzureInfrastructureConfig


def provision_aks(
    *, scope: Construct, cfg: AzureInfrastructureConfig, rg_name: str, subnet_aks
) -> KubernetesCluster:
    """Provision AKS using settings from cfg and return the cluster."""
    auto_enabled: bool = cfg.aks_config.enable_cluster_autoscaler
    min_count: Optional[int] = max(1, cfg.aks_config.node_count) if auto_enabled else None
    max_count: Optional[int] = (
        max(min_count if min_count is not None else 1, cfg.aks_config.node_count + 2)
        if auto_enabled
        else None
    )

    aks = KubernetesCluster(
        scope,
        "aks",
        name=cfg.aks_config.cluster_name,
        location=cfg.location,
        resource_group_name=rg_name,
        dns_prefix=f"{cfg.aks_config.cluster_name}-dns",
        kubernetes_version=None,
        default_node_pool={
            "name": "system",
            "vm_size": cfg.aks_config.vm_size,
            "node_count": cfg.aks_config.node_count,
            "vnet_subnet_id": subnet_aks.id,
            "type": "VirtualMachineScaleSets",
            "auto_scaling_enabled": auto_enabled,
            **({"min_count": min_count, "max_count": max_count} if auto_enabled else {}),
        },
        identity={"type": "SystemAssigned"},
        private_cluster_enabled=True,
        network_profile={
            "network_plugin": cfg.aks_config.network_plugin,
            "network_policy": cfg.aks_config.network_policy,
            "load_balancer_sku": "standard",
            "service_cidr": "10.96.0.0/16",
            "dns_service_ip": "10.96.0.10",
        },
        role_based_access_control_enabled=True,
    )

    if cfg.aks_config.node_pools and cfg.aks_config.node_pools[0].node_count > 0:
        KubernetesClusterNodePool(
            scope,
            "aksUserPool",
            kubernetes_cluster_id=aks.id,
            name="user",
            vm_size=cfg.aks_config.vm_size,
            node_count=cfg.aks_config.node_pools[0].node_count,
            vnet_subnet_id=subnet_aks.id,
            mode="User",
            orchestrator_version=None,
        )

    return aks
