#!/usr/bin/env python3
"""Generate all Day 032 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_032"

_cid = 0


def cid():
    global _cid
    _cid += 1
    return f"c{_cid:04d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cid(),
        "metadata": {},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "ai-course",
                "language": "python",
                "name": "ai-course",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

PARSE_DOTENV_IMPL = """\
def parse_dotenv(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key   = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result"""

MASK_SECRET_IMPL = """\
def mask_secret(value, show_chars: int = 4) -> str:
    s = str(value)
    if len(s) <= show_chars:
        return "***"
    return s[:show_chars] + "***" """

VALIDATE_CONFIG_IMPL = """\
def validate_config(config: dict, required_keys: list) -> list:
    return [k for k in required_keys if config.get(k) is None]"""

SAFE_LOG_CONFIG_IMPL = """\
def safe_log_config(config: dict, secret_keys: list) -> dict:
    return {
        k: mask_secret(str(v)) if k in secret_keys else v
        for k, v in config.items()
    }"""

SECURE_CONFIG_IMPL = """\
class SecureConfig:
    def __init__(self, defaults: dict | None = None):
        self._config: dict = dict(defaults or {})

    def load_dict(self, mapping: dict) -> "SecureConfig":
        self._config.update(mapping)
        return self

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def require(self, key: str) -> str:
        val = self._config.get(key)
        if val is None:
            raise KeyError(f"Required config key not found: '{key}'")
        return str(val)

    def validate(self, required_keys: list) -> list:
        return validate_config(self._config, required_keys)

    def masked_dict(self, secret_keys: list) -> dict:
        return safe_log_config(self._config, secret_keys)"""

ALL_IMPLS = "\n\n\n".join([
    PARSE_DOTENV_IMPL,
    MASK_SECRET_IMPL,
    VALIDATE_CONFIG_IMPL,
    SAFE_LOG_CONFIG_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — parse_dotenv
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 032 — Exercise 1: parse_dotenv\n\n"
            "**What you'll build:** `parse_dotenv(text) -> dict` — parses .env file text "
            "into a key-value dict. Handles comments, blank lines, quoted values, "
            "and values containing '='.\n\n"
            "**Why it matters:** .env files store secrets outside the code. Understanding "
            "the format lets you debug config issues and integrate with any tool that "
            "reads or writes .env files — including python-dotenv, Docker, and CI/CD systems."
        ),
        md("## Your Implementation"),
        code(
            "def parse_dotenv(text: str) -> dict:\n"
            '    """\n'
            "    Parse .env file text into a {key: value} dict.\n\n"
            "    Rules:\n"
            "      - Skip blank lines and lines starting with '#'\n"
            "      - Skip lines without '='\n"
            "      - Split on FIRST '=' only (line.partition('='))\n"
            "      - Strip whitespace from key and value\n"
            "      - Strip matching surrounding quotes (' or \\\") from value\n"
            '    """\n'
            "    # TODO: result = {}\n"
            "    # TODO: for line in text.splitlines():\n"
            "    #     line = line.strip()\n"
            "    #     skip blank lines, comments, lines without '='\n"
            "    #     key, _, value = line.partition('=')\n"
            "    #     key = key.strip(); value = value.strip()\n"
            "    #     strip matching quotes from value\n"
            "    #     result[key] = value\n"
            "    # TODO: return result\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'parse_dotenv' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: parse_dotenv defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: basic KEY=VALUE parsed correctly\n"
            "    try:\n"
            "        result = parse_dotenv('DB_HOST=localhost\\nDB_PORT=5432\\n')\n"
            "        assert result.get('DB_HOST') == 'localhost', \\\n"
            "            f\"DB_HOST wrong: {result.get('DB_HOST')!r}\"\n"
            "        assert result.get('DB_PORT') == '5432', \\\n"
            "            f\"DB_PORT wrong: {result.get('DB_PORT')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 2: basic KEY=VALUE parsed correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: comments and blank lines skipped\n"
            "    try:\n"
            "        text = '# This is a comment\\n\\nKEY=value\\n  # indented comment\\n'\n"
            "        result = parse_dotenv(text)\n"
            "        assert list(result.keys()) == ['KEY'], \\\n"
            "            f'only KEY should be parsed, got: {list(result.keys())}'\n"
            "        assert result['KEY'] == 'value'\n"
            "        passed += 1; print('\\u2705 Check 3: comments and blank lines skipped')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: double-quoted value — quotes stripped\n"
            "    try:\n"
            "        result = parse_dotenv('API_KEY=\"sk-demo-key-12345\"\\n')\n"
            "        assert result.get('API_KEY') == 'sk-demo-key-12345', \\\n"
            "            f\"quoted value wrong: {result.get('API_KEY')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: double-quoted value stripped')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: single-quoted; empty value; value containing '='\n"
            "    try:\n"
            "        text = \"NAME='John Doe'\\nEMPTY=\\nTOKEN=abc=def=ghi\\n\"\n"
            "        result = parse_dotenv(text)\n"
            "        assert result.get('NAME') == 'John Doe', \\\n"
            "            f\"single-quoted wrong: {result.get('NAME')!r}\"\n"
            "        assert 'EMPTY' in result and result['EMPTY'] == '', \\\n"
            "            f\"EMPTY should be empty string: {result.get('EMPTY')!r}\"\n"
            "        assert result.get('TOKEN') == 'abc=def=ghi', \\\n"
            "            f\"value with = wrong: {result.get('TOKEN')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: single-quoted, empty, value-with-= all correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + PARSE_DOTENV_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — mask_secret
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 032 — Exercise 2: mask_secret\n\n"
            "**What you'll build:** `mask_secret(value, show_chars=4) -> str` — "
            "masks a secret for safe logging by showing the first `show_chars` characters "
            "followed by '***'. Short values (≤ show_chars) are fully replaced with '***'.\n\n"
            "**Why it matters:** Logging raw secrets to stdout, files, or monitoring systems "
            "is a common cause of credential leaks. mask_secret lets you log enough to "
            "identify which key is configured without exposing usable credentials."
        ),
        md("## Your Implementation"),
        code(
            "def mask_secret(value, show_chars: int = 4) -> str:\n"
            '    """\n'
            "    Mask a secret for safe logging.\n\n"
            "    Args:\n"
            "        value:      The secret value (any type — converted to str).\n"
            "        show_chars: Number of leading characters to keep (default 4).\n\n"
            "    Returns:\n"
            "        str(value)[:show_chars] + '***' if len > show_chars.\n"
            "        '***' if len <= show_chars (never reveal a short secret).\n"
            '    """\n'
            "    # TODO: s = str(value)\n"
            "    # TODO: if len(s) <= show_chars: return '***'\n"
            "    # TODO: return s[:show_chars] + '***'\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'mask_secret' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: mask_secret defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: long secret → prefix + '***'\n"
            "    try:\n"
            "        result = mask_secret('sk-abc123def456')\n"
            "        assert result == 'sk-a***', \\\n"
            "            f\"expected 'sk-a***', got {result!r}\"\n"
            "        assert result.endswith('***')\n"
            "        assert result.startswith('sk-a')\n"
            "        passed += 1; print(f'\\u2705 Check 2: long secret masked to {result!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: short secret (≤ show_chars) → '***'\n"
            "    try:\n"
            "        short = mask_secret('abc')        # len 3 ≤ 4\n"
            "        empty = mask_secret('')            # empty\n"
            "        exact = mask_secret('abcd')       # len 4 == 4 → '***'\n"
            "        assert short == '***', f\"short 'abc' should be '***', got {short!r}\"\n"
            "        assert empty == '***', f\"empty should be '***', got {empty!r}\"\n"
            "        assert exact == '***', f\"exactly 4 chars should be '***', got {exact!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: short / empty / exact-length → ***')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: custom show_chars respected\n"
            "    try:\n"
            "        r6 = mask_secret('ghp_longtoken123', show_chars=6)\n"
            "        assert r6 == 'ghp_lo***', \\\n"
            "            f\"show_chars=6 wrong: {r6!r}\"\n"
            "        r0 = mask_secret('secret', show_chars=0)\n"
            "        assert r0 == '***', \\\n"
            "            f\"show_chars=0 should be '***': {r0!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: custom show_chars works')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: non-string input handled (int, bool)\n"
            "    try:\n"
            "        r_int  = mask_secret(123456789)\n"
            "        r_bool = mask_secret(True)\n"
            "        assert isinstance(r_int, str),  f'int input: expected str, got {type(r_int)}'\n"
            "        assert isinstance(r_bool, str), f'bool input: expected str, got {type(r_bool)}'\n"
            "        assert r_int.endswith('***'),    f'int masked: {r_int!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: non-string inputs handled (int, bool)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + MASK_SECRET_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — validate_config
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 032 — Exercise 3: validate_config\n\n"
            "**What you'll build:** `validate_config(config, required_keys) -> list` — "
            "returns a list of keys from `required_keys` that are missing or None in `config`. "
            "An empty list means the config is valid.\n\n"
            "**Why it matters:** Fail fast at startup. If a required API key is missing, "
            "detect it before running any automation logic and surface a clear error listing "
            "exactly what needs to be set."
        ),
        md("## Your Implementation"),
        code(
            "def validate_config(config: dict, required_keys: list) -> list:\n"
            '    """\n'
            "    Return list of required_keys that are absent or None in config.\n\n"
            "    A key is 'missing' if config.get(key) is None.\n"
            "    This catches both absent keys and keys explicitly set to None.\n"
            "    Empty string ('') is NOT missing — it is a valid configured value.\n\n"
            "    Returns:\n"
            "        List of missing key names (empty list if all present).\n"
            '    """\n'
            "    # TODO: return [k for k in required_keys if config.get(k) is None]\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    CFG = {\n"
            "        'API_KEY':  'sk-demo',\n"
            "        'DB_HOST':  'localhost',\n"
            "        'DB_PORT':  '5432',\n"
            "        'EMPTY':    '',\n"
            "        'NULL_VAL': None,\n"
            "    }\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'validate_config' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: validate_config defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: all present → empty list\n"
            "    try:\n"
            "        result = validate_config(CFG, ['API_KEY', 'DB_HOST'])\n"
            "        assert result == [], f'expected [], got {result}'\n"
            "        passed += 1; print('\\u2705 Check 2: all present → empty list []')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: missing key → appears in list\n"
            "    try:\n"
            "        result = validate_config(CFG, ['API_KEY', 'WEBHOOK_URL', 'DB_HOST'])\n"
            "        assert result == ['WEBHOOK_URL'], \\\n"
            "            f\"expected ['WEBHOOK_URL'], got {result}\"\n"
            "        passed += 1; print('\\u2705 Check 3: absent key appears in missing list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: key set to None → treated as missing\n"
            "    try:\n"
            "        result = validate_config(CFG, ['NULL_VAL'])\n"
            "        assert result == ['NULL_VAL'], \\\n"
            "            f\"None value should be missing, got {result}\"\n"
            "        passed += 1; print('\\u2705 Check 4: None value treated as missing')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty string NOT treated as missing\n"
            "    try:\n"
            "        result = validate_config(CFG, ['EMPTY'])\n"
            "        assert result == [], \\\n"
            "            f\"empty string should NOT be missing, got {result}\"\n"
            "        # Multiple missing keys — all returned in order\n"
            "        result2 = validate_config(CFG, ['API_KEY', 'MISSING_A', 'DB_HOST', 'MISSING_B'])\n"
            "        assert result2 == ['MISSING_A', 'MISSING_B'], \\\n"
            "            f\"multiple missing: expected ['MISSING_A','MISSING_B'], got {result2}\"\n"
            "        passed += 1; print('\\u2705 Check 5: empty string valid; order preserved')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + VALIDATE_CONFIG_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — safe_log_config
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 032 — Exercise 4: safe_log_config\n\n"
            "**What you'll build:** `safe_log_config(config, secret_keys) -> dict` — "
            "returns a new dict with secret keys' values replaced by `mask_secret(str(v))` "
            "and all other keys' values passed through unchanged.\n\n"
            "**Why it matters:** You need to log the config at startup to verify it loaded "
            "correctly. safe_log_config gives you a version that is safe to pass to any "
            "logger, print, or diagnostic report without exposing credentials."
        ),
        md("## Provided: mask_secret"),
        code(MASK_SECRET_IMPL),
        md("## Your Implementation"),
        code(
            "def safe_log_config(config: dict, secret_keys: list) -> dict:\n"
            '    """\n'
            "    Return a copy of config with secret values masked.\n\n"
            "    Args:\n"
            "        config:      The configuration dict.\n"
            "        secret_keys: List of key names whose values should be masked.\n\n"
            "    Returns:\n"
            "        New dict: secret keys have mask_secret(str(value)); others unchanged.\n"
            "        The original config dict is NOT modified.\n"
            '    """\n'
            "    # TODO: return {k: mask_secret(str(v)) if k in secret_keys else v\n"
            "    #               for k, v in config.items()}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    CONFIG = {\n"
            "        'API_KEY':  'sk-abc123def456',\n"
            "        'DB_HOST':  'localhost',\n"
            "        'DB_PORT':  5432,\n"
            "        'TOKEN':    'ghp_longtoken123',\n"
            "        'DEBUG':    True,\n"
            "    }\n"
            "    SECRETS = ['API_KEY', 'TOKEN']\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'safe_log_config' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: safe_log_config defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    safe = None\n"
            "\n"
            "    # Check 2: secret keys are masked (value contains '***')\n"
            "    try:\n"
            "        safe = safe_log_config(CONFIG, SECRETS)\n"
            "        assert '***' in safe.get('API_KEY', ''), \\\n"
            "            f\"API_KEY should be masked: {safe.get('API_KEY')!r}\"\n"
            "        assert '***' in safe.get('TOKEN', ''), \\\n"
            "            f\"TOKEN should be masked: {safe.get('TOKEN')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 2: secret keys masked (contain ***)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: non-secret keys pass through unchanged (including int, bool)\n"
            "    try:\n"
            "        assert safe is not None\n"
            "        assert safe.get('DB_HOST') == 'localhost', \\\n"
            "            f\"DB_HOST wrong: {safe.get('DB_HOST')!r}\"\n"
            "        assert safe.get('DB_PORT') == 5432, \\\n"
            "            f\"DB_PORT should remain int: {safe.get('DB_PORT')!r}\"\n"
            "        assert safe.get('DEBUG') is True, \\\n"
            "            f\"DEBUG should remain bool: {safe.get('DEBUG')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: non-secret values unchanged (int/bool preserved)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: original config NOT modified\n"
            "    try:\n"
            "        original_api = CONFIG['API_KEY']\n"
            "        _ = safe_log_config(CONFIG, SECRETS)\n"
            "        assert CONFIG['API_KEY'] == original_api, \\\n"
            "            f'Original config modified! API_KEY: {CONFIG[\"API_KEY\"]!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: original config not modified')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty secret_keys → all values pass through unchanged\n"
            "    try:\n"
            "        no_mask = safe_log_config(CONFIG, [])\n"
            "        assert no_mask['API_KEY'] == 'sk-abc123def456', \\\n"
            "            f\"empty secret_keys: API_KEY should be unchanged: {no_mask['API_KEY']!r}\"\n"
            "        assert len(no_mask) == len(CONFIG), \\\n"
            "            f'key count mismatch: {len(no_mask)} vs {len(CONFIG)}'\n"
            "        passed += 1; print('\\u2705 Check 5: empty secret_keys → all values unchanged')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + SAFE_LOG_CONFIG_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — SecureConfig
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 032 — Exercise 5: SecureConfig\n\n"
            "**What you'll build:** The `SecureConfig` class — "
            "`load_dict` to layer config from any dict, `get` for optional keys, "
            "`require` for mandatory keys (raises on absence), `validate` for startup "
            "checking, and `masked_dict` for log-safe output.\n\n"
            "**Why it matters:** SecureConfig is a reusable config module you can drop "
            "into any automation project. One import, one class, full secret hygiene."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "class SecureConfig:\n"
            '    """\n'
            "    Secure config module. Loads from layered dicts (defaults, .env, os.environ).\n"
            "    Provides safe access via get/require and logging-safe output via masked_dict.\n"
            '    """\n'
            "\n"
            "    def __init__(self, defaults: dict | None = None):\n"
            "        # TODO: self._config = dict(defaults or {})\n"
            "        pass\n"
            "\n"
            "    def load_dict(self, mapping: dict) -> 'SecureConfig':\n"
            "        # TODO: self._config.update(mapping); return self\n"
            "        pass\n"
            "\n"
            "    def get(self, key: str, default=None):\n"
            "        # TODO: return self._config.get(key, default)\n"
            "        pass\n"
            "\n"
            "    def require(self, key: str) -> str:\n"
            "        # TODO: val = self._config.get(key)\n"
            "        # TODO: if val is None: raise KeyError(f\"Required config key not found: '{key}'\")\n"
            "        # TODO: return str(val)\n"
            "        pass\n"
            "\n"
            "    def validate(self, required_keys: list) -> list:\n"
            "        # TODO: return validate_config(self._config, required_keys)\n"
            "        pass\n"
            "\n"
            "    def masked_dict(self, secret_keys: list) -> dict:\n"
            "        # TODO: return safe_log_config(self._config, secret_keys)\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with required methods\n"
            "    try:\n"
            "        assert 'SecureConfig' in globals()\n"
            "        for m in ('load_dict', 'get', 'require', 'validate', 'masked_dict'):\n"
            "            assert hasattr(SecureConfig, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: SecureConfig with all 5 methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: load_dict updates config and returns self (fluent)\n"
            "    try:\n"
            "        cfg = SecureConfig(defaults={'MODEL': 'llama3.2'})\n"
            "        ret = cfg.load_dict({'API_KEY': 'sk-demo', 'DB_HOST': 'localhost'})\n"
            "        assert ret is cfg, f'load_dict should return self, got {type(ret)}'\n"
            "        assert cfg.get('MODEL')   == 'llama3.2', f\"MODEL wrong: {cfg.get('MODEL')!r}\"\n"
            "        assert cfg.get('API_KEY') == 'sk-demo',  f\"API_KEY wrong: {cfg.get('API_KEY')!r}\"\n"
            "        assert cfg.get('DB_HOST') == 'localhost', f\"DB_HOST wrong: {cfg.get('DB_HOST')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 2: load_dict updates config and returns self')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: get returns value or default\n"
            "    try:\n"
            "        cfg2 = SecureConfig({'A': '1', 'B': None})\n"
            "        assert cfg2.get('A')            == '1',       f\"A: {cfg2.get('A')!r}\"\n"
            "        assert cfg2.get('B')            is None,      f\"B: {cfg2.get('B')!r}\"\n"
            "        assert cfg2.get('MISSING')      is None,      f\"MISSING: {cfg2.get('MISSING')!r}\"\n"
            "        assert cfg2.get('MISSING', 42)  == 42,        f\"default: {cfg2.get('MISSING', 42)!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: get returns value or default')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: require raises KeyError on None or absent key\n"
            "    try:\n"
            "        cfg3 = SecureConfig({'PRESENT': 'hello', 'NULL_KEY': None})\n"
            "        assert cfg3.require('PRESENT') == 'hello', \\\n"
            "            f\"require present key: {cfg3.require('PRESENT')!r}\"\n"
            "        raised_absent = False\n"
            "        try:\n"
            "            cfg3.require('MISSING_KEY')\n"
            "        except KeyError:\n"
            "            raised_absent = True\n"
            "        assert raised_absent, 'require should raise KeyError for absent key'\n"
            "        raised_none = False\n"
            "        try:\n"
            "            cfg3.require('NULL_KEY')\n"
            "        except KeyError:\n"
            "            raised_none = True\n"
            "        assert raised_none, 'require should raise KeyError for None value'\n"
            "        passed += 1; print('\\u2705 Check 4: require raises KeyError on absent/None key')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: validate and masked_dict work correctly\n"
            "    try:\n"
            "        cfg4 = SecureConfig({'API_KEY': 'sk-abc123', 'HOST': 'localhost'})\n"
            "        missing = cfg4.validate(['API_KEY', 'HOST', 'WEBHOOK'])\n"
            "        assert missing == ['WEBHOOK'], \\\n"
            "            f\"validate wrong: {missing}\"\n"
            "        safe = cfg4.masked_dict(['API_KEY'])\n"
            "        assert '***' in safe.get('API_KEY', ''), \\\n"
            "            f\"API_KEY should be masked: {safe.get('API_KEY')!r}\"\n"
            "        assert safe.get('HOST') == 'localhost', \\\n"
            "            f\"HOST should be unchanged: {safe.get('HOST')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: validate and masked_dict correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + SECURE_CONFIG_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — NOT executed by gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 032 Project: Secure Config Module\n\n"
            "## What You're Building\n\n"
            "A `SecureConfig` instance loaded from a `.env` text string that:\n"
            "1. Parses the .env format with `parse_dotenv`\n"
            "2. Validates required keys at startup with `validate`\n"
            "3. Exposes values safely with `get` and `require`\n"
            "4. Produces a log-safe representation with `masked_dict`\n\n"
            "## Project Requirements\n\n"
            "1. Define an `ENV_TEXT` string in .env format with at least 4 keys including\n"
            "   at least one secret (e.g., `API_KEY`, `TOKEN`, or `DB_PASSWORD`)\n"
            "2. Parse it with `parse_dotenv` and load into a `SecureConfig` instance\n"
            "3. Store the instance as `cfg`\n"
            "4. Run `validate` against at least 3 required keys\n"
            "5. Print `cfg.masked_dict(secret_keys)` to verify safe logging\n"
            "6. Verify with `_run_project_checks()`"
        ),
        md("## Provided: All Helper Functions + SecureConfig"),
        code(ALL_IMPLS + "\n\n\n" + SECURE_CONFIG_IMPL),
        md(
            "## Your Config Setup\n\n"
            "Define your .env text, required keys, and secret keys below."
        ),
        code(
            "# Define your .env content\n"
            "ENV_TEXT = \"\"\"\n"
            "# Application configuration\n"
            "API_KEY=sk-demo-key-12345678\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_NAME=myapp\n"
            "MODEL_NAME=llama3.2\n"
            "DEBUG=false\n"
            "\"\"\"\n"
            "\n"
            "# Keys that are secrets (will be masked in logs)\n"
            "SECRET_KEYS = ['API_KEY']\n"
            "\n"
            "# Keys that must be present at startup\n"
            "REQUIRED_KEYS = ['API_KEY', 'DB_HOST', 'DB_NAME', 'MODEL_NAME']\n"
            "\n"
            "# Build config\n"
            "cfg = SecureConfig(defaults={'DEBUG': 'false', 'MODEL_NAME': 'llama3.2'})\n"
            "cfg.load_dict(parse_dotenv(ENV_TEXT))\n"
            "\n"
            "# Validate\n"
            "missing = cfg.validate(REQUIRED_KEYS)\n"
            "if missing:\n"
            "    raise EnvironmentError(f'Missing required config: {missing}')\n"
            "print('All required keys present')\n"
            "\n"
            "# Safe logging\n"
            "safe = cfg.masked_dict(SECRET_KEYS)\n"
            "print('\\nConfig (safe for logging):')\n"
            "for k, v in safe.items():\n"
            "    print(f'  {k} = {v}')\n"
            "\n"
            "# Access values\n"
            "print(f'\\nDB host:   {cfg.require(\"DB_HOST\")}')\n"
            "print(f'Model:     {cfg.require(\"MODEL_NAME\")}')\n"
            "print(f'API key:   {mask_secret(cfg.require(\"API_KEY\"))}')"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: cfg is a SecureConfig instance\n"
            "    try:\n"
            "        assert 'cfg' in globals()\n"
            "        assert isinstance(cfg, SecureConfig), \\\n"
            "            f'cfg should be SecureConfig, got {type(cfg)}'\n"
            "        passed += 1; print('\\u2705 Check 1: cfg is a SecureConfig instance')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: cfg has at least 4 loaded keys\n"
            "    try:\n"
            "        assert hasattr(cfg, '_config')\n"
            "        assert len(cfg._config) >= 4, \\\n"
            "            f'expected >=4 config keys, got {len(cfg._config)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(cfg._config)} keys loaded')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: validate returns [] (all required keys present)\n"
            "    try:\n"
            "        missing = cfg.validate(REQUIRED_KEYS)\n"
            "        assert missing == [], \\\n"
            "            f'missing required keys: {missing}'\n"
            "        passed += 1; print('\\u2705 Check 3: all required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: masked_dict masks secret keys\n"
            "    try:\n"
            "        safe = cfg.masked_dict(SECRET_KEYS)\n"
            "        for sk in SECRET_KEYS:\n"
            "            assert '***' in str(safe.get(sk, '')), \\\n"
            "                f\"secret key '{sk}' not masked: {safe.get(sk)!r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 4: secret keys masked in masked_dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: require raises on a non-existent key\n"
            "    try:\n"
            "        raised = False\n"
            "        try:\n"
            "            cfg.require('DEFINITELY_NOT_SET_XYZ')\n"
            "        except KeyError:\n"
            "            raised = True\n"
            "        assert raised, 'require should raise KeyError for missing key'\n"
            "        passed += 1; print('\\u2705 Check 5: require raises KeyError for missing key')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('\\U0001f389 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "\n"
            "_run_project_checks()"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Extend SecureConfig with a `from_env(path='.env')` classmethod that calls "
            "`load_dotenv()` (python-dotenv) and then `load_dict(os.environ)` in one step\n"
            "- Add a `save_template(path)` method that writes a .env.example file with keys "
            "but empty values — useful for documenting required config in a repository\n"
            "- Add a `require_all(keys)` method that calls require for every key and collects "
            "all KeyErrors into one EnvironmentError — better UX than one error per missing key\n"
            "- Add type coercion to get: `get_int(key, default=0) -> int`, "
            "`get_bool(key, default=False) -> bool` using 'true'/'1'/'yes' for True\n"
            "- Integrate SecureConfig into a Day 31 batch processor: load the process_fn "
            "URL from config with require() instead of hardcoding it"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    all_code = ALL_IMPLS + "\n\n\n" + SECURE_CONFIG_IMPL

    return [
        md(
            "# Day 032 Project Solution — Secure Config Module\n\n"
            "A `SecureConfig` class loaded from a .env text string with validation, "
            "safe logging, and fail-fast access."
        ),
        code(all_code),
        md("## Action 1 — Parse .env and Build SecureConfig"),
        code(
            "ENV_TEXT = \"\"\"\n"
            "# API credentials\n"
            "API_KEY=sk-demo-key-12345678\n"
            "SLACK_WEBHOOK=https://hooks.slack.com/services/T123/B456/secrettoken\n"
            "\n"
            "# Database\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_NAME=myapp\n"
            "\n"
            "# Model\n"
            "MODEL_NAME=llama3.2\n"
            "DEBUG=false\n"
            "\"\"\"\n"
            "\n"
            "SECRET_KEYS   = ['API_KEY', 'SLACK_WEBHOOK']\n"
            "REQUIRED_KEYS = ['API_KEY', 'DB_HOST', 'DB_NAME', 'MODEL_NAME']\n"
            "\n"
            "cfg = SecureConfig(defaults={'MODEL_NAME': 'llama3.2', 'DEBUG': 'false'})\n"
            "cfg.load_dict(parse_dotenv(ENV_TEXT))\n"
            "\n"
            "print(f'Loaded {len(cfg._config)} config keys')\n"
            "print('Keys:', list(cfg._config.keys()))"
        ),
        md("## Action 2 — Validate and Log Safely"),
        code(
            "missing = cfg.validate(REQUIRED_KEYS)\n"
            "if missing:\n"
            "    raise EnvironmentError(f'Missing required config: {missing}')\n"
            "print('\\u2705 All required keys present')\n"
            "\n"
            "safe = cfg.masked_dict(SECRET_KEYS)\n"
            "print('\\nConfig (safe for logging):')\n"
            "for k, v in safe.items():\n"
            "    print(f'  {k:20} = {v}')"
        ),
        md("## Action 3 — Use Config and Demonstrate Fail-Fast"),
        code(
            "db_host = cfg.require('DB_HOST')\n"
            "db_name = cfg.require('DB_NAME')\n"
            "model   = cfg.require('MODEL_NAME')\n"
            "api_key = cfg.require('API_KEY')\n"
            "\n"
            "print(f'DB:    {db_host}/{db_name}')\n"
            "print(f'Model: {model}')\n"
            "print(f'Key:   {mask_secret(api_key)}')\n"
            "\n"
            "# Demonstrate fail-fast on a missing required key\n"
            "try:\n"
            "    cfg.require('NONEXISTENT_KEY')\n"
            "except KeyError as e:\n"
            "    print(f'\\nFail-fast: {e}')\n"
            "\n"
            "# Verify functions work on their own too\n"
            "assert parse_dotenv('KEY=val\\n')   == {'KEY': 'val'}\n"
            "assert mask_secret('sk-abc123')      == 'sk-a***'\n"
            "assert validate_config({}, ['K'])    == ['K']\n"
            "assert safe_log_config({'K': 'v'}, ['K']) == {'K': '***'}\n"
            "\n"
            "print('\\nConfig complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 032 notebooks...")
    ex_dir   = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir  = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir  / "exercise_01.ipynb", ex01())
    write_nb(ex_dir  / "exercise_02.ipynb", ex02())
    write_nb(ex_dir  / "exercise_03.ipynb", ex03())
    write_nb(ex_dir  / "exercise_04.ipynb", ex04())
    write_nb(ex_dir  / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb",    project_nb())
    write_nb(sol_dir  / "solution.ipynb",   solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
