"""Test suite for envdiff."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from envdiff import (
    EnvDiff,
    EnvParseError,
    diff_envs,
    format_diff,
    parse_env,
    parse_env_file,
)
from envdiff.__main__ import main


# ---------------------------------------------------------------------------
# parse_env — happy paths
# ---------------------------------------------------------------------------


def test_parse_env_simple_key_value_returns_dict():
    assert parse_env("FOO=bar") == {"FOO": "bar"}


def test_parse_env_multiple_keys_preserves_all():
    text = "A=1\nB=2\nC=3"
    assert parse_env(text) == {"A": "1", "B": "2", "C": "3"}


def test_parse_env_blank_lines_are_ignored():
    assert parse_env("\n\nFOO=bar\n\n") == {"FOO": "bar"}


def test_parse_env_comment_lines_are_ignored():
    assert parse_env("# header\nFOO=bar\n# trailing") == {"FOO": "bar"}


def test_parse_env_strips_inline_comment():
    assert parse_env("FOO=bar # this is a note") == {"FOO": "bar"}


def test_parse_env_inline_hash_inside_quotes_is_kept():
    assert parse_env('FOO="bar # not a comment"') == {"FOO": "bar # not a comment"}


def test_parse_env_double_quoted_value_is_unquoted():
    assert parse_env('FOO="bar baz"') == {"FOO": "bar baz"}


def test_parse_env_single_quoted_value_is_unquoted_literally():
    assert parse_env("FOO='bar\\nbaz'") == {"FOO": "bar\\nbaz"}


def test_parse_env_double_quoted_escapes_are_processed():
    assert parse_env('FOO="line1\\nline2\\tend"') == {"FOO": "line1\nline2\tend"}


def test_parse_env_export_prefix_is_stripped():
    assert parse_env("export FOO=bar") == {"FOO": "bar"}


def test_parse_env_empty_value_is_empty_string():
    assert parse_env("FOO=") == {"FOO": ""}


def test_parse_env_duplicate_key_last_definition_wins():
    assert parse_env("FOO=1\nFOO=2") == {"FOO": "2"}


def test_parse_env_handles_utf8_bom_on_first_line():
    assert parse_env("\ufeffFOO=bar") == {"FOO": "bar"}


def test_parse_env_keeps_underscores_and_digits_in_keys():
    assert parse_env("API_KEY_2=xyz") == {"API_KEY_2": "xyz"}


# ---------------------------------------------------------------------------
# parse_env — error paths
# ---------------------------------------------------------------------------


def test_parse_env_missing_equals_raises():
    with pytest.raises(EnvParseError, match="missing '='"):
        parse_env("FOO_BAR")


def test_parse_env_invalid_key_raises():
    with pytest.raises(EnvParseError, match="invalid key"):
        parse_env("FOO-BAR=baz")


def test_parse_env_empty_key_raises():
    with pytest.raises(EnvParseError, match="invalid key"):
        parse_env("=value")


def test_parse_env_non_string_input_raises_type_error():
    with pytest.raises(TypeError):
        parse_env(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# parse_env_file
# ---------------------------------------------------------------------------


def test_parse_env_file_reads_disk(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\nBAR=baz\n", encoding="utf-8")
    assert parse_env_file(env_file) == {"FOO": "bar", "BAR": "baz"}


def test_parse_env_file_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_env_file("/no/such/file.env")


# ---------------------------------------------------------------------------
# diff_envs
# ---------------------------------------------------------------------------


def test_diff_envs_identical_inputs_have_empty_drift():
    diff = diff_envs({"A": "1"}, {"A": "1"})
    assert diff.is_empty
    assert diff.unchanged == ("A",)


def test_diff_envs_detects_missing_in_right():
    diff = diff_envs({"A": "1", "B": "2"}, {"A": "1"})
    assert diff.missing_in_right == ("B",)
    assert diff.missing_in_left == ()
    assert not diff.is_empty


def test_diff_envs_detects_missing_in_left():
    diff = diff_envs({"A": "1"}, {"A": "1", "C": "3"})
    assert diff.missing_in_left == ("C",)
    assert diff.missing_in_right == ()


def test_diff_envs_detects_changed_values():
    diff = diff_envs({"A": "1"}, {"A": "2"})
    assert diff.changed == {"A": ("1", "2")}
    assert not diff.is_empty


def test_diff_envs_returns_sorted_keys():
    diff = diff_envs({"Z": "1", "A": "2"}, {"M": "3"})
    assert diff.missing_in_right == ("A", "Z")


def test_diff_envs_rejects_non_mapping_input():
    with pytest.raises(TypeError):
        diff_envs(["A=1"], {})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# format_diff
# ---------------------------------------------------------------------------


def test_format_diff_empty_returns_no_drift_message():
    out = format_diff(EnvDiff())
    assert "No drift" in out


def test_format_diff_includes_all_categories():
    diff = diff_envs({"A": "1", "B": "2"}, {"B": "9", "C": "3"})
    out = format_diff(diff)
    assert "- A" in out
    assert "+ C" in out
    assert "~ B" in out


def test_format_diff_with_color_emits_ansi_codes():
    diff = diff_envs({"A": "1"}, {})
    out = format_diff(diff, color=True)
    assert "\x1b[" in out


def test_format_diff_without_color_has_no_ansi():
    diff = diff_envs({"A": "1"}, {})
    assert "\x1b[" not in format_diff(diff, color=False)


def test_format_diff_rejects_non_envdiff_input():
    with pytest.raises(TypeError):
        format_diff("not a diff")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_cli_returns_zero_when_files_match(tmp_path, capsys):
    a = _write(tmp_path, "a.env", "FOO=bar")
    b = _write(tmp_path, "b.env", "FOO=bar")
    code = main([str(a), str(b), "--no-color"])
    assert code == 0
    assert "No drift" in capsys.readouterr().out


def test_cli_returns_one_when_drift_present(tmp_path, capsys):
    a = _write(tmp_path, "a.env", "FOO=1")
    b = _write(tmp_path, "b.env", "FOO=2")
    code = main([str(a), str(b), "--no-color"])
    assert code == 1
    assert "~ FOO" in capsys.readouterr().out


def test_cli_returns_two_on_missing_file(tmp_path, capsys):
    a = _write(tmp_path, "a.env", "FOO=1")
    code = main([str(a), str(tmp_path / "missing.env"), "--no-color"])
    assert code == 2
    assert "envdiff:" in capsys.readouterr().err


def test_cli_returns_two_on_parse_error(tmp_path, capsys):
    a = _write(tmp_path, "a.env", "FOO=1")
    bad = _write(tmp_path, "bad.env", "not-an-env-line")
    code = main([str(a), str(bad), "--no-color"])
    assert code == 2
