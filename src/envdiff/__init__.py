"""envdiff — Compare two .env files and report drift.

Public API:
    parse_env(text)         -> dict[str, str]
        parse_env_file(path)    -> dict[str, str]
            diff_envs(left, right)  -> EnvDiff
                format_diff(diff, ...)  -> str
                """
from .core import (
    EnvDiff,
    EnvParseError,
    diff_envs,
    format_diff,
    parse_env,
    parse_env_file,
)

__all__ = [
      "EnvDiff",
      "EnvParseError",
      "diff_envs",
      "format_diff",
      "parse_env",
      "parse_env_file",
]
__version__ = "0.1.0"
