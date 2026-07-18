#!/usr/bin/env python3
"""Generate all Day 029 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_029"

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

FORMAT_SLACK_IMPL = """\
def format_slack_message(
    title: str,
    body: str,
    color: str = "#36a64f",
) -> dict:
    from datetime import datetime
    return {
        "attachments": [
            {
                "fallback": title,
                "color":    color,
                "title":    title,
                "text":     body,
                "footer":   "NotificationBot",
                "ts":       int(datetime.now().timestamp()),
            }
        ]
    }"""

FORMAT_DISCORD_IMPL = """\
def format_discord_embed(
    title: str,
    description: str,
    color: int = 0x00b0f4,
) -> dict:
    return {
        "title":       title,
        "description": description,
        "color":       color,
    }"""

TRUNCATE_IMPL = """\
def truncate_for_chat(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "...\""""

AI_SUMMARIZE_IMPL = """\
def ai_summarize_for_chat(
    content: str,
    platform: str = "slack",
    model: str = "llama3.2",
) -> str:
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a notification writer for {platform}. "
                    "Write a concise notification summary: under 300 characters, "
                    "no headers, no bullet points. Lead with the most important fact."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Summarise this for a {platform} notification:\\n\\n"
                    f"{content[:3000]}"
                ),
            },
        ],
    )
    return response["message"]["content"]"""

BUILD_NOTIF_IMPL = """\
def build_notification(
    event_type: str,
    data: dict,
    model: str = "llama3.2",
) -> dict:
    content = (
        f"Event: {event_type}\\n\\nData:\\n"
        + "\\n".join(f"  {k}: {v}" for k, v in data.items())
    )
    summary = ai_summarize_for_chat(content, platform="slack", model=model)
    title   = f"[{event_type.upper()}] Notification"
    return {
        "event_type":      event_type,
        "title":           title,
        "summary":         summary,
        "slack_payload":   format_slack_message(title, summary),
        "discord_payload": {
            "embeds": [format_discord_embed(title, truncate_for_chat(summary, 4096))]
        },
    }"""

NOTIF_BOT_IMPL = """\
class NotificationBot:
    def __init__(
        self,
        slack_url: str | None = None,
        discord_url: str | None = None,
        model: str = "llama3.2",
    ):
        self.slack_url   = slack_url
        self.discord_url = discord_url
        self.model       = model

    def preview(self, event_type: str, data: dict) -> dict:
        return build_notification(event_type, data, model=self.model)

    def notify(self, event_type: str, data: dict) -> dict:
        result = self.preview(event_type, data)
        result["sent"] = []
        if self.slack_url:
            import requests
            r = requests.post(
                self.slack_url, json=result["slack_payload"], timeout=10
            )
            result["sent"].append(f"slack:{r.status_code}")
        if self.discord_url:
            import requests
            r = requests.post(
                self.discord_url, json=result["discord_payload"], timeout=10
            )
            result["sent"].append(f"discord:{r.status_code}")
        return result\
"""

ALL_IMPLS = "\n\n\n".join([
    FORMAT_SLACK_IMPL,
    FORMAT_DISCORD_IMPL,
    TRUNCATE_IMPL,
    AI_SUMMARIZE_IMPL,
    BUILD_NOTIF_IMPL,
])


# ---------------------------------------------------------------------------
# Exercise 01 — format_slack_message
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 029 — Exercise 1: format_slack_message\n\n"
            "**What you'll build:** `format_slack_message(title, body, color='#36a64f') -> dict` — "
            "builds a Slack incoming-webhook payload dict with a colour attachment.\n\n"
            "**Why it matters:** The payload shape is the contract between your script and "
            "Slack. A correct payload produces a formatted message; a wrong payload gets a "
            "400 error. Building and testing the payload without making HTTP calls lets you "
            "verify the structure without needing a real Slack workspace."
        ),
        md("## Your Implementation"),
        code(
            "def format_slack_message(\n"
            "    title: str,\n"
            "    body: str,\n"
            "    color: str = '#36a64f',\n"
            ") -> dict:\n"
            '    """\n'
            "    Build a Slack webhook payload with a colour attachment.\n\n"
            "    Args:\n"
            "        title: Bold headline of the attachment.\n"
            "        body:  Body text of the attachment.\n"
            "        color: Hex colour string for the left sidebar (default green).\n\n"
            "    Returns:\n"
            "        Dict with 'attachments' key containing one attachment dict.\n"
            "        Attachment has: fallback, color, title, text.\n"
            '    """\n'
            "    # TODO: return {'attachments': [{'fallback': title, 'color': color,\n"
            "    #                                'title': title, 'text': body}]}\n"
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
            "        assert 'format_slack_message' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: format_slack_message defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    payload = None\n"
            "\n"
            "    # Check 2: returns a dict with 'attachments' key\n"
            "    try:\n"
            "        payload = format_slack_message('Test Title', 'Test body')\n"
            "        assert isinstance(payload, dict), \\\n"
            "            f'expected dict, got {type(payload)}'\n"
            "        assert 'attachments' in payload, \\\n"
            "            f\"'attachments' key missing: {list(payload)}'\"\n"
            "        passed += 1; print('\\u2705 Check 2: returns dict with attachments key')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: attachments is a list with one item\n"
            "    try:\n"
            "        assert payload is not None\n"
            "        att = payload['attachments']\n"
            "        assert isinstance(att, list), \\\n"
            "            f'attachments should be list, got {type(att)}'\n"
            "        assert len(att) == 1, \\\n"
            "            f'expected 1 attachment, got {len(att)}'\n"
            "        passed += 1; print('\\u2705 Check 3: attachments is a list of 1')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: attachment has correct title and text\n"
            "    try:\n"
            "        assert payload is not None\n"
            "        att = payload['attachments'][0]\n"
            "        assert att.get('title') == 'Test Title', \\\n"
            "            f\"title wrong: {att.get('title')!r}\"\n"
            "        assert att.get('text') == 'Test body', \\\n"
            "            f\"text wrong: {att.get('text')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: title and text correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: default color is '#36a64f'; custom color works\n"
            "    try:\n"
            "        assert payload is not None\n"
            "        att = payload['attachments'][0]\n"
            "        assert att.get('color') == '#36a64f', \\\n"
            "            f\"default color wrong: {att.get('color')!r}\"\n"
            "        red_payload = format_slack_message('Error', 'Failed', color='#e01e5a')\n"
            "        red_att = red_payload['attachments'][0]\n"
            "        assert red_att.get('color') == '#e01e5a', \\\n"
            "            f\"custom color wrong: {red_att.get('color')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: default green and custom color work')\n"
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
            + FORMAT_SLACK_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — format_discord_embed
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md(
            "# Day 029 — Exercise 2: format_discord_embed\n\n"
            "**What you'll build:** `format_discord_embed(title, description, color=0x00b0f4) -> dict` — "
            "builds a Discord embed dict. The embed is the inner object; to send it, "
            "wrap it in `{'embeds': [embed_dict]}`.\n\n"
            "**Why it matters:** Discord and Slack use different payload shapes and "
            "colour formats. Discord's integer colour (0x00b0f4 = 45300) versus "
            "Slack's hex string ('#36a64f') is the most common source of confusion "
            "when supporting both platforms."
        ),
        md("## Your Implementation"),
        code(
            "def format_discord_embed(\n"
            "    title: str,\n"
            "    description: str,\n"
            "    color: int = 0x00b0f4,\n"
            ") -> dict:\n"
            '    """\n'
            "    Build a Discord embed dict.\n\n"
            "    Args:\n"
            "        title:       Bold headline of the embed.\n"
            "        description: Body text of the embed.\n"
            "        color:       Integer colour (e.g. 0x00b0f4 = light blue).\n\n"
            "    Returns:\n"
            "        Dict with keys: title, description, color.\n"
            "        Wrap in {'embeds': [result]} before POSTing to Discord.\n"
            '    """\n'
            "    # TODO: return {'title': title, 'description': description, 'color': color}\n"
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
            "        assert 'format_discord_embed' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: format_discord_embed defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    embed = None\n"
            "\n"
            "    # Check 2: returns a dict\n"
            "    try:\n"
            "        embed = format_discord_embed('Report Ready', 'Sales data processed.')\n"
            "        assert isinstance(embed, dict), \\\n"
            "            f'expected dict, got {type(embed)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a dict')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: has title and description\n"
            "    try:\n"
            "        assert embed is not None\n"
            "        assert embed.get('title') == 'Report Ready', \\\n"
            "            f\"title wrong: {embed.get('title')!r}\"\n"
            "        assert embed.get('description') == 'Sales data processed.', \\\n"
            "            f\"description wrong: {embed.get('description')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: title and description correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: color is an int (not a string)\n"
            "    try:\n"
            "        assert embed is not None\n"
            "        c = embed.get('color')\n"
            "        assert isinstance(c, int), \\\n"
            "            f'color should be int, got {type(c)}: {c!r}'\n"
            "        assert c == 0x00b0f4, \\\n"
            "            f'default color wrong: {c} (expected {0x00b0f4})'\n"
            "        passed += 1; print(f'\\u2705 Check 4: color is int ({c})')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: custom color works\n"
            "    try:\n"
            "        red = format_discord_embed('Error', 'Something failed.', color=0xe74c3c)\n"
            "        assert red.get('color') == 0xe74c3c, \\\n"
            "            f'custom color wrong: {red.get(\"color\")!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: custom color 0xe74c3c works')\n"
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
            + FORMAT_DISCORD_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — truncate_for_chat
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md(
            "# Day 029 — Exercise 3: truncate_for_chat\n\n"
            "**What you'll build:** `truncate_for_chat(text, max_chars=2000) -> str` — "
            "returns text unchanged if it fits within max_chars, or truncates it to "
            "`text[:max_chars - 3] + '...'` so the result is exactly max_chars characters.\n\n"
            "**Why it matters:** Discord caps message content at 2000 characters and embed "
            "descriptions at 4096. Exceeding these limits causes a 400 error. AI summaries "
            "should fit within these limits naturally, but truncation is the hard backstop "
            "that prevents send failures when the LLM is unusually verbose."
        ),
        md("## Your Implementation"),
        code(
            "def truncate_for_chat(text: str, max_chars: int = 2000) -> str:\n"
            '    """\n'
            "    Truncate text to at most max_chars characters.\n\n"
            "    Args:\n"
            "        text:      The string to truncate.\n"
            "        max_chars: Maximum character count (default 2000).\n\n"
            "    Returns:\n"
            "        text unchanged if len(text) <= max_chars, else text[:max_chars-3] + '...'\n"
            "        The returned string is always at most max_chars characters long.\n"
            '    """\n'
            "    # TODO: if len(text) <= max_chars: return text\n"
            "    # TODO: return text[:max_chars - 3] + '...'\n"
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
            "        assert 'truncate_for_chat' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: truncate_for_chat defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    # Check 2: short text returned unchanged\n"
            "    try:\n"
            "        short = 'Hello, world!'\n"
            "        result = truncate_for_chat(short, max_chars=2000)\n"
            "        assert result == short, \\\n"
            "            f'short text should be unchanged: {result!r}'\n"
            "        passed += 1; print('\\u2705 Check 2: short text returned unchanged')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: long text is truncated and ends with '...'\n"
            "    try:\n"
            "        long_text = 'A' * 3000\n"
            "        result = truncate_for_chat(long_text, max_chars=2000)\n"
            "        assert result.endswith('...'), \\\n"
            "            f'truncated text should end with ...: {result[-10:]!r}'\n"
            "        passed += 1; print('\\u2705 Check 3: truncated text ends with ...')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: truncated length is exactly max_chars\n"
            "    try:\n"
            "        long_text = 'B' * 3000\n"
            "        result = truncate_for_chat(long_text, max_chars=2000)\n"
            "        assert len(result) == 2000, \\\n"
            "            f'truncated length should be 2000, got {len(result)}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: truncated length is exactly 2000')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: custom max_chars works\n"
            "    try:\n"
            "        result = truncate_for_chat('C' * 200, max_chars=100)\n"
            "        assert len(result) == 100, \\\n"
            "            f'custom max_chars=100 failed: len={len(result)}'\n"
            "        assert result.endswith('...')\n"
            "        # text exactly at limit — should NOT be truncated\n"
            "        exact = truncate_for_chat('D' * 100, max_chars=100)\n"
            "        assert len(exact) == 100 and not exact.endswith('...'), \\\n"
            "            f'exact-length text should be unchanged: {exact[-5:]!r}'\n"
            "        passed += 1; print('\\u2705 Check 5: custom max_chars and boundary work')\n"
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
            + TRUNCATE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — ai_summarize_for_chat
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 029 — Exercise 4: ai_summarize_for_chat\n\n"
            "**What you'll build:** `ai_summarize_for_chat(content, platform='slack', model='llama3.2') -> str` — "
            "summarises content into a short, platform-appropriate chat notification using ollama.chat.\n\n"
            "**Why it matters:** A notification bot that sends raw AI report output to "
            "Slack is useless — walls of text get ignored. ai_summarize_for_chat converts "
            "long content into 2–3 sentences tuned for the target platform, leading with "
            "the most important fact."
        ),
        code("import ollama"),
        md("## Your Implementation"),
        code(
            "def ai_summarize_for_chat(\n"
            "    content: str,\n"
            "    platform: str = 'slack',\n"
            "    model: str = 'llama3.2',\n"
            ") -> str:\n"
            '    """\n'
            "    Summarise content for a short, platform-appropriate chat notification.\n\n"
            "    Args:\n"
            "        content:  The full text to summarise.\n"
            "        platform: Target platform ('slack' or 'discord') — used in prompt.\n"
            "        model:    Ollama model name.\n\n"
            "    Returns:\n"
            "        A short notification summary string.\n"
            '    """\n'
            "    # System: notification writer for {platform}; under 300 chars; no headers or bullets\n"
            "    # User: f'Summarise this for a {platform} notification:\\n\\n{content[:3000]}'\n"
            "    # TODO: call ollama.chat and return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    SAMPLE = (\n"
            "        'Quarterly sales report completed. '\n"
            "        'Total revenue: $12,450. Best performer: Epsilon X with $3,600 in Q4. '\n"
            "        'All five products showed positive growth compared to Q1. '\n"
            "        'Recommended action: expand Epsilon X production for next quarter.'\n"
            "    )\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_summarize_for_chat' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_summarize_for_chat defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        result = ai_summarize_for_chat(SAMPLE)\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result is non-empty\n"
            "    try:\n"
            "        assert result is not None\n"
            "        assert len(result.strip()) > 10, \\\n"
            "            f'summary too short: {result!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 3: summary is {len(result)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: discord platform also works\n"
            "    try:\n"
            "        discord_result = ai_summarize_for_chat(SAMPLE, platform='discord')\n"
            "        assert isinstance(discord_result, str) and len(discord_result) > 5\n"
            "        passed += 1; print('\\u2705 Check 4: works with platform=discord')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: summary is shorter than the original content\n"
            "    try:\n"
            "        assert result is not None\n"
            "        assert len(result) < len(SAMPLE), \\\n"
            "            f'summary ({len(result)} chars) should be shorter than input ({len(SAMPLE)} chars)'\n"
            "        passed += 1; print(f'\\u2705 Check 5: summary shorter than input ({len(result)} < {len(SAMPLE)})')\n"
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
            + AI_SUMMARIZE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — build_notification
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md(
            "# Day 029 — Exercise 5: build_notification\n\n"
            "**What you'll build:** `build_notification(event_type, data, model='llama3.2') -> dict` — "
            "the pipeline capstone. Takes an event type and data dict, generates an AI summary, "
            "and returns a dict with Slack and Discord payloads ready to send.\n\n"
            "**Why it matters:** build_notification is the single entry point for turning "
            "any automation event into a multi-platform notification. One call produces "
            "payloads for both Slack and Discord — the NotificationBot just adds the "
            "HTTP send step."
        ),
        code("import ollama"),
        md("## Provided: Helper Functions"),
        code(
            FORMAT_SLACK_IMPL + "\n\n\n"
            + FORMAT_DISCORD_IMPL + "\n\n\n"
            + TRUNCATE_IMPL + "\n\n\n"
            + AI_SUMMARIZE_IMPL
        ),
        md("## Your Implementation"),
        code(
            "def build_notification(\n"
            "    event_type: str,\n"
            "    data: dict,\n"
            "    model: str = 'llama3.2',\n"
            ") -> dict:\n"
            '    """\n'
            "    Build Slack and Discord notification payloads for an event.\n\n"
            "    Args:\n"
            "        event_type: Dot-notation event identifier (e.g. 'report.generated').\n"
            "        data:       Dict of event details {key: value}.\n"
            "        model:      Ollama model name.\n\n"
            "    Returns:\n"
            "        Dict with keys: event_type, title, summary,\n"
            "                        slack_payload, discord_payload.\n"
            '    """\n'
            "    # TODO: content = f'Event: {event_type}\\n\\nData:\\n'\n"
            "    #        + '\\n'.join(f'  {k}: {v}' for k, v in data.items())\n"
            "    # TODO: summary = ai_summarize_for_chat(content, platform='slack', model=model)\n"
            "    # TODO: title = f'[{event_type.upper()}] Notification'\n"
            "    # TODO: slack_payload = format_slack_message(title, summary)\n"
            "    # TODO: discord_payload = {'embeds': [format_discord_embed(title, truncate_for_chat(summary, 4096))]}\n"
            "    # TODO: return {event_type, title, summary, slack_payload, discord_payload}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    EVENT = 'report.generated'\n"
            "    DATA  = {'rows': 500, 'output': '/tmp/report.xlsx', 'duration_s': 12}\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'build_notification' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_notification defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a dict with all required keys\n"
            "    try:\n"
            "        result = build_notification(EVENT, DATA)\n"
            "        assert isinstance(result, dict), \\\n"
            "            f'expected dict, got {type(result)}'\n"
            "        for k in ('event_type', 'title', 'summary', 'slack_payload', 'discord_payload'):\n"
            "            assert k in result, f\"result missing '{k}': {list(result)}\"\n"
            "        passed += 1; print('\\u2705 Check 2: all required keys present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: event_type and title correct\n"
            "    try:\n"
            "        assert result is not None\n"
            "        assert result['event_type'] == EVENT, \\\n"
            "            f\"event_type wrong: {result['event_type']!r}\"\n"
            "        assert result['title'] == '[REPORT.GENERATED] Notification', \\\n"
            "            f\"title wrong: {result['title']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 3: event_type and title correct\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: slack_payload has 'attachments' structure\n"
            "    try:\n"
            "        assert result is not None\n"
            "        sp = result['slack_payload']\n"
            "        assert 'attachments' in sp, \\\n"
            "            f\"slack_payload missing 'attachments': {list(sp)}\"\n"
            "        att = sp['attachments'][0]\n"
            "        assert att.get('title') == result['title'], \\\n"
            "            f\"slack title mismatch: {att.get('title')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: slack_payload has correct attachments')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: discord_payload has 'embeds' structure\n"
            "    try:\n"
            "        assert result is not None\n"
            "        dp = result['discord_payload']\n"
            "        assert 'embeds' in dp, \\\n"
            "            f\"discord_payload missing 'embeds': {list(dp)}\"\n"
            "        embed = dp['embeds'][0]\n"
            "        assert embed.get('title') == result['title'], \\\n"
            "            f\"discord embed title mismatch: {embed.get('title')!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: discord_payload has correct embeds')\n"
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
            + BUILD_NOTIF_IMPL + "\n"
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
            "# Day 029 Project: NotificationBot\n\n"
            "## What You're Building\n\n"
            "A `NotificationBot` class that:\n"
            "1. Accepts optional Slack and Discord webhook URLs\n"
            "2. Generates AI-powered notifications with `build_notification`\n"
            "3. Exposes `preview(event_type, data)` — builds payloads without sending\n"
            "4. Exposes `notify(event_type, data)` — builds payloads and POSTs to webhooks\n\n"
            "## Project Requirements\n\n"
            "1. Implement `NotificationBot` with `preview` and `notify` methods\n"
            "2. Call `bot.preview(...)` for at least one event and store as `result`\n"
            "3. Verify with `_run_project_checks()`\n\n"
            "Webhook URLs are optional — `preview` works without them. "
            "If you have real Slack or Discord webhook URLs, try `notify` too!"
        ),
        code("import ollama"),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "Implement `NotificationBot` using the helper functions above."
        ),
        code(
            "class NotificationBot:\n"
            "    def __init__(\n"
            "        self,\n"
            "        slack_url: str | None = None,\n"
            "        discord_url: str | None = None,\n"
            "        model: str = 'llama3.2',\n"
            "    ):\n"
            "        self.slack_url   = slack_url\n"
            "        self.discord_url = discord_url\n"
            "        self.model       = model\n"
            "\n"
            "    def preview(self, event_type: str, data: dict) -> dict:\n"
            "        # TODO: return build_notification(event_type, data, model=self.model)\n"
            "        pass\n"
            "\n"
            "    def notify(self, event_type: str, data: dict) -> dict:\n"
            "        # TODO: result = self.preview(event_type, data)\n"
            "        # TODO: result['sent'] = []\n"
            "        # TODO: if self.slack_url: POST to slack_url; append 'slack:{status}'\n"
            "        # TODO: if self.discord_url: POST to discord_url; append 'discord:{status}'\n"
            "        # TODO: return result\n"
            "        pass"
        ),
        md("## Events to Test"),
        code(
            "# Test with a 'preview' — no webhook URLs needed\n"
            "# bot = NotificationBot()\n"
            "# result = bot.preview(\n"
            "#     event_type='report.generated',\n"
            "#     data={'rows': 500, 'output': '/tmp/report.xlsx', 'duration_s': 12},\n"
            "# )\n"
            "# print(f\"Title: {result['title']}\")\n"
            "# print(f\"Summary: {result['summary']}\")\n"
            "# print(f\"Slack payload keys: {list(result['slack_payload'])}\")\n"
            "\n"
            "# To send to real channels (requires actual webhook URLs):\n"
            "# bot = NotificationBot(\n"
            "#     slack_url=os.environ.get('SLACK_WEBHOOK'),\n"
            "#     discord_url=os.environ.get('DISCORD_WEBHOOK'),\n"
            "# )\n"
            "# result = bot.notify('report.generated', {'rows': 500})"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: NotificationBot has required methods\n"
            "    try:\n"
            "        assert 'NotificationBot' in globals()\n"
            "        for m in ('preview', 'notify'):\n"
            "            assert hasattr(NotificationBot, m), \\\n"
            "                f'NotificationBot missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: preview and notify methods present')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: bot is an instance\n"
            "    try:\n"
            "        assert 'bot' in globals()\n"
            "        assert isinstance(bot, NotificationBot)\n"
            "        passed += 1; print('\\u2705 Check 2: bot is a NotificationBot')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result dict has required keys\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        for k in ('event_type', 'title', 'summary',\n"
            "                  'slack_payload', 'discord_payload'):\n"
            "            assert k in result, f\"result missing '{k}'\"\n"
            "        passed += 1; print('\\u2705 Check 3: result has all required keys')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: slack_payload has attachments\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        assert 'attachments' in result['slack_payload'], \\\n"
            "            f\"slack_payload missing attachments: {list(result['slack_payload'])}\"\n"
            "        passed += 1; print('\\u2705 Check 4: slack_payload has attachments')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: discord_payload has embeds\n"
            "    try:\n"
            "        assert 'result' in globals()\n"
            "        assert 'embeds' in result['discord_payload'], \\\n"
            "            f\"discord_payload missing embeds: {list(result['discord_payload'])}\"\n"
            "        passed += 1; print('\\u2705 Check 5: discord_payload has embeds')\n"
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
            "- Add a `color_for_event(event_type) -> str` helper that returns "
            "red ('#e01e5a') for event types ending in '.failed' or '.error', "
            "yellow for '.warning', and green for everything else\n"
            "- Add a `notify_many(events)` method that takes a list of (event_type, data) "
            "tuples and sends them all, returning a list of results\n"
            "- Add Slack Block Kit support: a `format_slack_blocks(title, body, footer)` "
            "function that uses the blocks API instead of attachments\n"
            "- Add Discord fields: extend `format_discord_embed` to accept an optional "
            "`fields: list[dict]` parameter for structured key-value display\n"
            "- Add retry logic: if requests.post raises a ConnectionError, retry up to 3 times "
            "with a 2-second delay (Day 31 preview)"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    imports = "import ollama"

    all_code = imports + "\n\n\n" + ALL_IMPLS + "\n\n\n" + NOTIF_BOT_IMPL

    return [
        md(
            "# Day 029 Project Solution — NotificationBot\n\n"
            "A `NotificationBot` that converts automation events into AI-generated "
            "Slack and Discord notifications."
        ),
        code(all_code),
        md("## Action 1 — Build Slack and Discord Payloads Directly"),
        code(
            "# Slack green success payload\n"
            "slack_ok = format_slack_message(\n"
            "    title='\\u2705 Report Generated',\n"
            "    body='Sales report for 5 products completed successfully.',\n"
            "    color='#36a64f',\n"
            ")\n"
            "print('Slack payload keys:', list(slack_ok))\n"
            "print('Attachment title: ', slack_ok['attachments'][0]['title'])\n"
            "print('Attachment color: ', slack_ok['attachments'][0]['color'])\n"
            "\n"
            "# Discord blue info embed\n"
            "discord_embed = format_discord_embed(\n"
            "    title='\\U0001f4ca Sales Report Ready',\n"
            "    description='5 products analysed. Epsilon X leads with $3,600 in Q4.',\n"
            "    color=0x2ecc71,\n"
            ")\n"
            "discord_payload = {'embeds': [discord_embed]}\n"
            "print('\\nDiscord embed title:', discord_payload['embeds'][0]['title'])\n"
            "print('Discord embed color:', discord_payload['embeds'][0]['color'])\n"
            "\n"
            "# Truncation guard\n"
            "long_body = 'X' * 3000\n"
            "safe = truncate_for_chat(long_body, max_chars=2000)\n"
            "print(f'\\nTruncated {len(long_body)} → {len(safe)} chars, ends with: {safe[-5:]!r}')"
        ),
        md("## Action 2 — Generate AI-Powered Notification"),
        code(
            "bot = NotificationBot()\n"
            "\n"
            "result = bot.preview(\n"
            "    event_type='report.generated',\n"
            "    data={\n"
            "        'rows_analyzed': 5,\n"
            "        'top_product': 'Epsilon X',\n"
            "        'total_revenue': 13350,\n"
            "        'output': '/tmp/day028_report.xlsx',\n"
            "    },\n"
            ")\n"
            "print('Event type:', result['event_type'])\n"
            "print('Title:     ', result['title'])\n"
            "print('Summary:   ', result['summary'])"
        ),
        md("## Action 3 — Inspect Payloads and Verify"),
        code(
            "# Verify slack payload\n"
            "sp = result['slack_payload']\n"
            "print('Slack attachment title:', sp['attachments'][0]['title'])\n"
            "print('Slack attachment body: ', sp['attachments'][0]['text'][:80])\n"
            "\n"
            "# Verify discord payload\n"
            "dp = result['discord_payload']\n"
            "print('\\nDiscord embeds count:', len(dp['embeds']))\n"
            "print('Discord embed title: ', dp['embeds'][0]['title'])\n"
            "print('Discord embed desc:  ', dp['embeds'][0]['description'][:80])\n"
            "\n"
            "# Payloads would be sent like this (commented — no real webhook URL):\n"
            "# import requests\n"
            "# requests.post(SLACK_WEBHOOK, json=sp, timeout=10).raise_for_status()\n"
            "# requests.post(DISCORD_WEBHOOK, json=dp, timeout=10).raise_for_status()\n"
            "\n"
            "print('\\nNotification bot complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 029 notebooks...")
    ex_dir = DAY_DIR / "exercises"
    proj_dir = DAY_DIR / "project"
    sol_dir = proj_dir / "solution"
    for d in (ex_dir, proj_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    write_nb(ex_dir / "exercise_01.ipynb", ex01())
    write_nb(ex_dir / "exercise_02.ipynb", ex02())
    write_nb(ex_dir / "exercise_03.ipynb", ex03())
    write_nb(ex_dir / "exercise_04.ipynb", ex04())
    write_nb(ex_dir / "exercise_05.ipynb", ex05())
    write_nb(proj_dir / "project.ipynb", project_nb())
    write_nb(sol_dir / "solution.ipynb", solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
