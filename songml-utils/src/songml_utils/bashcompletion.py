"""Generate bash completion script for songml-* commands."""

from __future__ import annotations

import argparse
import os


def load_completion_script() -> str:
    """Load bash completion script from data file.

    Returns:
        Complete bash completion script as string
    """
    script_path = os.path.join(os.path.dirname(__file__), "data", "bash_completion.sh")

    with open(script_path, encoding="utf-8") as f:
        return f.read()


def main() -> None:
    """CLI entry point for songml-bashcompletion command."""
    parser = argparse.ArgumentParser(
        description="Generate bash completion script for all songml-* commands.",
        epilog="""Installation:
  %(prog)s > ~/.config/bash_completion.d/songml
  source ~/.config/bash_completion.d/songml

Or add to ~/.bashrc:
  source ~/.config/bash_completion.d/songml

System-wide installation (requires sudo):
  %(prog)s | sudo tee /etc/bash_completion.d/songml
  # Restart shell or: source /etc/bash_completion.d/songml""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.parse_args()

    # Load and output completion script
    script = load_completion_script()
    print(script)


if __name__ == "__main__":  # pragma: no cover
    main()
