"""
Network module.

Creates RG, VNet, subnets (public/aks/db), NSGs, NAT, and route tables.
"""

from __future__ import annotations

from typing import Tuple

from constructs import Construct

from cdktf import TerraformOutput
from cdktf_cdktf_provider_azurerm.resource_group import ResourceGroup
from cdktf_cdktf_provider_azurerm.virtual_network import VirtualNetwork
from cdktf_cdktf_provider_azurerm.subnet import (
    Subnet,
    SubnetDelegation,
    SubnetDelegationServiceDelegation,
)
from cdktf_cdktf_provider_azurerm.network_security_group import NetworkSecurityGroup
from cdktf_cdktf_provider_azurerm.network_security_rule import NetworkSecurityRule
from cdktf_cdktf_provider_azurerm.public_ip import PublicIp
from cdktf_cdktf_provider_azurerm.nat_gateway import NatGateway
from cdktf_cdktf_provider_azurerm.nat_gateway_public_ip_association import (
    NatGatewayPublicIpAssociation,
)
from cdktf_cdktf_provider_azurerm.subnet_nat_gateway_association import (
    SubnetNatGatewayAssociation,
)
from cdktf_cdktf_provider_azurerm.route_table import RouteTable, RouteTableRoute
from cdktf_cdktf_provider_azurerm.subnet_route_table_association import (
    SubnetRouteTableAssociation,
)
from cdktf_cdktf_provider_azurerm.subnet_network_security_group_association import (
    SubnetNetworkSecurityGroupAssociation,
)

from iac_types import AzureInfrastructureConfig


def _base_prefix_from_rg(rg_name: str) -> str:
    return rg_name[:-3] if rg_name.endswith("-rg") else rg_name


def provision_network(
    *, scope: Construct, cfg: AzureInfrastructureConfig
) -> Tuple[ResourceGroup, VirtualNetwork, Subnet, Subnet, Subnet, NatGateway]:
    """Provision networking and return (rg, vnet, subnet_public, subnet_aks, subnet_db, nat)."""
    rg = ResourceGroup(scope, "rg", name=cfg.resource_group_name, location=cfg.location)

    vnet = VirtualNetwork(
        scope,
        "vnet",
        name=cfg.vnet_config.name,
        location=cfg.location,
        resource_group_name=rg.name,
        address_space=cfg.vnet_config.address_space,
    )

    nsg_public = NetworkSecurityGroup(
        scope,
        "nsgPublic",
        name=cfg.vnet_config.network_security_groups["public"].name,
        location=cfg.location,
        resource_group_name=rg.name,
    )

    nsg_private = NetworkSecurityGroup(
        scope,
        "nsgPrivate",
        name=cfg.vnet_config.network_security_groups["private"].name,
        location=cfg.location,
        resource_group_name=rg.name,
    )

    NetworkSecurityRule(
        scope,
        "nsgPrivateAllowAzureLb",
        name=f"{cfg.vnet_config.network_security_groups['private'].name}-allow-azlb",
        priority=100,
        direction="Inbound",
        access="Allow",
        protocol="Tcp",
        source_port_range="*",
        destination_port_range="*",
        source_address_prefix="AzureLoadBalancer",
        destination_address_prefix="*",
        resource_group_name=rg.name,
        network_security_group_name=nsg_private.name,
    )

    subnet_public = Subnet(
        scope,
        "subnetPublic",
        name=cfg.vnet_config.subnets["public"].name,
        resource_group_name=rg.name,
        virtual_network_name=vnet.name,
        address_prefixes=[cfg.vnet_config.subnets["public"].address_prefix],
        depends_on=[vnet],
    )

    subnet_aks = Subnet(
        scope,
        "subnetAks",
        name=cfg.vnet_config.subnets["aks"].name,
        resource_group_name=rg.name,
        virtual_network_name=vnet.name,
        address_prefixes=[cfg.vnet_config.subnets["aks"].address_prefix],
        service_endpoints=["Microsoft.Storage"],
        private_endpoint_network_policies="Disabled",
        depends_on=[vnet],
    )

    subnet_db = Subnet(
        scope,
        "subnetDb",
        name=cfg.vnet_config.subnets["db"].name,
        resource_group_name=rg.name,
        virtual_network_name=vnet.name,
        address_prefixes=[cfg.vnet_config.subnets["db"].address_prefix],
        private_endpoint_network_policies="Disabled",
        delegation=[
            SubnetDelegation(
                name="pgsql-flexible",
                service_delegation=SubnetDelegationServiceDelegation(
                    name="Microsoft.DBforPostgreSQL/flexibleServers",
                    actions=["Microsoft.Network/virtualNetworks/subnets/join/action"],
                ),
            )
        ],
        depends_on=[vnet],
    )

    SubnetNetworkSecurityGroupAssociation(
        scope, "subnetPublicNsgAssoc", subnet_id=subnet_public.id, network_security_group_id=nsg_public.id
    )
    SubnetNetworkSecurityGroupAssociation(
        scope, "subnetAksNsgAssoc", subnet_id=subnet_aks.id, network_security_group_id=nsg_private.id
    )
    SubnetNetworkSecurityGroupAssociation(
        scope, "subnetDbNsgAssoc", subnet_id=subnet_db.id, network_security_group_id=nsg_private.id
    )

    base_prefix = _base_prefix_from_rg(cfg.resource_group_name)
    nat_pip = PublicIp(
        scope,
        "natPip",
        name=f"{base_prefix}-nat-pip",
        location=cfg.location,
        resource_group_name=rg.name,
        allocation_method="Static",
        sku="Standard",
    )

    nat = NatGateway(
        scope,
        "nat",
        name=f"{base_prefix}-nat",
        location=cfg.location,
        resource_group_name=rg.name,
        sku_name="Standard",
    )

    NatGatewayPublicIpAssociation(scope, "natPipAssoc", nat_gateway_id=nat.id, public_ip_address_id=nat_pip.id)
    SubnetNatGatewayAssociation(scope, "natAssocAks", subnet_id=subnet_aks.id, nat_gateway_id=nat.id)
    SubnetNatGatewayAssociation(scope, "natAssocDb", subnet_id=subnet_db.id, nat_gateway_id=nat.id)

    rt_private = RouteTable(
        scope,
        "rtPrivate",
        name=f"{base_prefix}-rt-private",
        location=cfg.location,
        resource_group_name=rg.name,
        route=[RouteTableRoute(name="default-internet", address_prefix="0.0.0.0/0", next_hop_type="Internet")],
    )
    SubnetRouteTableAssociation(scope, "rtaAks", subnet_id=subnet_aks.id, route_table_id=rt_private.id)
    SubnetRouteTableAssociation(scope, "rtaDb", subnet_id=subnet_db.id, route_table_id=rt_private.id)

    TerraformOutput(scope, "resource_group", value=rg.name)
    TerraformOutput(scope, "virtual_network", value=vnet.name)

    return rg, vnet, subnet_public, subnet_aks, subnet_db, nat
