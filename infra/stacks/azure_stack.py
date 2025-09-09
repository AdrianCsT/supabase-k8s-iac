"""
Azure stack config helpers.

This module adapts tfvars (loaded elsewhere) into the strongly-typed
AzureInfrastructureConfig used by the CDKTF stack.
"""

from dataclasses import asdict
from typing import Any, Dict

from iac_types import AzureInfrastructureConfig


def build_stack_config(config: AzureInfrastructureConfig) -> AzureInfrastructureConfig:
    """No-op adapter kept for future extensions.

    Keeping this function allows adding validation or defaults in one
    place without touching the CDKTF stack code.
    """
    return config


def synth_config_json(config: AzureInfrastructureConfig) -> Dict[str, Any]:
    """Convert dataclasses to plain dict for diagnostics or outputs."""
    return asdict(config)
