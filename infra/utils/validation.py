"""
Preflight validation helpers.

Pure, minimal functions to validate required environment variables
and format actionable error messages for users.
"""

from __future__ import annotations

from typing import List, Mapping


def missing_env(env: Mapping[str, str], keys: List[str]) -> List[str]:
    """Return the list of keys missing in the provided environment mapping."""
    return [k for k in keys if not env.get(k)]


def format_missing_env_message(missing: List[str]) -> str:
    """Format a friendly, actionable message for missing env vars (PowerShell)."""
    if not missing:
        return ""
    lines: List[str] = []
    lines.append("Preflight check failed: missing environment variables")
    lines.append("")
    lines.append("Missing:")
    for k in missing:
        lines.append(f"  - {k}")
    lines.append("")
    lines.append("How to set them in PowerShell (current session):")
    for k in missing:
        lines.append(f"  $env:{k} = \"<value>\"")
    lines.append("")
    lines.append("Then re-run: python -m scripts.cli infra-deploy --project-dir infra")
    return "\n".join(lines)

