#!/usr/bin/env python3
"""Generate all Day 025 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_025"

_cid = 0

# Sample email used across exercises 2, 3, 5 (RFC 2822, text/plain)
SAMPLE_EMAIL = (
    "From: alice@example.com\n"
    "To: bob@example.com\n"
    "Subject: Project Kickoff Meeting\n"
    "Message-ID: <20260717090000.alice@example.com>\n"
    "Date: Mon, 17 Jul 2026 09:00:00 +0000\n"
    "Content-Type: text/plain; charset=utf-8\n"
    "\n"
    "Hi Bob,\n"
    "\n"
    "Can we schedule a kickoff meeting for the new project?\n"
    "I am available Tuesday or Wednesday afternoon.\n"
    "\n"
    "Best,\n"
    "Alice\n"
)


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
# Solution implementations (imports in each notebook's imports cell)
# ---------------------------------------------------------------------------

BUILD_EMAIL_IMPL = """\
def build_email_message(
    to: str,
    subject: str,
    body: str,
    from_addr: str = "sender@example.com",
) -> email.message.EmailMessage:
    msg = email.message.EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg"""

PARSE_EMAIL_IMPL = """\
def parse_email_string(raw_email: str) -> email.message.Message:
    return email.message_from_string(raw_email)"""

GET_BODY_IMPL = """\
def get_email_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                raw = part.get_payload(decode=True)
                if raw is not None:
                    charset = part.get_content_charset() or "utf-8"
                    return raw.decode(charset, errors="replace")
                return str(part.get_payload() or "")
    raw = msg.get_payload(decode=True)
    if raw is not None:
        charset = msg.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")
    return str(msg.get_payload() or "")"""

DRAFT_REPLY_IMPL = """\
def draft_reply(
    original_subject: str,
    original_body: str,
    context: str,
    model: str = "llama3.2",
) -> str:
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional email assistant. "
                    "Write concise, polite email replies. "
                    "Match the tone of the original. "
                    "Return only the email body — no subject line, no 'Subject:' prefix."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original subject: {original_subject}\\n\\n"
                    f"Original message:\\n{original_body}\\n\\n"
                    f"Context for your reply: {context}\\n\\n"
                    "Write a reply email body:"
                ),
            },
        ],
    )
    return response["message"]["content"]"""

BUILD_REPLY_IMPL = """\
def build_reply_email(
    original_msg: email.message.Message,
    reply_body: str,
    from_addr: str,
    to_addr: str | None = None,
) -> email.message.EmailMessage:
    reply = email.message.EmailMessage()
    subject = original_msg.get("Subject", "")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
    reply["Subject"] = subject
    reply["From"] = from_addr
    reply["To"] = to_addr or original_msg.get("From", "")
    msg_id = original_msg.get("Message-ID")
    if msg_id:
        reply["In-Reply-To"] = msg_id
    reply.set_content(reply_body)
    return reply"""

ALL_IMPLS = (
    BUILD_EMAIL_IMPL + "\n\n\n"
    + PARSE_EMAIL_IMPL + "\n\n\n"
    + GET_BODY_IMPL + "\n\n\n"
    + DRAFT_REPLY_IMPL + "\n\n\n"
    + BUILD_REPLY_IMPL
)

EMAIL_DRAFTER_IMPL = """\
class EmailDrafter:
    def parse(self, raw_email: str) -> email.message.Message:
        return parse_email_string(raw_email)

    def draft(
        self,
        msg: email.message.Message,
        context: str,
        model: str = "llama3.2",
    ) -> str:
        body = get_email_body(msg)
        return draft_reply(
            original_subject=msg.get("Subject", ""),
            original_body=body,
            context=context,
            model=model,
        )

    def build_reply(
        self,
        original_msg: email.message.Message,
        reply_body: str,
        from_addr: str,
    ) -> email.message.EmailMessage:
        return build_reply_email(original_msg, reply_body, from_addr=from_addr)

    def run_pipeline(
        self,
        raw_email: str,
        context: str,
        from_addr: str,
        model: str = "llama3.2",
    ) -> dict:
        parsed = self.parse(raw_email)
        reply_body = self.draft(parsed, context=context, model=model)
        reply_msg = self.build_reply(parsed, reply_body, from_addr=from_addr)
        return {"parsed": parsed, "reply_body": reply_body, "reply_msg": reply_msg}\
"""


# ---------------------------------------------------------------------------
# Exercise 01 — build_email_message
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md(
            "# Day 025 — Exercise 1: build_email_message\n\n"
            "**What you'll build:** `build_email_message(to, subject, body, from_addr)` — "
            "constructs a ready-to-send `EmailMessage` object using Python's stdlib `email` module.\n\n"
            "**Why it matters:** `EmailMessage` (Python 3.6+) is the modern way to build emails "
            "in Python — it sets `Content-Type`, handles encoding, and works directly with "
            "`smtplib.send_message()`. No third-party packages needed."
        ),
        code("import email\nimport email.message"),
        md("## Your Implementation"),
        code(
            "def build_email_message(\n"
            "    to: str,\n"
            "    subject: str,\n"
            "    body: str,\n"
            '    from_addr: str = "sender@example.com",\n'
            ") -> email.message.EmailMessage:\n"
            '    """\n'
            "    Build a plain-text email message.\n\n"
            "    Args:\n"
            "        to:        Recipient email address.\n"
            "        subject:   Email subject line.\n"
            "        body:      Plain-text body.\n"
            "        from_addr: Sender address (default: sender@example.com).\n\n"
            "    Returns:\n"
            "        email.message.EmailMessage ready for smtplib.send_message().\n"
            '    """\n'
            "    # TODO: msg = email.message.EmailMessage()\n"
            '    # TODO: msg["From"] = from_addr\n'
            '    # TODO: msg["To"] = to\n'
            '    # TODO: msg["Subject"] = subject\n'
            "    # TODO: msg.set_content(body)\n"
            "    # TODO: return msg\n"
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
            "        assert 'build_email_message' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_email_message defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    msg = None\n"
            "\n"
            "    # Check 2: returns an EmailMessage\n"
            "    try:\n"
            "        msg = build_email_message(\n"
            "            'bob@example.com', 'Hello', 'Hello Bob!'\n"
            "        )\n"
            "        assert isinstance(msg, email.message.Message), \\\n"
            "            f'expected EmailMessage, got {type(msg)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns an EmailMessage')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: headers correct\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None (Check 2 failed)'\n"
            "        assert msg['Subject'] == 'Hello', \\\n"
            "            f\"Subject wrong: {msg['Subject']!r}\"\n"
            "        assert msg['To'] == 'bob@example.com', \\\n"
            "            f\"To wrong: {msg['To']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: Subject and To headers correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: default from_addr used\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None'\n"
            "        assert msg['From'] == 'sender@example.com', \\\n"
            "            f\"From should be default, got {msg['From']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: default from_addr='sender@example.com'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: body text is in the payload\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None'\n"
            "        payload = msg.get_payload()\n"
            "        if isinstance(payload, bytes):\n"
            "            payload = payload.decode('utf-8', errors='replace')\n"
            "        assert 'Hello Bob!' in str(payload), \\\n"
            "            f\"body not found in payload: {payload!r}\"\n"
            "        passed += 1; print('\\u2705 Check 5: body text present in payload')\n"
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
            + BUILD_EMAIL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — parse_email_string
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    sample_repr = repr(SAMPLE_EMAIL)
    return [
        md(
            "# Day 025 — Exercise 2: parse_email_string\n\n"
            "**What you'll build:** `parse_email_string(raw_email)` — parses a raw RFC 2822 "
            "email string into an `email.message.Message` object.\n\n"
            "**Why it matters:** IMAP servers return raw email bytes. After decoding to a string, "
            "`email.message_from_string()` turns the flat text into a structured object where "
            "every header is a keyed attribute and the body is separated cleanly."
        ),
        code("import email"),
        md("## Your Implementation"),
        code(
            "def parse_email_string(raw_email: str) -> email.message.Message:\n"
            '    """\n'
            "    Parse a raw RFC 2822 email string into a Message object.\n\n"
            "    Args:\n"
            "        raw_email: Full email text including headers and body.\n\n"
            "    Returns:\n"
            "        email.message.Message with accessible headers and payload.\n"
            '    """\n'
            "    # TODO: return email.message_from_string(raw_email)\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"SAMPLE_EMAIL = {sample_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'parse_email_string' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: parse_email_string defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    msg = None\n"
            "\n"
            "    # Check 2: returns a Message object\n"
            "    try:\n"
            "        msg = parse_email_string(SAMPLE_EMAIL)\n"
            "        assert isinstance(msg, email.message.Message), \\\n"
            "            f'expected Message, got {type(msg)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns an email.message.Message')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: From header correct\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None (Check 2 failed)'\n"
            "        assert msg['From'] == 'alice@example.com', \\\n"
            "            f\"From wrong: {msg['From']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: From='alice@example.com'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: Subject header correct\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None'\n"
            "        assert msg['Subject'] == 'Project Kickoff Meeting', \\\n"
            "            f\"Subject wrong: {msg['Subject']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: Subject='Project Kickoff Meeting'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: Message-ID header accessible\n"
            "    try:\n"
            "        assert msg is not None, 'msg is None'\n"
            "        msg_id = msg.get('Message-ID')\n"
            "        assert msg_id is not None, 'Message-ID header not found'\n"
            "        assert 'alice@example.com' in msg_id, \\\n"
            "            f\"Message-ID doesn't look right: {msg_id!r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 5: Message-ID accessible: {msg_id}')\n"
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
            + PARSE_EMAIL_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — get_email_body
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    sample_repr = repr(SAMPLE_EMAIL)
    return [
        md(
            "# Day 025 — Exercise 3: get_email_body\n\n"
            "**What you'll build:** `get_email_body(msg)` — extracts the plain-text body "
            "from a parsed email message, handling both single-part and multipart emails.\n\n"
            "**Why it matters:** Emails arrive in many formats: plain text, HTML, "
            "or multipart (both). A robust body extractor walks the MIME structure and "
            "always returns a clean string — never None — so AI drafting can work "
            "on any email regardless of format."
        ),
        code("import email"),
        md("## Your Implementation"),
        code(
            "def get_email_body(msg: email.message.Message) -> str:\n"
            '    """\n'
            "    Extract the plain-text body from a parsed email message.\n\n"
            "    Args:\n"
            "        msg: Parsed email.message.Message object.\n\n"
            "    Returns:\n"
            "        Plain text body as a string. Empty string if no body found.\n"
            "        Handles both single-part and multipart messages.\n"
            '    """\n'
            "    # For multipart: walk() all parts, find text/plain, extract\n"
            "    # For single-part: get_payload(decode=True) → bytes (if encoded)\n"
            "    #                  get_payload()            → str  (if not encoded)\n"
            "    # TODO: if msg.is_multipart():\n"
            "    #           for part in msg.walk():\n"
            "    #               if part.get_content_type() == 'text/plain':\n"
            "    #                   raw = part.get_payload(decode=True)\n"
            "    #                   if raw is not None:\n"
            "    #                       charset = part.get_content_charset() or 'utf-8'\n"
            "    #                       return raw.decode(charset, errors='replace')\n"
            "    #                   return str(part.get_payload() or '')\n"
            "    # TODO: raw = msg.get_payload(decode=True)\n"
            "    # TODO: if raw is not None:\n"
            "    #           charset = msg.get_content_charset() or 'utf-8'\n"
            "    #           return raw.decode(charset, errors='replace')\n"
            "    # TODO: return str(msg.get_payload() or '')\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"SAMPLE_EMAIL = {sample_repr}\n"
            "\n"
            "EMPTY_BODY_EMAIL = (\n"
            "    'From: x@x.com\\n'\n"
            "    'To: y@y.com\\n'\n"
            "    'Subject: Empty\\n'\n"
            "    '\\n'\n"
            ")\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'get_email_body' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: get_email_body defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    body = None\n"
            "\n"
            "    # Check 2: returns a string from SAMPLE_EMAIL\n"
            "    try:\n"
            "        msg = email.message_from_string(SAMPLE_EMAIL)\n"
            "        body = get_email_body(msg)\n"
            "        assert isinstance(body, str), f'expected str, got {type(body)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: body contains expected text\n"
            "    try:\n"
            "        assert body is not None, 'body is None (Check 2 failed)'\n"
            "        assert 'kickoff meeting' in body.lower(), \\\n"
            "            f\"'kickoff meeting' not found in body: {body!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 3: body contains 'kickoff meeting'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: body is non-empty for SAMPLE_EMAIL\n"
            "    try:\n"
            "        assert body is not None, 'body is None'\n"
            "        assert len(body.strip()) > 0, f'body is empty: {body!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: body is {len(body.strip())} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty-body email returns a string without crashing\n"
            "    try:\n"
            "        empty_msg = email.message_from_string(EMPTY_BODY_EMAIL)\n"
            "        empty_body = get_email_body(empty_msg)\n"
            "        assert isinstance(empty_body, str), \\\n"
            "            f'expected str for empty email, got {type(empty_body)}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: empty-body email returns {empty_body!r}')\n"
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
            + GET_BODY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — draft_reply
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 025 — Exercise 4: draft_reply\n\n"
            "**What you'll build:** `draft_reply(original_subject, original_body, context, model)` "
            "— uses the LLM to draft a professional email reply given the original message "
            "and a context hint from you.\n\n"
            "**Why it matters:** AI email drafting works exactly like Day 6's prompt templates: "
            "the system prompt establishes the persona (professional email assistant), "
            "the user prompt provides the data (original email + your intent). "
            "The LLM does the writing; you do the reviewing."
        ),
        code("import ollama"),
        md("## Your Implementation"),
        code(
            "def draft_reply(\n"
            "    original_subject: str,\n"
            "    original_body: str,\n"
            "    context: str,\n"
            '    model: str = "llama3.2",\n'
            ") -> str:\n"
            '    """\n'
            "    Draft a professional email reply using the LLM.\n\n"
            "    Args:\n"
            "        original_subject: Subject line of the incoming email.\n"
            "        original_body:    Body text of the incoming email.\n"
            "        context:          Your intent or instructions for the reply\n"
            "                          (e.g. 'Accept the meeting, propose Thursday').\n"
            "        model:            Ollama model name.\n\n"
            "    Returns:\n"
            "        Drafted reply body as a string (no subject line prefix).\n"
            '    """\n'
            "    # TODO: build a system prompt: 'professional email assistant, body only'\n"
            "    # TODO: build user prompt with original_subject, original_body, context\n"
            "    # TODO: call ollama.chat (no format='json' — free-form text reply)\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "SUBJECT = 'Project Kickoff Meeting'\n"
            "BODY    = 'Hi, can we schedule a kickoff meeting for the new project?'\n"
            "CONTEXT = 'Accept the meeting, suggest Thursday at 2pm.'\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'draft_reply' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: draft_reply defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string (1 LLM call)\n"
            "    try:\n"
            "        result = draft_reply(SUBJECT, BODY, CONTEXT)\n"
            "        assert isinstance(result, str), f'expected str, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result is non-empty\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 2 failed)'\n"
            "        assert len(result) > 0, 'result is empty string'\n"
            "        passed += 1; print('\\u2705 Check 3: result is non-empty')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: result is a meaningful length (> 20 chars)\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        assert len(result) > 20, \\\n"
            "            f'result too short ({len(result)} chars): {result!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: draft is {len(result)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works with empty inputs (no crash) — 1 LLM call\n"
            "    try:\n"
            "        empty_result = draft_reply('', '', 'Acknowledge receipt')\n"
            "        assert isinstance(empty_result, str), \\\n"
            "            f'expected str for empty inputs, got {type(empty_result)}'\n"
            "        passed += 1; print('\\u2705 Check 5: works with empty subject/body')\n"
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
            + DRAFT_REPLY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — build_reply_email
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    sample_repr = repr(SAMPLE_EMAIL)
    return [
        md(
            "# Day 025 — Exercise 5: build_reply_email\n\n"
            "**What you'll build:** `build_reply_email(original_msg, reply_body, from_addr, to_addr)` "
            "— constructs a properly threaded reply `EmailMessage`: `Re:` subject, "
            "`In-Reply-To` header, correct `From`/`To`.\n\n"
            "**Why it matters:** Email clients use `In-Reply-To` and `References` to thread "
            "messages. Without these, your AI reply lands as a new conversation rather than "
            "a response. `Re:` prefix prevention stops double-`Re:` accumulation."
        ),
        code("import email\nimport email.message"),
        md("## Your Implementation"),
        code(
            "def build_reply_email(\n"
            "    original_msg: email.message.Message,\n"
            "    reply_body: str,\n"
            "    from_addr: str,\n"
            "    to_addr: str | None = None,\n"
            ") -> email.message.EmailMessage:\n"
            '    """\n'
            "    Construct a threaded reply EmailMessage.\n\n"
            "    Args:\n"
            "        original_msg: The parsed incoming email to reply to.\n"
            "        reply_body:   The plain-text body of the reply.\n"
            "        from_addr:    The sender address for the reply.\n"
            "        to_addr:      Override recipient; if None, reply to original From.\n\n"
            "    Returns:\n"
            "        EmailMessage with Re: subject, In-Reply-To header, correct From/To.\n"
            '    """\n'
            "    # TODO: reply = email.message.EmailMessage()\n"
            "    # TODO: subject = original_msg.get('Subject', '')\n"
            "    # TODO: if not subject.startswith('Re:'): subject = f'Re: {subject}'\n"
            "    # TODO: reply['Subject'] = subject\n"
            "    # TODO: reply['From'] = from_addr\n"
            "    # TODO: reply['To'] = to_addr or original_msg.get('From', '')\n"
            "    # TODO: msg_id = original_msg.get('Message-ID')\n"
            "    # TODO: if msg_id: reply['In-Reply-To'] = msg_id\n"
            "    # TODO: reply.set_content(reply_body)\n"
            "    # TODO: return reply\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"SAMPLE_EMAIL = {sample_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'build_reply_email' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: build_reply_email defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    original = email.message_from_string(SAMPLE_EMAIL)\n"
            "    reply = None\n"
            "\n"
            "    # Check 2: returns an EmailMessage\n"
            "    try:\n"
            "        reply = build_reply_email(\n"
            "            original,\n"
            "            'Sure, Thursday at 2pm works for me!',\n"
            "            'bob@example.com',\n"
            "        )\n"
            "        assert isinstance(reply, email.message.Message), \\\n"
            "            f'expected EmailMessage, got {type(reply)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns an EmailMessage')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: subject has Re: prefix\n"
            "    try:\n"
            "        assert reply is not None, 'reply is None (Check 2 failed)'\n"
            "        assert reply['Subject'].startswith('Re:'), \\\n"
            "            f\"Subject should start with 'Re:', got {reply['Subject']!r}\"\n"
            "        passed += 1; print(f\"\\u2705 Check 3: Subject={reply['Subject']!r}\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: From and To correct\n"
            "    try:\n"
            "        assert reply is not None, 'reply is None'\n"
            "        assert reply['From'] == 'bob@example.com', \\\n"
            "            f\"From wrong: {reply['From']!r}\"\n"
            "        assert reply['To'] == 'alice@example.com', \\\n"
            "            f\"To should be original From 'alice@example.com', got {reply['To']!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: From and To headers correct')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: In-Reply-To set to original Message-ID\n"
            "    try:\n"
            "        assert reply is not None, 'reply is None'\n"
            "        in_reply_to = reply.get('In-Reply-To')\n"
            "        original_id = original.get('Message-ID')\n"
            "        assert in_reply_to == original_id, \\\n"
            "            f\"In-Reply-To {in_reply_to!r} != Message-ID {original_id!r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 5: In-Reply-To set to original Message-ID')\n"
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
            + BUILD_REPLY_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template — NOT executed by gate)
# ---------------------------------------------------------------------------

def project_nb():
    global _cid; _cid = 500
    sample_repr = repr(SAMPLE_EMAIL)
    return [
        md(
            "# Day 025 Project: AI Email-Responder Drafter\n\n"
            "## What You're Building\n\n"
            "An `EmailDrafter` class that takes an incoming email (raw RFC 2822 string), "
            "parses it, uses the LLM to draft a reply, and returns a fully formed "
            "`EmailMessage` ready to send via SMTP.\n\n"
            "This is the pipeline: `parse → draft → build_reply → (optionally) send`.\n\n"
            "## Project Requirements\n\n"
            "1. Implement `EmailDrafter` with methods:\n"
            "   - `parse(raw_email)` → `email.message.Message`\n"
            "   - `draft(msg, context, model)` → `str` (reply body)\n"
            "   - `build_reply(original_msg, reply_body, from_addr)` → `EmailMessage`\n"
            "   - `run_pipeline(raw_email, context, from_addr, model)` → `dict`\n"
            "2. Run the pipeline on SAMPLE_EMAIL with a context hint\n"
            "3. Print the reply email headers and body\n\n"
            "**Deliverable:** A complete reply email string — ready to paste into SMTP."
        ),
        code(
            "import email\n"
            "import email.message\n"
            "import ollama"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "Implement `EmailDrafter` by wiring together the helper functions."
        ),
        code(
            "class EmailDrafter:\n"
            "    def parse(self, raw_email: str) -> email.message.Message:\n"
            "        # TODO: return parse_email_string(raw_email)\n"
            "        pass\n"
            "\n"
            "    def draft(\n"
            "        self, msg: email.message.Message, context: str, model: str = 'llama3.2'\n"
            "    ) -> str:\n"
            "        # TODO: body = get_email_body(msg)\n"
            "        # TODO: return draft_reply(\n"
            "        #           original_subject=msg.get('Subject', ''),\n"
            "        #           original_body=body, context=context, model=model)\n"
            "        pass\n"
            "\n"
            "    def build_reply(\n"
            "        self, original_msg: email.message.Message,\n"
            "        reply_body: str, from_addr: str\n"
            "    ) -> email.message.EmailMessage:\n"
            "        # TODO: return build_reply_email(original_msg, reply_body, from_addr=from_addr)\n"
            "        pass\n"
            "\n"
            "    def run_pipeline(\n"
            "        self, raw_email: str, context: str,\n"
            "        from_addr: str, model: str = 'llama3.2'\n"
            "    ) -> dict:\n"
            "        # TODO: parsed     = self.parse(raw_email)\n"
            "        # TODO: reply_body = self.draft(parsed, context=context, model=model)\n"
            "        # TODO: reply_msg  = self.build_reply(parsed, reply_body, from_addr=from_addr)\n"
            "        # TODO: return {'parsed': parsed, 'reply_body': reply_body, 'reply_msg': reply_msg}\n"
            "        pass"
        ),
        md("## Use Your Email Drafter"),
        code(
            f"SAMPLE_EMAIL = {sample_repr}\n"
        ),
        code(
            "# drafter = EmailDrafter()\n"
            "# result = drafter.run_pipeline(\n"
            "#     raw_email=SAMPLE_EMAIL,\n"
            "#     context='Accept the meeting, suggest Thursday at 2pm',\n"
            "#     from_addr='bob@example.com',\n"
            "# )\n"
            "# print('Original:')\n"
            "# print(f\"  From: {result['parsed']['From']}\")\n"
            "# print(f\"  Subject: {result['parsed']['Subject']}\")\n"
            "# print('\\nDrafted reply:')\n"
            "# print(result['reply_body'])\n"
            "# print('\\nReply email (ready to send):')\n"
            "# print(result['reply_msg'].as_string())\n"
        ),
        md(
            "## How to Actually Send (SMTP)\n\n"
            "Once you have a reply `EmailMessage`, sending it is three lines:\n\n"
            "```python\n"
            "import smtplib\n\n"
            "# Gmail example — needs an App Password (not your login password)\n"
            "with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:\n"
            "    server.login('you@gmail.com', 'your-app-password')\n"
            "    server.send_message(reply_msg)\n"
            "```\n\n"
            "For Outlook/Hotmail: `smtp.office365.com:587` with `SMTP` + `starttls()`.\n"
            "For local testing: use `smtplib.SMTP('localhost', 1025)` with a "
            "[mailhog](https://github.com/mailhog/MailHog) test server.\n\n"
            "**Credentials**: store in environment variables (Day 32), never hardcode."
        ),
        md(
            "## How to Read Email (IMAP)\n\n"
            "```python\n"
            "import imaplib, email\n\n"
            "with imaplib.IMAP4_SSL('imap.gmail.com') as imap:\n"
            "    imap.login('you@gmail.com', 'your-app-password')\n"
            "    imap.select('INBOX')\n"
            "    _, data = imap.search(None, 'UNSEEN')\n"
            "    for msg_id in data[0].split()[-5:]:\n"
            "        _, msg_data = imap.fetch(msg_id, '(RFC822)')\n"
            "        raw = msg_data[0][1]  # bytes\n"
            "        msg = email.message_from_bytes(raw)\n"
            "        body = get_email_body(msg)\n"
            "        reply = drafter.run_pipeline(msg.as_string(), 'Acknowledge receipt', 'me@example.com')\n"
            "```\n"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: EmailDrafter has all required methods\n"
            "    try:\n"
            "        assert 'EmailDrafter' in globals(), 'EmailDrafter not defined'\n"
            "        for m in ('parse', 'draft', 'build_reply', 'run_pipeline'):\n"
            "            assert hasattr(EmailDrafter, m), f'EmailDrafter missing: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: EmailDrafter has all required methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: drafter is an EmailDrafter\n"
            "    try:\n"
            "        assert 'drafter' in globals(), 'drafter not defined'\n"
            "        assert isinstance(drafter, EmailDrafter), \\\n"
            "            f'drafter must be EmailDrafter, got {type(drafter)}'\n"
            "        passed += 1; print('\\u2705 Check 2: drafter is an EmailDrafter')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: result is a dict with required keys\n"
            "    try:\n"
            "        assert 'result' in globals(), 'result not defined'\n"
            "        for key in ('parsed', 'reply_body', 'reply_msg'):\n"
            "            assert key in result, f\"result missing key '{key}': {list(result)}\"\n"
            "        passed += 1; print('\\u2705 Check 3: result has parsed/reply_body/reply_msg')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: reply_body is a non-empty string\n"
            "    try:\n"
            "        assert 'result' in globals(), 'result not defined'\n"
            "        rb = result.get('reply_body')\n"
            "        assert isinstance(rb, str) and len(rb) > 10, \\\n"
            "            f'reply_body should be non-empty str, got {rb!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: reply_body is {len(rb)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: reply_msg has Re: subject and correct From\n"
            "    try:\n"
            "        assert 'result' in globals(), 'result not defined'\n"
            "        rm = result.get('reply_msg')\n"
            "        assert rm is not None, 'reply_msg is None'\n"
            "        assert rm['Subject'].startswith('Re:'), \\\n"
            "            f\"reply Subject should start with 'Re:', got {rm['Subject']!r}\"\n"
            "        assert rm['From'] == 'bob@example.com', \\\n"
            "            f\"reply From should be 'bob@example.com', got {rm['From']!r}\"\n"
            "        passed += 1; print(f'\\u2705 Check 5: reply subject and From correct')\n"
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
            "- Add a `classify_urgency(msg, model) -> str` method that uses the LLM to "
            "classify the email as 'urgent', 'normal', or 'low-priority' before drafting\n"
            "- Add a `summarize(msg, model) -> str` method that summarises the email in "
            "one sentence (useful when the body is long)\n"
            "- Extend the pipeline to handle a list of raw emails: process each one, "
            "skipping emails where `get_email_body` returns an empty string\n"
            "- Test with a real IMAP connection to your Gmail or Outlook (needs app password)\n"
            "- Add `References` header alongside `In-Reply-To` for proper thread linking"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate — must run clean)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600
    sample_repr = repr(SAMPLE_EMAIL)

    solution_all = (
        "import email\n"
        "import email.message\n"
        "import ollama\n"
        "\n"
        "\n"
        + ALL_IMPLS
        + "\n"
        "\n"
        "\n"
        + EMAIL_DRAFTER_IMPL
    )

    return [
        md(
            "# Day 025 Project Solution — AI Email-Responder Drafter\n\n"
            "An `EmailDrafter` that parses incoming email, drafts a reply with the LLM, "
            "and returns a properly threaded `EmailMessage` ready for SMTP delivery."
        ),
        code(solution_all),
        code(f"SAMPLE_EMAIL = {sample_repr}"),
        md("## Action 1 — Parse the Incoming Email"),
        code(
            "drafter = EmailDrafter()\n"
            "parsed = drafter.parse(SAMPLE_EMAIL)\n"
            "print('Parsed email:')\n"
            "print(f\"  From:    {parsed['From']}\")\n"
            "print(f\"  To:      {parsed['To']}\")\n"
            "print(f\"  Subject: {parsed['Subject']}\")\n"
            "body = get_email_body(parsed)\n"
            "print(f\"  Body ({len(body)} chars): {body[:80].strip()!r}\")"
        ),
        md("## Action 2 — Draft an AI Reply"),
        code(
            "reply_body = drafter.draft(\n"
            "    parsed,\n"
            "    context='Accept the meeting, propose Thursday at 2pm.',\n"
            ")\n"
            "print('\\nDrafted reply:')\n"
            "print(reply_body)"
        ),
        md("## Action 3 — Build and Inspect the Reply Email"),
        code(
            "reply_msg = drafter.build_reply(parsed, reply_body, from_addr='bob@example.com')\n"
            "print('\\nReply email headers:')\n"
            "print(f\"  From:         {reply_msg['From']}\")\n"
            "print(f\"  To:           {reply_msg['To']}\")\n"
            "print(f\"  Subject:      {reply_msg['Subject']}\")\n"
            "print(f\"  In-Reply-To:  {reply_msg.get('In-Reply-To')}\")\n"
            "print('\\nDrafting complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 025 notebooks...")
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
