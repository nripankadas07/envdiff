"""Core parsing and diff logic for envdiff."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


class EnvParseError(ValueError):
    """Raised when a .env source contains an unparseable line."""


@dataclass(frozen=True)
class EnvDiff:
    """Structured diff between two .env mappings.

    Attributes:
        missing_in_right: keys present in left but absent in right.
        missing_in_left:  keys present in right but absent in left.
        changed:          keys present in both with differing values,
                          mapped to a (left_value, right_value) tuple.
        unchanged:        keys present in both with identical values.
    """

    missing_in_right: tuple[str, ...] = field(default_factory=tuple)
    missing_in_left: tuple[str, ...] = field(default_factory=tuple)
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)
    unchanged: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """True when there are no missing or changed keys."""
        return not (self.missing_in_right or self.missing_in_left or self.changed)


_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'"}


def _strip_inline_comment(value: str) -> str:
    """Strip an unquoted trailing ` # comment` from a raw value."""
    out: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(value):
        char = value[i]
        if quote is None and char == "#" and (not out or out[-1] in (" ", "\t")):
            break
        if quote is None and char in ('"', "'"):
            quote = char
        elif char == quote:
            quote = None
        out.append(char)
        i += 1
    return "".join(out).rstrip()


def _unquote(value: str) -> str:
    """Remove surrounding quotes from value and apply escapes if double-quoted."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        body = value[1:-1]
        if value[0] == "'":
            return body
        result: list[str] = []
        i = 0
        while i < len(body):
            char = body[i]
            if char == "\\" and i + 1 < len(body) and body[i + 1] in _ESCAPES:
                result.append(_ESCAPES[body[i + 1]])
                i += 2
                continue
            result.append(char)
            i += 1
        return "".join(result)
    return value


def _parse_line(raw: str, line_no: int) -> tuple[str, str] | None:
    """Parse a single .env line into (key, value), or None if blank/comment."""
    line = raw.lstrip("\ufeff").strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].lstrip()
    if "=" not in line:
        raise EnvParseError(f"line {line_no}: missing '=' in {raw!r}")
    key, _, rest = line.partition("=")
    key = key.strip()
    if not key or not all(ch.isalnum() or ch == "_" for ch in key):
        raise EnvParseError(f"line {line_no}: invalid key {key!r}")
    return key, _unquote(_strip_inline_comment(rest.strip()))


def parse_env(text: str) -> dict[str, str]:
    """Parse .env text into a dict. Later definitions override earlier ones."""
    if not isinstance(text, str):
        raise TypeError("parse_env expects str input")
    result: dict[str, str] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        parsed = _parse_line(raw, line_no)
        if parsed is not None:
            result[parsed[0]] = parsed[1]
    return result


def parse_env_file(path: str | Path) -> dict[str, str]:
    """Parse a .env file from disk."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"no such .env file: {file_path}")
    return parse_env(file_path.read_text(encoding="utf-8"))


def diff_envs(left: Mapping[str, str], right: Mapping[str, str]) -> EnvDiff:
    """Compute a structured drift report between two env mappings."""
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        raise TypeError("diff_envs expects Mapping inputs")
    left_keys = set(left)
    right_keys = set(right)
    common = left_keys & right_keys
    changed = {k: (left[k], right[k]) for k in sorted(common) if left[k] != right[k]}
    unchanged = tuple(sorted(k for k in common if left[k] == right[k]))
    return EnvDiff(
        missing_in_right=tuple(sorted(left_keys - right_keys)),
        missing_in_left=tuple(sorted(right_keys - left_keys)),
        changed=changed,
        unchanged=unchanged,
    )


def _color(text: str, code: str, enabled: bool) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if enabled else text


def format_diff(diff: EnvDiff, *, color: bool = False) -> str:
    """Render an EnvDiff as a human-readable multi-line string."""
    if not isinstance(diff, EnvDiff):
        raise TypeError("format_diff expects an EnvDiff instance")
    if diff.is_empty:
        return _color("No drift detected.", "32", color)
    lines: list[str] = []
    for key in diff.missing_in_right:
        lines.append(_color(f"- {key}  (only in left)", "31", color))
    for key in diff.missing_in_left:
        lines.append(_color(f"+ {key}  (only in right)", "32", color))
    for key, (lv, rv) in diff.changed.items():
        lines.append(_color(f"~ {key}: {lv!r} -> {rv!r}", "33", color))
    return "\n".join(lines)
