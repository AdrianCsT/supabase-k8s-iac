# Infrastructure (CDK for Terraform - Azure)

This folder contains a code-first IaC setup using CDK for Terraform (Python) targeting Azure. It provisions:
- Virtual Network, subnets, NSGs, NAT Gateway
- AKS (private, zonal, autoscaler)
- PostgreSQL Flexible Server (zone-redundant HA)
- Blob Storage (private endpoint)
- Key Vault (RBAC) for secrets

Structure
- `cdktf.json`: CDKTF app configuration
- `requirements.txt`: Python dependencies for infra
- `main.py`: App entrypoint wiring stacks and modules
- `types.py`: Strongly typed configuration dataclasses
- `stacks/azure_stack.py`: Top-level Azure stack
- `modules/*`: Modular constructs for network, aks, postgres, storage, keyvault

Notes
- Keep logic modular and idempotent.
- Use least privilege for identities.
- Do not commit secrets.
