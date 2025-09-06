"""
CDKTF entrypoint for Azure Supabase infrastructure.

Note: This is a skeleton aligned with StackAI-TAH. Fill in resource
implementations within modules and wire them in the Azure stack.
"""

from typing import NoReturn


def main() -> NoReturn:
    # Intentionally left minimal to avoid runtime deps in skeleton phase.
    # Implement CDKTF App/Stack wiring here when ready to deploy.
    raise NotImplementedError(
        "CDKTF app not yet wired. Implement stacks in infra/stacks and run via 'cdktf synth/deploy'."
    )


if __name__ == "__main__":
    main()
