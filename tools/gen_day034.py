#!/usr/bin/env python3
"""Generate all Day 034 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_034"

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

MAKE_PARSER_IMPL = """\
from argparse import ArgumentParser

def make_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='ai-tool',
        description='AI command-line tool powered by local LLM',
    )
    parser.add_argument(
        '--prompt', '-p', type=str, required=True,
        help='Prompt to send to the model',
    )
    parser.add_argument(
        '--model', '-m', type=str, default='llama3.2',
        help='Ollama model name (default: llama3.2)',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Print extra diagnostic output',
    )
    return parser"""

MAKE_EXTENDED_PARSER_IMPL = """\
def make_extended_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog='ai-batch',
        description='AI batch processing tool',
    )
    parser.add_argument(
        '--prompt', '-p', type=str, required=True,
        help='Prompt text',
    )
    parser.add_argument(
        '--count', '-n', type=int, default=1,
        help='Number of completions (default: 1)',
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='Output format (default: text)',
    )
    parser.add_argument(
        '--temperature', type=float, default=0.7,
        help='Sampling temperature 0.0-1.0 (default: 0.7)',
    )
    return parser"""

MAKE_SUBCOMMAND_PARSER_IMPL = """\
def make_subcommand_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='ai-tool', description='AI CLI')
    subs   = parser.add_subparsers(dest='command', required=True,
                                   title='commands')

    chat = subs.add_parser('chat', help='Send a prompt to the AI')
    chat.add_argument('--prompt', '-p', required=True, help='The prompt')
    chat.add_argument('--model',  '-m', default='llama3.2')

    summarize = subs.add_parser('summarize', help='Summarize text')
    summarize.add_argument('--text',  '-t', required=True,
                           help='Text to summarize')
    summarize.add_argument('--model', '-m', default='llama3.2')

    return parser"""

DISPATCH_IMPL = """\
def dispatch(ns, handlers: dict) -> str:
    cmd = ns.command
    if cmd not in handlers:
        raise KeyError(f"No handler registered for command: {cmd!r}")
    return handlers[cmd](ns)"""

AICLI_IMPL = """\
import ollama
from argparse import ArgumentParser

class AICli:
    def __init__(self, prog: str = 'ai-tool', model: str = 'llama3.2'):
        self.model       = model
        self._parser     = ArgumentParser(prog=prog,
                                          description='AI command-line tool')
        self._subs       = self._parser.add_subparsers(dest='command',
                                                        required=True)
        self._prompt_fns: dict = {}

    def add_command(self, name: str, prompt_fn,
                    help: str = '') -> 'AICli':
        sub = self._subs.add_parser(name, help=help)
        sub.add_argument('--input', '-i', required=True, help='Input text')
        self._prompt_fns[name] = prompt_fn
        return self

    def run(self, args_list: list[str]) -> str:
        ns     = self._parser.parse_args(args_list)
        prompt = self._prompt_fns[ns.command](ns.input)
        resp   = ollama.chat(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return resp['message']['content']"""

ALL_IMPLS = "\n\n\n".join([
    MAKE_PARSER_IMPL,
    MAKE_EXTENDED_PARSER_IMPL,
    MAKE_SUBCOMMAND_PARSER_IMPL,
    DISPATCH_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — make_parser
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 034 — Exercise 1: make_parser\n\n"
            "**What you'll build:** `make_parser() -> ArgumentParser` — create and return "
            "a configured `ArgumentParser` with three arguments: `--prompt/-p` (str, required), "
            "`--model/-m` (str, default='llama3.2'), and `--verbose/-v` (store_true flag).\n\n"
            "**Why it matters:** `make_parser` is the foundation of every CLI tool. "
            "Returning the parser (rather than calling `parse_args` inside the function) "
            "keeps it testable and extensible."
        ),
        md("## Your Implementation"),
        code(
            "from argparse import ArgumentParser\n"
            "\n"
            "def make_parser() -> ArgumentParser:\n"
            '    """\n'
            "    Create and return a configured ArgumentParser for an AI CLI.\n\n"
            "    Arguments:\n"
            "        --prompt/-p  str, required        Prompt to send to the model\n"
            "        --model/-m   str, default=llama3.2  Ollama model name\n"
            "        --verbose/-v store_true flag       Enable verbose output\n"
            '    """\n'
            "    # TODO: parser = ArgumentParser(prog='ai-tool', description='...')\n"
            "    # TODO: parser.add_argument('--prompt', '-p', type=str, required=True, help='...')\n"
            "    # TODO: parser.add_argument('--model',  '-m', type=str, default='llama3.2', help='...')\n"
            "    # TODO: parser.add_argument('--verbose','-v', action='store_true', help='...')\n"
            "    # TODO: return parser\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import io\n"
            "import sys\n"
            "from argparse import ArgumentParser\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined and returns ArgumentParser\n"
            "    try:\n"
            "        assert 'make_parser' in globals()\n"
            "        parser = make_parser()\n"
            "        assert isinstance(parser, ArgumentParser), \\\n"
            "            f'expected ArgumentParser, got {type(parser).__name__}'\n"
            "        passed += 1; print('\\u2705 Check 1: make_parser returns ArgumentParser')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: parse valid args — defaults applied\n"
            "    try:\n"
            "        ns = parser.parse_args(['--prompt', 'hello'])\n"
            "        assert ns.prompt == 'hello',      f'prompt: {ns.prompt!r}'\n"
            "        assert ns.model  == 'llama3.2',   f'model default: {ns.model!r}'\n"
            "        assert ns.verbose == False,        f'verbose default: {ns.verbose!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: parse --prompt hello gives correct defaults')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: short flags (-p, -v) work\n"
            "    try:\n"
            "        ns = parser.parse_args(['-p', 'test', '-v'])\n"
            "        assert ns.prompt  == 'test', f'-p: {ns.prompt!r}'\n"
            "        assert ns.verbose == True,   f'-v: {ns.verbose!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: short flags -p and -v work')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: --model overrides default\n"
            "    try:\n"
            "        ns = parser.parse_args(['--prompt', 'hi', '--model', 'llama3.1'])\n"
            "        assert ns.model == 'llama3.1', f'custom model: {ns.model!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: --model overrides default')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: missing --prompt raises SystemExit(2)\n"
            "    try:\n"
            "        old_err = sys.stderr; sys.stderr = io.StringIO()\n"
            "        raised = False\n"
            "        try:\n"
            "            parser.parse_args([])\n"
            "        except SystemExit as e:\n"
            "            raised = True\n"
            "            assert e.code == 2, f'expected exit code 2, got {e.code}'\n"
            "        finally:\n"
            "            sys.stderr = old_err\n"
            "        assert raised, 'missing --prompt should raise SystemExit'\n"
            "        passed += 1; print('\\u2705 Check 5: missing --prompt raises SystemExit(2)')\n"
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
            + MAKE_PARSER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — make_extended_parser
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 034 — Exercise 2: make_extended_parser\n\n"
            "**What you'll build:** `make_extended_parser() -> ArgumentParser` — "
            "a parser with typed arguments: `--count/-n` (int, default=1), "
            "`--format/-f` (choices=['text','json','markdown'], default='text'), "
            "and `--temperature` (float, default=0.7).\n\n"
            "**Why it matters:** `type=int` and `choices=` give you free input validation — "
            "argparse rejects `--count abc` or `--format html` with a clear error message "
            "before your code ever runs."
        ),
        md("## Provided: make_parser (from Exercise 1)"),
        code(MAKE_PARSER_IMPL),
        md("## Your Implementation"),
        code(
            "def make_extended_parser() -> ArgumentParser:\n"
            '    """\n'
            "    Parser with typed and constrained arguments.\n\n"
            "    Arguments:\n"
            "        --prompt/-p      str, required\n"
            "        --count/-n       int, default=1\n"
            "        --format/-f      choices=['text','json','markdown'], default='text'\n"
            "        --temperature    float, default=0.7\n"
            '    """\n'
            "    # TODO: parser = ArgumentParser(prog='ai-batch', description='...')\n"
            "    # TODO: parser.add_argument('--prompt', '-p', type=str, required=True, help='...')\n"
            "    # TODO: parser.add_argument('--count', '-n', type=int, default=1, help='...')\n"
            "    # TODO: parser.add_argument('--format', '-f',\n"
            "    #             choices=['text', 'json', 'markdown'], default='text', help='...')\n"
            "    # TODO: parser.add_argument('--temperature', type=float, default=0.7, help='...')\n"
            "    # TODO: return parser\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import io\n"
            "import sys\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'make_extended_parser' in globals()\n"
            "        parser = make_extended_parser()\n"
            "        passed += 1; print('\\u2705 Check 1: make_extended_parser defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: count parses as int (not str)\n"
            "    try:\n"
            "        ns = parser.parse_args(['--prompt', 'hi', '--count', '5'])\n"
            "        assert ns.count == 5,               f'count should be int 5, got {ns.count!r}'\n"
            "        assert isinstance(ns.count, int),   f'count type: {type(ns.count).__name__}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: --count 5 parses as int (got {ns.count!r})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: invalid choice for --format raises SystemExit(2)\n"
            "    try:\n"
            "        old_err = sys.stderr; sys.stderr = io.StringIO()\n"
            "        raised = False\n"
            "        try:\n"
            "            parser.parse_args(['--prompt', 'x', '--format', 'html'])\n"
            "        except SystemExit as e:\n"
            "            raised = True\n"
            "            assert e.code == 2, f'expected exit 2, got {e.code}'\n"
            "        finally:\n"
            "            sys.stderr = old_err\n"
            "        assert raised, '--format html should be rejected'\n"
            "        passed += 1; print('\\u2705 Check 3: invalid --format raises SystemExit(2)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: defaults correct when only --prompt given\n"
            "    try:\n"
            "        ns = parser.parse_args(['--prompt', 'hi'])\n"
            "        assert ns.count       == 1,      f'default count: {ns.count!r}'\n"
            "        assert ns.format      == 'text', f'default format: {ns.format!r}'\n"
            "        assert ns.temperature == 0.7,    f'default temp: {ns.temperature!r}'\n"
            "        passed += 1; print('\\u2705 Check 4: all four defaults correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: temperature parses as float; valid choices pass\n"
            "    try:\n"
            "        ns = parser.parse_args(\n"
            "            ['--prompt', 'hi', '--temperature', '0.3', '--format', 'json']\n"
            "        )\n"
            "        assert isinstance(ns.temperature, float), \\\n"
            "            f'temperature type: {type(ns.temperature).__name__}'\n"
            "        assert ns.temperature == 0.3, f'temperature: {ns.temperature!r}'\n"
            "        assert ns.format == 'json',   f'format: {ns.format!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: temperature=float, valid format choices work')\n"
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
            + MAKE_EXTENDED_PARSER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — make_subcommand_parser
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 034 — Exercise 3: make_subcommand_parser\n\n"
            "**What you'll build:** `make_subcommand_parser() -> ArgumentParser` — "
            "a parser with two subcommands: `chat` (--prompt/-p required, --model/-m) "
            "and `summarize` (--text/-t required, --model/-m), created with "
            "`add_subparsers(dest='command', required=True)`.\n\n"
            "**Why it matters:** Subcommands turn one tool into a multi-mode program. "
            "`ns.command` tells your dispatch which branch to run."
        ),
        md("## Provided: make_parser, make_extended_parser"),
        code(MAKE_PARSER_IMPL + "\n\n\n" + MAKE_EXTENDED_PARSER_IMPL),
        md("## Your Implementation"),
        code(
            "def make_subcommand_parser() -> ArgumentParser:\n"
            '    """\n'
            "    Parser with 'chat' and 'summarize' subcommands.\n\n"
            "    chat subcommand:     --prompt/-p (required), --model/-m (default='llama3.2')\n"
            "    summarize subcommand: --text/-t  (required), --model/-m (default='llama3.2')\n"
            '    """\n'
            "    # TODO: parser = ArgumentParser(prog='ai-tool', description='AI CLI')\n"
            "    # TODO: subs = parser.add_subparsers(dest='command', required=True, title='commands')\n"
            "    #\n"
            "    # TODO: chat = subs.add_parser('chat', help='Send a prompt to the AI')\n"
            "    # TODO: chat.add_argument('--prompt', '-p', required=True, help='The prompt')\n"
            "    # TODO: chat.add_argument('--model',  '-m', default='llama3.2')\n"
            "    #\n"
            "    # TODO: summarize = subs.add_parser('summarize', help='Summarize text')\n"
            "    # TODO: summarize.add_argument('--text',  '-t', required=True, help='Text to summarize')\n"
            "    # TODO: summarize.add_argument('--model', '-m', default='llama3.2')\n"
            "    #\n"
            "    # TODO: return parser\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "import io\n"
            "import sys\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'make_subcommand_parser' in globals()\n"
            "        parser = make_subcommand_parser()\n"
            "        passed += 1; print('\\u2705 Check 1: make_subcommand_parser defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: parse chat subcommand\n"
            "    try:\n"
            "        ns = parser.parse_args(['chat', '--prompt', 'hello'])\n"
            "        assert ns.command == 'chat',      f'command: {ns.command!r}'\n"
            "        assert ns.prompt  == 'hello',     f'prompt: {ns.prompt!r}'\n"
            "        assert ns.model   == 'llama3.2',  f'model default: {ns.model!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: chat subcommand parsed correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: parse summarize subcommand\n"
            "    try:\n"
            "        ns = parser.parse_args(['summarize', '--text', 'long article'])\n"
            "        assert ns.command == 'summarize',    f'command: {ns.command!r}'\n"
            "        assert ns.text    == 'long article', f'text: {ns.text!r}'\n"
            "        assert ns.model   == 'llama3.2',     f'model: {ns.model!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: summarize subcommand parsed correctly')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: no subcommand raises SystemExit(2)\n"
            "    try:\n"
            "        old_err = sys.stderr; sys.stderr = io.StringIO()\n"
            "        raised = False\n"
            "        try:\n"
            "            parser.parse_args([])\n"
            "        except SystemExit as e:\n"
            "            raised = True; code = e.code\n"
            "        finally:\n"
            "            sys.stderr = old_err\n"
            "        assert raised, 'missing subcommand should raise SystemExit'\n"
            "        assert code == 2, f'expected exit 2, got {code}'\n"
            "        passed += 1; print('\\u2705 Check 4: missing subcommand raises SystemExit(2)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: unknown subcommand raises SystemExit(2)\n"
            "    try:\n"
            "        old_err = sys.stderr; sys.stderr = io.StringIO()\n"
            "        raised = False\n"
            "        try:\n"
            "            parser.parse_args(['classify', '--prompt', 'x'])\n"
            "        except SystemExit as e:\n"
            "            raised = True\n"
            "        finally:\n"
            "            sys.stderr = old_err\n"
            "        assert raised, 'unknown subcommand should raise SystemExit'\n"
            "        passed += 1; print('\\u2705 Check 5: unknown subcommand raises SystemExit')\n"
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
            + MAKE_SUBCOMMAND_PARSER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — dispatch
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 034 — Exercise 4: dispatch\n\n"
            "**What you'll build:** `dispatch(ns, handlers) -> str` — "
            "look up `ns.command` in a `handlers` dict and call the matching handler, "
            "returning its result. Raise `KeyError` if the command has no handler.\n\n"
            "**Why it matters:** The `handlers` dict pattern is extensible (add a command = "
            "add one dict entry), testable (inject mock handlers), and explicit "
            "(KeyError immediately flags a missing handler)."
        ),
        md("## Provided: make_subcommand_parser (used in checks)"),
        code(MAKE_PARSER_IMPL + "\n\n\n" + MAKE_SUBCOMMAND_PARSER_IMPL),
        md("## Your Implementation"),
        code(
            "def dispatch(ns, handlers: dict) -> str:\n"
            '    """\n'
            "    Route a parsed Namespace to the correct handler function.\n\n"
            "    Args:\n"
            "        ns:       Parsed argparse Namespace with a .command attribute.\n"
            "        handlers: dict mapping command name (str) to handler function.\n\n"
            "    Returns:\n"
            "        The string returned by handlers[ns.command](ns).\n\n"
            "    Raises:\n"
            "        KeyError: if ns.command is not in handlers.\n"
            '    """\n'
            "    # TODO: cmd = ns.command\n"
            "    # TODO: if cmd not in handlers:\n"
            "    #     raise KeyError(f'No handler registered for command: {cmd!r}')\n"
            "    # TODO: return handlers[cmd](ns)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Stub handlers for testing — no LLM calls\n"
            "    def _chat_handler(ns):\n"
            "        return f'chat:{ns.prompt}'\n"
            "\n"
            "    def _summarize_handler(ns):\n"
            "        return f'summarize:{ns.text}'\n"
            "\n"
            "    handlers = {\n"
            "        'chat':      _chat_handler,\n"
            "        'summarize': _summarize_handler,\n"
            "    }\n"
            "    parser = make_subcommand_parser()\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'dispatch' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: dispatch defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: routes 'chat' correctly\n"
            "    try:\n"
            "        ns = parser.parse_args(['chat', '--prompt', 'hello'])\n"
            "        result = dispatch(ns, handlers)\n"
            "        assert result == 'chat:hello', \\\n"
            "            f\"expected 'chat:hello', got {result!r}\"\n"
            "        passed += 1; print('\\u2705 Check 2: dispatch routes chat → _chat_handler')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: routes 'summarize' correctly\n"
            "    try:\n"
            "        ns = parser.parse_args(['summarize', '--text', 'some text'])\n"
            "        result = dispatch(ns, handlers)\n"
            "        assert result == 'summarize:some text', \\\n"
            "            f\"expected 'summarize:some text', got {result!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: dispatch routes summarize → _summarize_handler')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: raises KeyError for unknown command\n"
            "    try:\n"
            "        import types\n"
            "        fake_ns = types.SimpleNamespace(command='classify', text='x')\n"
            "        raised = False\n"
            "        try:\n"
            "            dispatch(fake_ns, handlers)\n"
            "        except KeyError:\n"
            "            raised = True\n"
            "        assert raised, 'unknown command should raise KeyError'\n"
            "        passed += 1; print('\\u2705 Check 4: unknown command raises KeyError')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: handler receives correct namespace attributes\n"
            "    try:\n"
            "        received = {}\n"
            "        def _inspecting_handler(ns):\n"
            "            received['command'] = ns.command\n"
            "            received['prompt']  = ns.prompt\n"
            "            received['model']   = ns.model\n"
            "            return 'ok'\n"
            "        h2 = {'chat': _inspecting_handler}\n"
            "        ns = parser.parse_args(['chat', '--prompt', 'test', '--model', 'custom'])\n"
            "        dispatch(ns, h2)\n"
            "        assert received['command'] == 'chat',   f'command: {received.get(\"command\")!r}'\n"
            "        assert received['prompt']  == 'test',   f'prompt: {received.get(\"prompt\")!r}'\n"
            "        assert received['model']   == 'custom', f'model: {received.get(\"model\")!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: handler receives full namespace with correct attrs')\n"
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
            + DISPATCH_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — AICli
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 034 — Exercise 5: AICli\n\n"
            "**What you'll build:** The `AICli` class — `add_command(name, prompt_fn, help)` "
            "registers a subcommand that transforms `--input` text with `prompt_fn` before "
            "calling `ollama.chat`; `run(args_list)` parses and executes; `add_command` "
            "returns `self` for fluent chaining.\n\n"
            "**Why it matters:** AICli is the full CLI tool in a class: any `prompt_fn` "
            "becomes a subcommand with one call to `add_command`."
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md("## Your Implementation"),
        code(
            "import ollama\n"
            "from argparse import ArgumentParser\n"
            "\n"
            "class AICli:\n"
            '    """\n'
            "    CLI wrapper: argparse subcommands + ollama LLM calls.\n"
            "    Each subcommand maps --input text through a prompt_fn before calling\n"
            "    ollama.chat. add_command returns self for fluent chaining.\n"
            '    """\n'
            "\n"
            "    def __init__(self, prog: str = 'ai-tool', model: str = 'llama3.2'):\n"
            "        # TODO: self.model = model\n"
            "        # TODO: self._parser = ArgumentParser(prog=prog, description='AI CLI')\n"
            "        # TODO: self._subs = self._parser.add_subparsers(dest='command', required=True)\n"
            "        # TODO: self._prompt_fns = {}\n"
            "        pass\n"
            "\n"
            "    def add_command(self, name: str, prompt_fn,\n"
            "                    help: str = '') -> 'AICli':\n"
            "        # TODO: sub = self._subs.add_parser(name, help=help)\n"
            "        # TODO: sub.add_argument('--input', '-i', required=True, help='Input text')\n"
            "        # TODO: self._prompt_fns[name] = prompt_fn\n"
            "        # TODO: return self\n"
            "        pass\n"
            "\n"
            "    def run(self, args_list: list[str]) -> str:\n"
            "        # TODO: ns = self._parser.parse_args(args_list)\n"
            "        # TODO: prompt = self._prompt_fns[ns.command](ns.input)\n"
            "        # TODO: resp = ollama.chat(\n"
            "        #     model=self.model,\n"
            "        #     messages=[{'role': 'user', 'content': prompt}],\n"
            "        # )\n"
            "        # TODO: return resp['message']['content']\n"
            "        pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: class defined with add_command and run methods\n"
            "    try:\n"
            "        assert 'AICli' in globals()\n"
            "        for m in ('add_command', 'run'):\n"
            "            assert hasattr(AICli, m), f'missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: AICli with add_command and run')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: __init__ stores model and creates parser\n"
            "    try:\n"
            "        cli = AICli(prog='test-tool', model='llama3.2')\n"
            "        assert cli.model == 'llama3.2', \\\n"
            "            f'model: expected llama3.2, got {cli.model!r}'\n"
            "        assert hasattr(cli, '_parser'), 'missing _parser attribute'\n"
            "        assert hasattr(cli, '_prompt_fns'), 'missing _prompt_fns attribute'\n"
            "        assert isinstance(cli._prompt_fns, dict), '_prompt_fns should be dict'\n"
            "        passed += 1; print('\\u2705 Check 2: __init__ stores model and creates parser')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: add_command returns self (fluent) and registers prompt_fn\n"
            "    try:\n"
            "        cli = AICli()\n"
            "        fn  = lambda t: f'test:{t}'\n"
            "        ret = cli.add_command('ask', fn, help='Ask a question')\n"
            "        assert ret is cli, f'add_command should return self, got {type(ret)}'\n"
            "        assert 'ask' in cli._prompt_fns, \\\n"
            "            f'ask not registered: {list(cli._prompt_fns.keys())}'\n"
            "        assert cli._prompt_fns['ask']('hello') == 'test:hello', \\\n"
            "            f'prompt_fn wrong: {cli._prompt_fns[\"ask\"](\"hello\")!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: add_command returns self and registers prompt_fn')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: run calls LLM and returns string\n"
            "    try:\n"
            "        cli = AICli(model='llama3.2')\n"
            "        cli.add_command('ask', lambda t: t, help='Raw prompt')\n"
            "        result = cli.run(['ask', '--input', 'Say the word hello'])\n"
            "        assert isinstance(result, str), \\\n"
            "            f'run should return str, got {type(result).__name__}'\n"
            "        assert result.strip(), 'run returned empty string'\n"
            "        passed += 1; print(f'\\u2705 Check 4: run returns non-empty string: {result.strip()[:40]!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: fluent chaining and multiple commands\n"
            "    try:\n"
            "        cli = (\n"
            "            AICli()\n"
            "            .add_command('ask', lambda t: t)\n"
            "            .add_command('upper', lambda t: f'UPPERCASE: {t}')\n"
            "        )\n"
            "        assert 'ask'   in cli._prompt_fns, 'ask not registered'\n"
            "        assert 'upper' in cli._prompt_fns, 'upper not registered'\n"
            "        assert len(cli._prompt_fns) >= 2, \\\n"
            "            f'expected >=2 commands, got {len(cli._prompt_fns)}'\n"
            "        passed += 1; print('\\u2705 Check 5: fluent chaining registers multiple commands')\n"
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
            + AICLI_IMPL + "\n"
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
            "# Day 034 Project: Installable AI CLI Tool\n\n"
            "## What You're Building\n\n"
            "A multi-command `AICli` instance with at least three subcommands that "
            "each transform `--input` text through a different prompt before calling "
            "the LLM.\n\n"
            "## Project Requirements\n\n"
            "1. Create an `AICli` instance stored as `cli`\n"
            "2. Register at least 3 subcommands (e.g., `ask`, `summarize`, `classify`)\n"
            "3. Each subcommand must have a distinct `prompt_fn` that wraps the input\n"
            "4. Call at least 2 different subcommands and print the results\n"
            "5. Print the entry-point snippet that would make this tool installable\n"
            "6. Verify with `_run_project_checks()`"
        ),
        md("## Provided: All Helper Functions + AICli"),
        code(ALL_IMPLS + "\n\n\n" + AICLI_IMPL),
        md("## Your CLI Tool"),
        code(
            "# Build your AICli with at least 3 subcommands\n"
            "cli = (\n"
            "    AICli(prog='my-ai', model='llama3.2')\n"
            "    .add_command(\n"
            "        'ask',\n"
            "        lambda t: t,\n"
            "        help='Send a raw prompt to the AI',\n"
            "    )\n"
            "    .add_command(\n"
            "        'summarize',\n"
            "        lambda t: f'Summarize in 2 sentences:\\n\\n{t}',\n"
            "        help='Summarize the input text',\n"
            "    )\n"
            "    .add_command(\n"
            "        'classify',\n"
            "        lambda t: f\"Classify as positive/negative/neutral. One word.\\n\\n'{t}'\",\n"
            "        help='Classify text sentiment',\n"
            "    )\n"
            ")\n"
            "\n"
            "# TODO: run at least 2 subcommands and print results\n"
            "# result1 = cli.run(['ask', '--input', 'What is the capital of France?'])\n"
            "# print(f'ask: {result1.strip()}')\n"
            "#\n"
            "# result2 = cli.run(['classify', '--input', 'I love this!'])\n"
            "# print(f'classify: {result2.strip()}')\n"
            "\n"
            "# TODO: print the pyproject.toml entry-point snippet\n"
            "print('[project.scripts]')\n"
            "print('my-ai = \"my_module:main\"')"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: cli is an AICli instance\n"
            "    try:\n"
            "        assert 'cli' in globals()\n"
            "        assert isinstance(cli, AICli), \\\n"
            "            f'cli should be AICli, got {type(cli)}'\n"
            "        passed += 1; print('\\u2705 Check 1: cli is an AICli instance')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: at least 3 subcommands registered\n"
            "    try:\n"
            "        assert hasattr(cli, '_prompt_fns')\n"
            "        assert len(cli._prompt_fns) >= 3, \\\n"
            "            f'need >= 3 commands, got {len(cli._prompt_fns)}: {list(cli._prompt_fns)}'\n"
            "        passed += 1; print(f'\\u2705 Check 2: {len(cli._prompt_fns)} subcommands registered')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result1 defined (at least one subcommand was run)\n"
            "    try:\n"
            "        assert 'result1' in globals(), \\\n"
            "            'result1 not defined — run at least 2 subcommands'\n"
            "        assert isinstance(result1, str) and result1.strip(), \\\n"
            "            'result1 should be a non-empty string'\n"
            "        passed += 1; print('\\u2705 Check 3: result1 is a non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: result2 defined (at least two subcommands were run)\n"
            "    try:\n"
            "        assert 'result2' in globals(), \\\n"
            "            'result2 not defined — run at least 2 subcommands'\n"
            "        assert isinstance(result2, str) and result2.strip(), \\\n"
            "            'result2 should be a non-empty string'\n"
            "        passed += 1; print('\\u2705 Check 4: result2 is a non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: distinct prompt_fns (each command does something different)\n"
            "    try:\n"
            "        fns = list(cli._prompt_fns.values())\n"
            "        prompts = [fn('test input') for fn in fns]\n"
            "        unique = len(set(prompts))\n"
            "        assert unique == len(fns), \\\n"
            "            f'all prompt_fns should produce different prompts for same input; got {unique} unique'\n"
            "        passed += 1; print(f'\\u2705 Check 5: {unique} distinct prompt_fns registered')\n"
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
            "- Add `--model` to each subcommand so users can choose the model per call\n"
            "- Add a `--verbose` flag that prints the prompt before sending it to the LLM\n"
            "- Add a `translate` subcommand: `--input` + `--lang` (target language), "
            "  prompt_fn builds `'Translate to {lang}: {input}'`\n"
            "- Write `main.py` with `if __name__ == '__main__': sys.exit(main())` and a "
            "`pyproject.toml` — then install with `pip install -e .` and try `my-ai ask --input hello`\n"
            "- Combine with Day 033 BatchProcessor: add a `batch` subcommand that reads "
            "  `--input` as a comma-separated list and processes all items concurrently"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    all_code = ALL_IMPLS + "\n\n\n" + AICLI_IMPL

    return [
        md(
            "# Day 034 Project Solution — Installable AI CLI Tool\n\n"
            "A multi-command `AICli` wrapping argparse + ollama. "
            "Demonstrates `make_parser`, `make_subcommand_parser`, `dispatch`, and `AICli`."
        ),
        code(all_code),
        md("## Action 1 — Demonstrate make_parser and make_extended_parser"),
        code(
            "import io, sys\n"
            "\n"
            "# make_parser\n"
            "p = make_parser()\n"
            "ns = p.parse_args(['--prompt', 'hello world', '--verbose'])\n"
            "assert ns.prompt  == 'hello world'\n"
            "assert ns.model   == 'llama3.2'\n"
            "assert ns.verbose == True\n"
            "print(f'make_parser: prompt={ns.prompt!r}, model={ns.model!r}, verbose={ns.verbose}')\n"
            "\n"
            "# make_extended_parser\n"
            "ep = make_extended_parser()\n"
            "ns2 = ep.parse_args(['--prompt', 'hi', '--count', '3', '--format', 'json'])\n"
            "assert ns2.count == 3               # int\n"
            "assert ns2.format == 'json'          # choice\n"
            "assert isinstance(ns2.temperature, float)\n"
            "print(f'make_extended_parser: count={ns2.count} (int), format={ns2.format!r}, '\n"
            "      f'temp={ns2.temperature}')"
        ),
        md("## Action 2 — Subcommands and dispatch"),
        code(
            "def _chat_handler(ns):\n"
            "    return f'[chat] prompt={ns.prompt!r}, model={ns.model!r}'\n"
            "\n"
            "def _summarize_handler(ns):\n"
            "    return f'[summarize] text={ns.text[:30]!r}, model={ns.model!r}'\n"
            "\n"
            "handlers = {'chat': _chat_handler, 'summarize': _summarize_handler}\n"
            "sp = make_subcommand_parser()\n"
            "\n"
            "ns = sp.parse_args(['chat', '--prompt', 'What is AI?'])\n"
            "print(dispatch(ns, handlers))\n"
            "\n"
            "ns2 = sp.parse_args(['summarize', '--text', 'Long article about AI...'])\n"
            "print(dispatch(ns2, handlers))\n"
            "\n"
            "assert ns.command  == 'chat'\n"
            "assert ns2.command == 'summarize'"
        ),
        md("## Action 3 — AICli end-to-end"),
        code(
            "cli = (\n"
            "    AICli(prog='ai-tool', model='llama3.2')\n"
            "    .add_command('ask',\n"
            "                 lambda t: t,\n"
            "                 help='Send raw prompt')\n"
            "    .add_command('sentiment',\n"
            "                 lambda t: f\"Classify as positive/negative/neutral. One word.\\n\\n'{t}'\",\n"
            "                 help='Classify sentiment')\n"
            ")\n"
            "\n"
            "r1 = cli.run(['ask', '--input', 'What colour is the sky? One word.'])\n"
            "print(f'ask:       {r1.strip()!r}')\n"
            "\n"
            "r2 = cli.run(['sentiment', '--input', 'I love this product!'])\n"
            "print(f'sentiment: {r2.strip()!r}')\n"
            "\n"
            "assert isinstance(r1, str) and r1.strip()\n"
            "assert isinstance(r2, str) and r2.strip()\n"
            "\n"
            "# Entry-point reminder\n"
            "print('\\n# pyproject.toml entry point:')\n"
            "print('[project.scripts]')\n"
            "print('ai-tool = \"my_module.cli:main\"')\n"
            "\n"
            "print('\\nCLI complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 034 notebooks...")
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
