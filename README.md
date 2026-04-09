# envdiff

Compare two `.env` files and report drift — keys missing on either side and
values that have changed. Pure-Python, zero dependencies, ships with both a
library API and a small CLI.

## Install

```bash
pip install envdiff
```

Or, from a checkout:

```bash
pip install -e .
```

## Usage

### CLI

```bash
envdiff .env.example .env
```

Exit codes:

- `0` — no drift
- - `1` — drift detected
  - - `2` — input error (missing file or parse error)
   
    - Pass `--no-color` to disable ANSI colors in piped output.
   
    - ### Library
   
    - ```python
      from envdiff import diff_envs, format_diff, parse_env_file

      left = parse_env_file(".env.example")
      right = parse_env_file(".env")
      diff = diff_envs(left, right)

      if not diff.is_empty:
          print(format_diff(diff, color=True))
      ```

      ## API

      ### `parse_env(text: str) -> dict[str, str]`

      Parse a `.env` document. Supports comments (`#`), inline comments,
      double-quoted values with `\n`, `\t`, `\r`, `\\`, `\"` escapes, single-quoted
      literal values, the `export` prefix, and a UTF-8 BOM. Later definitions of a
      key override earlier ones. Raises `EnvParseError` on malformed lines or invalid
      keys, and `TypeError` on non-string input.

      ### `parse_env_file(path: str | Path) -> dict[str, str]`

      Read a file from disk and parse it. Raises `FileNotFoundError` if the path
      does not exist.

      ### `diff_envs(left: Mapping[str, str], right: Mapping[str, str]) -> EnvDiff`

      Return an `EnvDiff` describing the keys missing on either side, the keys whose
      values have changed, and the keys that match.

      ### `EnvDiff`

      Frozen dataclass with `missing_in_right`, `missing_in_left`, `changed`,
      `unchanged` fields and an `is_empty` property.

      ### `format_diff(diff: EnvDiff, *, color: bool = False) -> str`

      Render a diff as a human-readable, optionally ANSI-colored string.

      ## Non-goals

      envdiff intentionally does **not** perform shell-style variable interpolation
      (`${OTHER}`), does not write or sync files, and does not modify your
      environment. It is a read-only drift reporter.

      ## Running tests

      ```bash
      pip install pytest pytest-cov
      PYTHONPATH=src pytest --cov=envdiff
      ```

      ## License

      MIT — see `LICENSE`.
      
