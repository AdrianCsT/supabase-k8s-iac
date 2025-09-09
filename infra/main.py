"""
CDKTF entrypoint for Azure Supabase infrastructure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Optional
import os
import sys

from constructs import Construct
from cdktf import App, TerraformOutput, TerraformStack

from cdktf_cdktf_provider_azurerm.provider import (
    AzurermProvider,
    AzurermProviderFeatures,
)
from cdktf_cdktf_provider_azurerm.resource_group import ResourceGroup
from cdktf_cdktf_provider_azurerm.key_vault_secret import KeyVaultSecret

from stacks.azure_stack import synth_config_json
from modules.storage.storage import provision_storage
from modules.network.network import provision_network
from modules.aks.aks import provision_aks
from modules.postgres.postgres import provision_postgres
from modules.keyvault.keyvault import provision_key_vault
from iac_types import AzureInfrastructureConfig
from utils.config_loader import load_tfvars_config
from utils.validation import missing_env, format_missing_env_message


def _base_prefix_from_rg(rg_name: str) -> str:
    return rg_name[:-3] if rg_name.endswith("-rg") else rg_name


class AzureSupabaseStack(TerraformStack):
    """TerraformStack that wires Azure resources based on typed config."""

    def __init__(
        self, scope: Construct, id: str, config: AzureInfrastructureConfig
    ) -> None:
        super().__init__(scope, id)

        # Provider
        AzurermProvider(self, "azurerm", features=[{}])

        # Networking
        rg, vnet, _, subnet_aks, subnet_db, _nat = provision_network(
            scope=self, cfg=config
        )

        # Storage
        _storage = provision_storage(
            self, config.storage_config, rg.name, config.location, vnet, subnet_aks
        )

        # AKS
        aks = provision_aks(
            scope=self, cfg=config, rg_name=rg.name, subnet_aks=subnet_aks
        )
        TerraformOutput(self, "aks_name", value=aks.name)

        # PostgreSQL
        _pg = provision_postgres(
            scope=self,
            cfg=config,
            rg_name=rg.name,
            location=config.location,
            subnet_db=subnet_db,
            vnet=vnet,
        )
        TerraformOutput(self, "postgres_server", value=_pg.name)

        # Key Vault
        _kv, tenant_id = provision_key_vault(
            scope=self, cfg=config, rg_name=rg.name, location=config.location
        )
        TerraformOutput(self, "key_vault_name", value=_kv.name)

        # Add S3 credentials to Key Vault if environment variables are set
        import os

        s3_access_key = os.getenv("S3_ACCESS_KEY_ID")
        s3_secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
        if s3_access_key and s3_secret_key:
            KeyVaultSecret(
                self,
                "s3-access-key",
                key_vault_id=_kv.id,
                name="supabase-s3-access-key",
                value=s3_access_key,
            )
            KeyVaultSecret(
                self,
                "s3-secret-key",
                key_vault_id=_kv.id,
                name="supabase-s3-secret-key",
                value=s3_secret_key,
            )

        # Output tenant_id and subscription_id
        TerraformOutput(self, "tenant_id", value=tenant_id)
        subscription_id = os.getenv("ARM_SUBSCRIPTION_ID")
        if subscription_id:
            TerraformOutput(self, "subscription_id", value=subscription_id)

        # Storage Outputs
        TerraformOutput(self, "storage_account_name", value=_storage.name)
        TerraformOutput(
            self, "storage_blob_endpoint", value=_storage.primary_blob_endpoint
        )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_tfvars_config(repo_root=repo_root)

    # Preflight: ensure required env vars are present before synthesizing
    required_env = ["PG_ADMIN_LOGIN", "PG_ADMIN_PASSWORD"]
    missing = missing_env(env=os.environ, keys=required_env)
    if missing:
        msg = format_missing_env_message(missing)
        print(msg, file=sys.stderr)
        sys.exit(2)

    app = App()
    try:
        AzureSupabaseStack(app, "azure-supabase", cfg)
    except ValueError as ex:
        # Surface a concise, friendly message instead of a long traceback
        print(f"Error: {ex}", file=sys.stderr)
        sys.exit(1)

    # Surface a copy of the config used for traceability
    _cfg_json = synth_config_json(cfg)
    TerraformOutput(
        app.node.try_find_child("azure-supabase"), "config_json", value=str(_cfg_json)
    )

    try:
        app.synth()
    except Exception as ex:  # noqa: BLE001 - present actionable error
        print("Synthesis failed.", file=sys.stderr)
        print(str(ex), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
