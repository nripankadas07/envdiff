"""CLI entry point: ``python -m envdiff a.env b.env``."""
from __future__ import annotations

import argparse
import sys

from .core import EnvParseError, diff_envs, format_diff, parse_env_file


def _build_parser() -> argparse.ArgumentParser:
      parser = argparse.ArgumentParser(
                prog="envdiff",
                description="Compare two .env files and report drift.",
      )
      parser.add_argument("left", help="Path to the baseline .env file")
      parser.add_argument("right", help="Path to the compared .env file")
      parser.add_argument(
          "--no-color", action="store_true", help="Disable ANSI color in output"
      )
      return parser


def main(argv: list[str] | None = None) -> int:
      """Run the envdiff CLI. Returns exit code (0 = no drift, 1 = drift, 2 = error)."""
      args = _build_parser().parse_args(argv)
      try:
                left = parse_env_file(args.left)
                right = parse_env_file(args.right)
except (FileNotFoundError, EnvParseError) as exc:
        print(f"envdiff: {exc}", file=sys.stderr)
        return 2
    diff = diff_envs(left, right)
    print(format_diff(diff, color=not args.no_color and sys.stdout.isatty()))
    return 0 if diff.is_empty else 1


if __name__ == "__main__":  # pragma: no cover
      raise SystemExit(main())
  
