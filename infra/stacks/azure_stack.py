"""
Azure Stack skeleton for CDKTF.

Use this stack to compose modular constructs from infra/modules/*.
"""

from dataclasses import asdict
from typing import Any, Dict

from infra.types import AzureInfrastructureConfig


def build_stack_config() -> AzureInfrastructureConfig:
    """Return a strongly-typed default config to bootstrap development."""
    # Populate with meaningful values during implementation.
    raise NotImplementedError("Provide AzureInfrastructureConfig with your environment settings")


def synth_config_json(config: AzureInfrastructureConfig) -> Dict[str, Any]:
    """Convert dataclasses to plain dict for diagnostics or outputs."""
    return asdict(config)


# Placeholder: Add CDKTF App/Stack classes when implementing real resources.
