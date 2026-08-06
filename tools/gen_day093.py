#!/usr/bin/env python3
"""Day 093 generator — AI-Driven Signals (news sentiment)."""
import json, pathlib

ROOT  = pathlib.Path(__file__).parent.parent
DAY   = "093"
SLUG  = "sentiment"
TITLE = "AI-Driven Signals"
DIR   = ROOT / "07_finance" / f"day_{DAY}"

# ══════════════════════════════════════════════════════════════════════════════
# Deliverable
# ══════════════════════════════════════════════════════════════════════════════

DELIVERABLE = '''\
"""
Day 093 — AI-Driven Signals
==============================
News-sentiment signal using an LLM as the scoring engine.

Inject llm_fn(messages: list[dict]) -> str to replace the live Ollama call.
Gate always injects a keyword-based mock; production uses llama3.2 via Ollama.

Public API
----------
    parse_score(text)                           -> float in [-1.0, 1.0]
    build_sentiment_prompt(headline)            -> list[dict]
    score_headline(headline, llm_fn=None)       -> float in [-1.0, 1.0]
    score_headlines(headlines, llm_fn=None)     -> list[float]
    aggregate_sentiment(scores)                 -> float in [-1.0, 1.0]
    sentiment_to_signal(sentiment, threshold=0.1) -> int {0, 1}

    SentimentSignal(llm_fn=None, threshold=0.1)
        .score(headline)          -> float
        .score_many(headlines)    -> list[float]
        .signal_from(headlines)   -> int {0, 1}
        .history()                -> list[dict]
        .clear_history()          -> None
"""
import re


# ── primitive helpers ─────────────────────────────────────────────────────────

def parse_score(text):
    """Extract a sentiment float from raw LLM output.

    Finds the first number (integer or decimal, optionally negative) in `text`.
    Clamps the result to [-1.0, 1.0].
    Returns 0.0 (neutral) if no number is found.

    Examples:
        parse_score("0.8")             -> 0.8
        parse_score(" -0.5 ")          -> -0.5
        parse_score("Score: 0.75")     -> 0.75
        parse_score("-1.9")            -> -1.0  (clamped)
        parse_score("no numbers here") -> 0.0
    """
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not matches:
        return 0.0
    return max(-1.0, min(1.0, float(matches[0])))


def build_sentiment_prompt(headline):
    """Build the messages list for LLM sentiment scoring.

    Returns a two-message list (system + user) ready for any OpenAI-compatible
    chat API or Ollama.  The system message instructs the model to reply with
    a single number so parse_score can extract it reliably.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a financial news sentiment analyzer. "
                "Score the sentiment of the given headline from -1.0 (very bearish) "
                "to 1.0 (very bullish). "
                "Reply with ONLY a single decimal number between -1.0 and 1.0. "
                "No explanation, no additional text — just the number."
            ),
        },
        {
            "role": "user",
            "content": f"Headline: {headline}",
        },
    ]


# ── scoring functions ─────────────────────────────────────────────────────────

def score_headline(headline, llm_fn=None):
    """Score one headline for financial sentiment.

    Args:
        headline : str — a news headline
        llm_fn   : callable(messages) -> str  (injection for testing)
                   If None, uses Ollama (llama3.2).

    Returns:
        float in [-1.0, 1.0]; 0.0 if the LLM returns unparseable output.
    """
    messages = build_sentiment_prompt(headline)
    if llm_fn is not None:
        response = llm_fn(messages)
    else:
        import ollama
        response = ollama.chat(
            model="llama3.2",
            messages=messages,
        )["message"]["content"]
    return parse_score(response)


def score_headlines(headlines, llm_fn=None):
    """Score a list of headlines.

    Args:
        headlines : list[str]
        llm_fn    : optional injection (same as score_headline)

    Returns:
        list[float] — same length as headlines; each value in [-1.0, 1.0].
    """
    return [score_headline(h, llm_fn) for h in headlines]


# ── aggregation ───────────────────────────────────────────────────────────────

def aggregate_sentiment(scores):
    """Aggregate a list of sentiment scores by taking the mean.

    Returns 0.0 for an empty list (neutral default).
    The result is clamped to [-1.0, 1.0] to handle floating-point edge cases.
    """
    if not scores:
        return 0.0
    return max(-1.0, min(1.0, sum(scores) / len(scores)))


def sentiment_to_signal(sentiment, threshold=0.1):
    """Convert an aggregate sentiment score to a binary trading signal.

    Args:
        sentiment : float — aggregate score in [-1.0, 1.0]
        threshold : float — minimum positive score to go long (default 0.1)

    Returns:
        1 if sentiment > threshold (go long), 0 otherwise (stay flat).
    """
    return 1 if sentiment > threshold else 0


# ── stateful class ────────────────────────────────────────────────────────────

class SentimentSignal:
    """Stateful sentiment scorer with history.

    Follows the four-method pattern from Section 6 agents:
        score / score_many / signal_from / history / clear_history
    """

    def __init__(self, llm_fn=None, threshold=0.1):
        self._llm_fn    = llm_fn
        self._threshold = threshold
        self._history   = []

    def score(self, headline):
        """Score one headline and append to history. Returns float."""
        s = score_headline(headline, self._llm_fn)
        self._history.append({"headline": headline, "score": s})
        return s

    def score_many(self, headlines):
        """Score a list of headlines, recording each in history.

        Returns list[float] — same length as headlines.
        """
        return [self.score(h) for h in headlines]

    def signal_from(self, headlines):
        """Aggregate sentiment from a list of headlines into a binary signal.

        Calls score_many (records history), aggregates, then applies threshold.
        Returns int {0, 1}.
        """
        scores = self.score_many(headlines)
        return sentiment_to_signal(aggregate_sentiment(scores), self._threshold)

    def history(self):
        """Return a copy of the scoring history."""
        return list(self._history)

    def clear_history(self):
        """Clear scoring history in-place."""
        self._history.clear()
'''

# ══════════════════════════════════════════════════════════════════════════════
# Notebook helpers
# ══════════════════════════════════════════════════════════════════════════════

def _nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (ipykernel)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }

def _code(src, outputs=None):
    return {
        "cell_type": "code", "execution_count": None, "metadata": {},
        "outputs": outputs or [],
        "source": src.splitlines(keepends=True),
    }

def _md(src):
    return {"cell_type": "markdown", "metadata": {},
            "source": src.splitlines(keepends=True)}

# ── preludes ──────────────────────────────────────────────────────────────────

_P_BASE = """\
import re

# Gate-safe mock LLM — keyword-based, deterministic, no Ollama required
# Checks only the user message to avoid matching keywords in the system prompt.
def _mock_llm(messages):
    user_text = next(
        (m.get("content", "") for m in messages if m.get("role") == "user"), ""
    ).lower()
    if any(w in user_text for w in ["surge", "rally", "rise", "gain", "bull", "strong"]):
        return "0.75"
    if any(w in user_text for w in ["crash", "fall", "decline", "bear", "weak", "loss"]):
        return "-0.60"
    return "0.10"

BULLISH_HEADLINES = [
    "Tech stocks rally on strong earnings",
    "Markets surge as Fed signals rate pause",
    "S&P 500 gains 2% on positive jobs data",
    "Bull market continues with broad gains",
]
BEARISH_HEADLINES = [
    "Markets crash amid recession fears",
    "Stocks fall sharply on weak economic data",
    "S&P 500 declines on hawkish Fed remarks",
    "Bear market deepens as losses mount",
]
NEUTRAL_HEADLINES = [
    "Markets trade sideways in quiet session",
    "Mixed signals leave investors cautious",
    "Stocks finish flat as investors await data",
]
"""

_P_PARSE = """\
def parse_score(text):
    \"\"\"Extract and clamp a float from LLM output. Returns 0.0 if not found.\"\"\"
    matches = re.findall(r"-?\\d+(?:\\.\\d+)?", text)
    if not matches:
        return 0.0
    return max(-1.0, min(1.0, float(matches[0])))

def build_sentiment_prompt(headline):
    return [
        {
            "role": "system",
            "content": (
                "You are a financial news sentiment analyzer. "
                "Score the sentiment from -1.0 (very bearish) to 1.0 (very bullish). "
                "Reply with ONLY a single decimal number. No explanation."
            ),
        },
        {"role": "user", "content": f"Headline: {headline}"},
    ]
"""

_P_SCORE_ONE = """\
def score_headline(headline, llm_fn=None):
    messages = build_sentiment_prompt(headline)
    if llm_fn is not None:
        response = llm_fn(messages)
    else:
        import ollama
        response = ollama.chat(model="llama3.2", messages=messages)["message"]["content"]
    return parse_score(response)
"""

_P_SCORE_MANY = """\
def score_headlines(headlines, llm_fn=None):
    return [score_headline(h, llm_fn) for h in headlines]
"""

_P_AGG = """\
def aggregate_sentiment(scores):
    if not scores:
        return 0.0
    return max(-1.0, min(1.0, sum(scores) / len(scores)))

def sentiment_to_signal(sentiment, threshold=0.1):
    return 1 if sentiment > threshold else 0
"""

_P_CLASS = """\
class SentimentSignal:
    def __init__(self, llm_fn=None, threshold=0.1):
        self._llm_fn = llm_fn; self._threshold = threshold; self._history = []
    def score(self, headline):
        s = score_headline(headline, self._llm_fn)
        self._history.append({"headline": headline, "score": s})
        return s
    def score_many(self, headlines):
        return [self.score(h) for h in headlines]
    def signal_from(self, headlines):
        return sentiment_to_signal(aggregate_sentiment(self.score_many(headlines)), self._threshold)
    def history(self):
        return list(self._history)
    def clear_history(self):
        self._history.clear()
"""

# ══════════════════════════════════════════════════════════════════════════════
# Exercises
# ══════════════════════════════════════════════════════════════════════════════

_EX1 = _nb([
    _md("# Exercise 1 — parse_score and build_sentiment_prompt\n\n"
        "These two functions are the foundation of the sentiment pipeline. "
        "`build_sentiment_prompt` wraps a headline in the message format the LLM "
        "expects. `parse_score` extracts a float from whatever the LLM returns — "
        "because LLMs don't always follow instructions perfectly."),
    _code(_P_BASE + """\

def parse_score(text):
    \"\"\"Extract the first number from LLM output and clamp to [-1.0, 1.0].

    Steps:
      1. matches = re.findall(r\"-?\\\\d+(?:\\\\.\\\\d+)?\", text)
      2. if not matches: return 0.0
      3. return max(-1.0, min(1.0, float(matches[0])))

    Handles: "0.8", " -0.5 ", "Score: 0.75", "1.9" (clamped → 1.0), "no num" → 0.0
    \"\"\"
    # TODO: implement the 3 steps
    return 0.0


def build_sentiment_prompt(headline):
    \"\"\"Build the two-message list for LLM sentiment scoring.

    Returns:
        [
            {"role": "system", "content": <instruction to score from -1.0 to 1.0>},
            {"role": "user",   "content": f"Headline: {headline}"},
        ]
    \"\"\"
    # TODO: return the two-message list
    return [{"role": "user", "content": headline}]
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — parse_score: extracts a plain float
try:
    assert abs(parse_score("0.8")  - 0.8)  < 1e-9
    assert abs(parse_score("-0.5") - (-0.5)) < 1e-9
    assert abs(parse_score("0")    - 0.0)  < 1e-9
    checks += 1; print("✅ 1 parse_score extracts plain floats correctly")
except Exception as e:
    print("❌ 1:", e)

# 2 — parse_score: works with surrounding text
try:
    assert abs(parse_score("Score: 0.75")      - 0.75) < 1e-9
    assert abs(parse_score("The score is -0.3") - (-0.3)) < 1e-9
    checks += 1; print("✅ 2 parse_score works with surrounding text")
except Exception as e:
    print("❌ 2:", e)

# 3 — parse_score: clamps out-of-range values
try:
    assert abs(parse_score("-1.9") - (-1.0)) < 1e-9, f"expected -1.0, got {parse_score('-1.9')}"
    assert abs(parse_score("1.5")  -   1.0)  < 1e-9, f"expected  1.0, got {parse_score('1.5')}"
    checks += 1; print("✅ 3 parse_score clamps to [-1.0, 1.0]")
except Exception as e:
    print("❌ 3:", e)

# 4 — parse_score: returns 0.0 for no-number input
try:
    assert parse_score("bullish sentiment") == 0.0
    assert parse_score("") == 0.0
    checks += 1; print("✅ 4 parse_score returns 0.0 when no number found")
except Exception as e:
    print("❌ 4:", e)

# 5 — build_sentiment_prompt: structure check
try:
    h = "Markets surge on strong earnings"
    p = build_sentiment_prompt(h)
    assert isinstance(p, list) and len(p) == 2, f"expected list of 2, got {type(p)}/{len(p)}"
    roles = [m["role"] for m in p]
    assert "system" in roles, "missing system message"
    assert "user"   in roles, "missing user message"
    user_msg = next(m for m in p if m["role"] == "user")
    assert h in user_msg["content"], "headline not in user message"
    checks += 1; print("✅ 5 build_sentiment_prompt: 2 messages, system+user, headline in user")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX2 = _nb([
    _md("# Exercise 2 — score_headline\n\n"
        "`score_headline` is the core LLM call: build the prompt, call the model "
        "(or the injected mock), parse the response. In production it calls Ollama; "
        "in tests it calls `_mock_llm`. This injection pattern keeps the exercises "
        "fast and deterministic — no network, no model download required."),
    _code(_P_BASE + _P_PARSE + """\

def score_headline(headline, llm_fn=None):
    \"\"\"Score one headline for financial sentiment.

    Steps:
      1. messages  = build_sentiment_prompt(headline)
      2. if llm_fn is not None:
             response = llm_fn(messages)
         else:
             import ollama
             response = ollama.chat(model="llama3.2",
                                    messages=messages)["message"]["content"]
      3. return parse_score(response)

    Args:
        headline : str — a financial news headline
        llm_fn   : callable(messages) -> str  (inject _mock_llm for testing)

    Returns:
        float in [-1.0, 1.0]
    \"\"\"
    # TODO: implement the 3 steps
    return 0.0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a float in [-1.0, 1.0]
try:
    s = score_headline("Markets rally strongly", llm_fn=_mock_llm)
    assert isinstance(s, float), f"expected float, got {type(s)}"
    assert -1.0 <= s <= 1.0,     f"out of range: {s}"
    checks += 1; print("✅ 1 score_headline returns float in [-1.0, 1.0]")
except Exception as e:
    print("❌ 1:", e)

# 2 — bullish headlines score positively with mock
try:
    s = score_headline("S&P 500 surges on strong jobs data", llm_fn=_mock_llm)
    assert s > 0, f"expected positive score for bullish headline, got {s}"
    checks += 1; print("✅ 2 bullish headline → positive score")
except Exception as e:
    print("❌ 2:", e)

# 3 — bearish headlines score negatively with mock
try:
    s = score_headline("Markets crash amid recession fears", llm_fn=_mock_llm)
    assert s < 0, f"expected negative score for bearish headline, got {s}"
    checks += 1; print("✅ 3 bearish headline → negative score")
except Exception as e:
    print("❌ 3:", e)

# 4 — llm_fn is called with a list of messages (not a plain string)
try:
    received_args = []
    def _capturing_llm(messages):
        received_args.append(messages)
        return "0.5"
    score_headline("Any headline", llm_fn=_capturing_llm)
    assert len(received_args) == 1, "llm_fn should be called exactly once"
    assert isinstance(received_args[0], list), f"expected list of messages, got {type(received_args[0])}"
    checks += 1; print("✅ 4 llm_fn called with messages list")
except Exception as e:
    print("❌ 4:", e)

# 5 — returns 0.0 when llm returns non-number
try:
    def _bad_llm(messages): return "no numbers here at all"
    s = score_headline("Some headline", llm_fn=_bad_llm)
    assert s == 0.0, f"expected 0.0 for non-number response, got {s}"
    checks += 1; print("✅ 5 returns 0.0 when LLM returns unparseable output")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX3 = _nb([
    _md("# Exercise 3 — score_headlines\n\n"
        "`score_headlines` is the batch version: map `score_headline` over a "
        "list of headlines. In practice, a trading day produces multiple news "
        "items — earnings releases, central bank statements, economic data. "
        "Scoring all of them and aggregating gives a more robust daily signal "
        "than relying on a single headline."),
    _code(_P_BASE + _P_PARSE + _P_SCORE_ONE + """\

def score_headlines(headlines, llm_fn=None):
    \"\"\"Score a list of headlines.

    Args:
        headlines : list[str]
        llm_fn    : optional injection (same signature as score_headline)

    Returns:
        list[float] — same length as headlines; each value in [-1.0, 1.0].

    Implementation:
        return [score_headline(h, llm_fn) for h in headlines]
    \"\"\"
    # TODO: one line
    return [0.0] * len(headlines)
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — returns a list of the same length as input
try:
    scores = score_headlines(BULLISH_HEADLINES, llm_fn=_mock_llm)
    assert isinstance(scores, list) and len(scores) == len(BULLISH_HEADLINES)
    checks += 1; print("✅ 1 returns list of same length as input")
except Exception as e:
    print("❌ 1:", e)

# 2 — all values are floats in [-1.0, 1.0]
try:
    scores = score_headlines(BULLISH_HEADLINES + BEARISH_HEADLINES, llm_fn=_mock_llm)
    for s in scores:
        assert isinstance(s, float) and -1.0 <= s <= 1.0, f"invalid score: {s}"
    checks += 1; print("✅ 2 all values are float in [-1.0, 1.0]")
except Exception as e:
    print("❌ 2:", e)

# 3 — bullish headlines → all positive scores with mock
try:
    scores = score_headlines(BULLISH_HEADLINES, llm_fn=_mock_llm)
    assert all(s > 0 for s in scores), f"expected all positive: {scores}"
    checks += 1; print("✅ 3 bullish headlines → all positive scores")
except Exception as e:
    print("❌ 3:", e)

# 4 — bearish headlines → all negative scores with mock
try:
    scores = score_headlines(BEARISH_HEADLINES, llm_fn=_mock_llm)
    assert all(s < 0 for s in scores), f"expected all negative: {scores}"
    checks += 1; print("✅ 4 bearish headlines → all negative scores")
except Exception as e:
    print("❌ 4:", e)

# 5 — empty list returns empty list
try:
    scores = score_headlines([], llm_fn=_mock_llm)
    assert scores == [], f"expected [], got {scores}"
    checks += 1; print("✅ 5 empty headlines list → empty scores list")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX4 = _nb([
    _md("# Exercise 4 — aggregate_sentiment and sentiment_to_signal\n\n"
        "`aggregate_sentiment` reduces a list of headline scores to a single "
        "daily sentiment number by taking the mean. `sentiment_to_signal` applies "
        "a threshold: positive enough sentiment → long (1), otherwise flat (0). "
        "The threshold default of 0.1 means the model needs to see a mild net "
        "positive signal to go long — not just any non-zero score."),
    _code(_P_BASE + _P_PARSE + _P_SCORE_ONE + _P_SCORE_MANY + """\

def aggregate_sentiment(scores):
    \"\"\"Mean of a list of sentiment scores, clamped to [-1.0, 1.0].

    Returns 0.0 for an empty list (neutral default).

    Implementation:
        if not scores: return 0.0
        return max(-1.0, min(1.0, sum(scores) / len(scores)))
    \"\"\"
    # TODO: implement
    return 0.0


def sentiment_to_signal(sentiment, threshold=0.1):
    \"\"\"Convert aggregate sentiment to a binary trading signal.

    Returns 1 (long) if sentiment > threshold, else 0 (flat).

    Implementation:
        return 1 if sentiment > threshold else 0
    \"\"\"
    # TODO: one line
    return 0
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — aggregate_sentiment returns the mean of the scores
try:
    scores = [0.4, 0.6, 0.2]
    agg = aggregate_sentiment(scores)
    assert abs(agg - (0.4+0.6+0.2)/3) < 1e-9, f"expected {(0.4+0.6+0.2)/3:.4f}, got {agg}"
    checks += 1; print("✅ 1 aggregate_sentiment returns correct mean")
except Exception as e:
    print("❌ 1:", e)

# 2 — aggregate_sentiment: empty list → 0.0
try:
    assert aggregate_sentiment([]) == 0.0, f"expected 0.0 for empty, got {aggregate_sentiment([])}"
    checks += 1; print("✅ 2 aggregate_sentiment returns 0.0 for empty list")
except Exception as e:
    print("❌ 2:", e)

# 3 — aggregate_sentiment: clamps the mean to [-1.0, 1.0]
try:
    # This shouldn't happen with valid scores, but handle edge cases
    agg = aggregate_sentiment([0.9, 0.9, 0.9])
    assert -1.0 <= agg <= 1.0, f"out of range: {agg}"
    checks += 1; print("✅ 3 aggregate_sentiment result is within [-1.0, 1.0]")
except Exception as e:
    print("❌ 3:", e)

# 4 — sentiment_to_signal: positive above threshold → 1
try:
    assert sentiment_to_signal(0.5)  == 1, "0.5 > 0.1 → should be 1"
    assert sentiment_to_signal(0.1)  == 0, "0.1 is NOT > 0.1 → should be 0"
    assert sentiment_to_signal(0.11) == 1, "0.11 > 0.1 → should be 1"
    checks += 1; print("✅ 4 sentiment_to_signal: >threshold → 1; ≤threshold → 0")
except Exception as e:
    print("❌ 4:", e)

# 5 — full pipeline: bullish headlines → signal = 1
try:
    scores = score_headlines(BULLISH_HEADLINES, llm_fn=_mock_llm)
    agg    = aggregate_sentiment(scores)
    sig    = sentiment_to_signal(agg)
    assert sig == 1, f"bullish headlines should give signal=1, got sig={sig} (agg={agg:.3f})"
    print(f"  Bullish: mean score={agg:.3f} → signal={sig}")

    scores = score_headlines(BEARISH_HEADLINES, llm_fn=_mock_llm)
    agg    = aggregate_sentiment(scores)
    sig    = sentiment_to_signal(agg)
    assert sig == 0, f"bearish headlines should give signal=0, got sig={sig} (agg={agg:.3f})"
    print(f"  Bearish: mean score={agg:.3f} → signal={sig}")
    checks += 1; print("✅ 5 full pipeline: bullish→1, bearish→0")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

_EX5 = _nb([
    _md("# Exercise 5 — SentimentSignal Class\n\n"
        "`SentimentSignal` is the stateful wrapper that ties all the pieces "
        "together. It follows the same four-method pattern used throughout "
        "Section 6 agents: `score` / `score_many` / `signal_from` / `history`. "
        "History records every headline and its score — important for auditing "
        "an AI-driven trading signal."),
    _code(_P_BASE + _P_PARSE + _P_SCORE_ONE + _P_SCORE_MANY + _P_AGG + """\

class SentimentSignal:
    \"\"\"Stateful news-sentiment signal generator.

    Constructor args:
        llm_fn    : optional injection callable(messages) -> str
        threshold : minimum positive score to go long (default 0.1)

    Methods:
        score(headline)       -> float     — score one headline, record in history
        score_many(headlines) -> list[float] — score list, record each in history
        signal_from(headlines)-> int {0,1} — aggregate+threshold → signal
        history()             -> list[dict] — copy of {headline, score} records
        clear_history()       -> None      — clear history in-place
    \"\"\"

    def __init__(self, llm_fn=None, threshold=0.1):
        # TODO: store llm_fn, threshold, and initialise _history to empty list
        self._llm_fn = llm_fn
        self._threshold = threshold
        self._history = []

    def score(self, headline):
        # TODO: call score_headline, append {"headline": headline, "score": s}, return s
        return 0.0

    def score_many(self, headlines):
        # TODO: return [self.score(h) for h in headlines]
        return [0.0] * len(headlines)

    def signal_from(self, headlines):
        # TODO: scores = self.score_many(headlines)
        #        return sentiment_to_signal(aggregate_sentiment(scores), self._threshold)
        return 0

    def history(self):
        # TODO: return list(self._history)
        return []

    def clear_history(self):
        # TODO: self._history.clear()
        pass
"""),
    _md("### Checks"),
    _code("""\
checks = 0

# 1 — score returns a float and records history
try:
    ss = SentimentSignal(llm_fn=_mock_llm)
    s  = ss.score("Markets rally on earnings")
    assert isinstance(s, float) and -1.0 <= s <= 1.0
    assert len(ss.history()) == 1, f"expected 1 history entry, got {len(ss.history())}"
    assert "headline" in ss.history()[0] and "score" in ss.history()[0]
    checks += 1; print("✅ 1 score returns float and records history entry")
except Exception as e:
    print("❌ 1:", e)

# 2 — score_many records all headlines in history
try:
    ss = SentimentSignal(llm_fn=_mock_llm)
    scores = ss.score_many(BULLISH_HEADLINES)
    assert len(scores) == len(BULLISH_HEADLINES)
    assert len(ss.history()) == len(BULLISH_HEADLINES)
    checks += 1; print("✅ 2 score_many records all headlines in history")
except Exception as e:
    print("❌ 2:", e)

# 3 — signal_from: bullish headlines → 1, bearish → 0
try:
    ss_bull = SentimentSignal(llm_fn=_mock_llm)
    ss_bear = SentimentSignal(llm_fn=_mock_llm)
    bull_sig = ss_bull.signal_from(BULLISH_HEADLINES)
    bear_sig = ss_bear.signal_from(BEARISH_HEADLINES)
    assert bull_sig == 1, f"bullish → expected 1, got {bull_sig}"
    assert bear_sig == 0, f"bearish → expected 0, got {bear_sig}"
    checks += 1; print("✅ 3 signal_from: bullish→1, bearish→0")
except Exception as e:
    print("❌ 3:", e)

# 4 — history returns a copy (not a reference)
try:
    ss = SentimentSignal(llm_fn=_mock_llm)
    ss.score("Test headline")
    h1 = ss.history()
    h1.append({"headline": "injected", "score": 99.0})  # mutate the copy
    h2 = ss.history()
    assert len(h2) == 1, "history() should return a copy, not a reference"
    checks += 1; print("✅ 4 history() returns a copy — internal state protected")
except Exception as e:
    print("❌ 4:", e)

# 5 — clear_history empties history
try:
    ss = SentimentSignal(llm_fn=_mock_llm)
    ss.score_many(BULLISH_HEADLINES)
    assert len(ss.history()) > 0
    ss.clear_history()
    assert len(ss.history()) == 0, "history should be empty after clear_history()"
    checks += 1; print("✅ 5 clear_history empties history")
except Exception as e:
    print("❌ 5:", e)

print(f"\\n{checks}/5 checks passed!")
"""),
])

EXERCISES = [_EX1, _EX2, _EX3, _EX4, _EX5]

# ══════════════════════════════════════════════════════════════════════════════
# YAML lessons
# ══════════════════════════════════════════════════════════════════════════════

LESSONS = [
    """\
day: "093"
lesson: 1
title: "AI-Driven Signals: Why News Moves Markets"
slides:
  - type: title
    heading: "AI-Driven Signals"
    subheading: "Turn news headlines into trading signals with an LLM"
    narration: >
      Day 93. Today you add a fifth signal type to the strategy layer: AI-driven
      news sentiment. Instead of computing signals from price data alone, you will
      call a language model to read a financial headline and score it from negative
      one (very bearish) to positive one (very bullish). That score becomes a
      trading signal. The key insight is that price movements are often preceded
      by news events — earnings surprises, central bank announcements, economic
      data releases. An AI that reads and scores those events before the market
      fully reacts has a potential information edge.

  - type: concept
    label: "News and price"
    heading: "Why News Matters for Price"
    body: >
      Markets move on information. News is the primary source of new information.
    bullets:
      - "Earnings beats: stock often rises before and after the announcement"
      - "Central bank signals: rate expectations move bonds and equities globally"
      - "Economic data: jobs numbers, inflation, GDP revisions shift entire sectors"
      - "Sentiment precedes price: pessimism builds before a sell-off"
      - "AI reads faster than humans: scoring 100 headlines takes seconds"
    narration: >
      The efficient market hypothesis says that all public information is
      instantly priced in. In practice, markets process news gradually — there is
      a 'price discovery' period after a news event during which the signal can
      still be acted on. News sentiment analysis does not try to beat the market
      in the first millisecond. It tries to identify the aggregate direction of
      information flow — is today's news predominantly positive or negative for
      this asset? — and take a position accordingly.

  - type: concept
    label: "Injection pattern"
    heading: "The llm_fn Injection Pattern"
    body: >
      Every sentiment function accepts llm_fn=None; production uses Ollama.
    bullets:
      - "llm_fn(messages: list[dict]) -> str — same shape as Ollama chat"
      - "If llm_fn is not None: call it (testing, faster)"
      - "If llm_fn is None: import ollama; call llama3.2 (production)"
      - "Gate always injects _mock_llm — keyword-based, deterministic, no network"
      - "This pattern appeared in Section 6 agents — same design, new application"
    narration: >
      The injection pattern is the same one you used throughout Section 6 for
      agent LLM calls. A function that accepts llm_fn=None can be tested
      deterministically without a running model. In production you pass nothing
      and Ollama handles the call. For the course gate, a keyword-based mock
      returns a predictable score string for any headline containing known words
      like 'surge' or 'crash'. This design separates the AI logic from the AI
      dependency — a hallmark of good AI engineering.

  - type: exercise
    heading: "Exercise 1 — parse_score and build_sentiment_prompt"
    prompt: >
      Implement parse_score(text) to extract the first float from the text
      using re.findall(r"-?\\d+(?:\\.\\d+)?", text) and clamp to [-1.0, 1.0].
      Return 0.0 if no number found. Implement build_sentiment_prompt(headline)
      to return a list with system and user messages.
    hint: >
      The regex r"-?\\d+(?:\\.\\d+)?" matches optional minus, digits, optional
      decimal point and more digits. Check 3 tests clamping: parse_score("-1.9")
      should return -1.0, not -1.9. Check 5 tests that the headline appears in
      the user message content.
    narration: >
      These two functions are the interface layer. parse_score handles the
      messiness of real LLM output: sometimes the model says 'Score: 0.8',
      sometimes just '0.8', sometimes a sentence with the number embedded.
      The regex finds it regardless of context.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "News sentiment: LLM scores headlines from -1.0 to 1.0"
      - "llm_fn injection: same pattern as Section 6 agents"
      - "parse_score: regex + clamp — robust against messy LLM output"
      - "build_sentiment_prompt: system instructs score format; user = headline"
      - "Next: the full scoring pipeline — one headline at a time"
    narration: >
      The building blocks are in place. Next lesson: score_headline, the
      function that actually calls the LLM and returns a float.
""",

    """\
day: "093"
lesson: 2
title: "Scoring a Headline"
slides:
  - type: title
    heading: "score_headline"
    subheading: "Build prompt → call LLM → parse response"
    narration: >
      score_headline is the core function: three steps in five lines. Build
      the messages, call the LLM or the injected mock, parse the response with
      parse_score. Every other function in sentiment.py is either a utility
      (parse_score, build_sentiment_prompt) or a higher-level wrapper
      (score_headlines, aggregate_sentiment). This is the one that actually
      touches the language model.

  - type: code
    label: "score_headline"
    heading: "Three Steps, Five Lines"
    body: >
      The injection branch decides production vs. test path.
    code: |
      def score_headline(headline, llm_fn=None):
          messages = build_sentiment_prompt(headline)
          if llm_fn is not None:
              response = llm_fn(messages)
          else:
              import ollama
              response = ollama.chat(
                  model="llama3.2",
                  messages=messages,
              )["message"]["content"]
          return parse_score(response)

      # Production: score_headline("Markets fall", llm_fn=None)  → Ollama
      # Testing:    score_headline("Markets fall", _mock_llm)     → mock
    narration: >
      The lazy import — import ollama inside the else branch — means the module
      loads without error even when ollama is not installed. The import only
      runs in production. In a course gate or unit test where llm_fn is always
      provided, ollama is never imported. This is the same pattern used for
      yfinance in market_data.py on Day 89.

  - type: concept
    label: "Prompt quality"
    heading: "Why 'Reply with ONLY a number' Matters"
    body: >
      LLMs are verbose by default. Constraining the format reduces parse failures.
    bullets:
      - "Without constraint: 'The sentiment of this headline is positive, I would score it 0.7'"
      - "With constraint: '0.7'"
      - "parse_score handles both — but the first form is slower and noisier"
      - "Temperature = 0 (or very low) gives more consistent number outputs"
      - "Few-shot examples in the system prompt further reduce format variance"
    narration: >
      LLMs trained for conversation tend to explain their answers. A system
      prompt that says 'reply with ONLY a single decimal number' reduces but
      does not eliminate explanatory text. The regex in parse_score finds the
      number regardless of surrounding words — a deliberate defense-in-depth.
      In production, you might add a few-shot example in the system prompt:
      'Example — Headline: Markets rally. Response: 0.7' to further anchor the
      model to the format you expect.

  - type: concept
    label: "Score interpretation"
    heading: "Reading Sentiment Scores"
    body: >
      The number range [-1.0, 1.0] maps naturally to market expectations.
    bullets:
      - "+1.0: extremely bullish — strong buy signal"
      - "+0.5 to +0.9: moderately bullish — lean long"
      - "-0.1 to +0.1: neutral — stay flat"
      - "-0.5 to -0.9: moderately bearish — avoid or short"
      - "-1.0: extremely bearish — strong exit signal"
    narration: >
      The threshold in sentiment_to_signal defaults to 0.1. This means the
      signal only goes long if the aggregate sentiment is above 0.1 — above
      the neutral zone. You can tune this threshold: a higher threshold (0.3)
      means you only trade on strong positive sentiment, fewer trades but higher
      conviction. A lower threshold (0.05) means you trade on mild positivity,
      more trades but more noise. The right threshold depends on the specific
      market and model.

  - type: exercise
    heading: "Exercise 2 — Implement score_headline"
    prompt: >
      Implement score_headline(headline, llm_fn=None) following the three steps.
      Check 4 verifies that llm_fn is called with a list of messages (not a
      plain string). Check 5 verifies that 0.0 is returned when the LLM
      response contains no parseable number.
    hint: >
      Checks 2 and 3 use _mock_llm which returns "0.75" for bullish keywords
      and "-0.60" for bearish keywords. A headline containing "surge" or "rally"
      will return a positive score; one with "crash" or "fall" returns negative.
    narration: >
      Check 4 uses a capturing lambda to verify the argument type. This tests
      that you are passing the messages list from build_sentiment_prompt, not
      just the raw headline string. The LLM API expects a structured messages
      list — passing a plain string would cause an error in production.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "score_headline: build prompt → call LLM (or mock) → parse → return float"
      - "Lazy import ollama: only imported when llm_fn is None"
      - "Prompt constraint: 'reply with ONLY a number' reduces format variance"
      - "parse_score handles messy output as a fallback"
      - "Next: batch scoring over multiple headlines"
    narration: >
      One function, three steps. Next: score_headlines maps it over a list.
      After that, aggregate_sentiment combines the list into a single score.
      Then sentiment_to_signal converts that score into the {0,1} trading signal.
""",

    """\
day: "093"
lesson: 3
title: "Batch Scoring and Parsing"
slides:
  - type: title
    heading: "Batch Scoring"
    subheading: "Score many headlines, aggregate into one daily signal"
    narration: >
      A single headline is rarely sufficient to make a trading decision. News
      flows continuously — multiple headlines per hour, per day. Scoring all
      of them and aggregating into a mean sentiment gives a more stable signal
      than any single headline. This lesson covers score_headlines for batch
      processing, aggregate_sentiment for reducing the batch to one number, and
      the robust parsing design that makes the pipeline fault-tolerant.

  - type: concept
    label: "Batch to aggregate"
    heading: "From Many Headlines to One Daily Signal"
    body: >
      Five steps from raw text to a trading position.
    bullets:
      - "Step 1: collect today's headlines (earnings, macro, company news)"
      - "Step 2: score_headlines → list of floats"
      - "Step 3: aggregate_sentiment → mean score (clamped)"
      - "Step 4: sentiment_to_signal → 0 or 1"
      - "Step 5: pass to run_backtest as the signal Series for that day"
    narration: >
      In a production system, you would run this pipeline once per day after
      market close: fetch the day's headlines from a news API, score each one,
      aggregate, apply the threshold, and store the signal. The next day, you
      execute the signal at market open. This is exactly the look-ahead prevention
      from backtester.py: you observe the news today and trade tomorrow.
      The sentiment signal, like any indicator-based signal, is subject to the
      same shift(1) rule in run_backtest.

  - type: concept
    label: "Fault tolerance"
    heading: "Robust Parsing for AI Pipelines"
    body: >
      In production, LLMs occasionally return unexpected output. Design for failure.
    bullets:
      - "parse_score returns 0.0 (neutral) if no number found — never crashes"
      - "Neutral default: missing data → hold position, not random entry"
      - "Clamping prevents out-of-range scores from breaking downstream math"
      - "Aggregate over many headlines: one bad response has little impact"
      - "Log all raw LLM responses for debugging (history() in SentimentSignal)"
    narration: >
      Fault tolerance is the difference between a research prototype and a
      production system. If one LLM call returns 'I cannot process this request'
      instead of a number, parse_score returns 0.0 and the pipeline continues.
      If you averaged ten headlines and one is 0.0 (neutral default), the impact
      on the aggregate is small. The history() method in SentimentSignal records
      every raw response for later inspection — if the model starts misbehaving,
      the history tells you which headlines triggered the problem.

  - type: code
    label: "Batch pipeline"
    heading: "Five Lines from Headlines to Signal"
    body: >
      The complete daily sentiment pipeline.
    code: |
      headlines = [
          "Tech stocks surge on AI earnings beat",
          "Fed signals rate pause — markets rally",
          "Consumer confidence rises to six-month high",
      ]

      scores = score_headlines(headlines, llm_fn=_mock_llm)
      # e.g. [0.75, 0.75, 0.10]

      agg    = aggregate_sentiment(scores)
      # e.g. 0.533

      signal = sentiment_to_signal(agg, threshold=0.1)
      # e.g. 1 (go long)
    narration: >
      This is the complete pipeline for one trading day. In practice you would
      wrap this in a function and call it once per day, storing the signal in
      a Series aligned to your OHLCV index. The series then gets passed to
      run_backtest, which applies shift(1) before computing strategy returns.
      The sentiment signal obeys the same look-ahead rules as every other
      signal: information from day t produces a position on day t+1.

  - type: exercise
    heading: "Exercises 3 and 4 — Batch Scoring + Aggregation"
    prompt: >
      Exercise 3: implement score_headlines(headlines, llm_fn=None) as a one-line
      list comprehension. Exercise 4: implement aggregate_sentiment(scores) as
      mean + clamp, returning 0.0 for empty; and sentiment_to_signal(sentiment,
      threshold=0.1) returning 1 if sentiment > threshold else 0.
    hint: >
      Exercise 4 check 5 is the full pipeline: bullish headlines → scores →
      aggregate → signal = 1. If it fails, trace through each step: print
      scores, then agg, then sig. The mock returns 0.75 for bullish keywords,
      so the mean of 4 bullish headlines should be 0.75.
    narration: >
      Both exercises are short. The value is in understanding the data flow:
      strings → LLM → float list → mean → threshold → 0 or 1. Each step
      reduces information: from many words to one number per headline, to one
      number per day, to one bit. That final bit is your trading decision.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "score_headlines: map score_headline over a list"
      - "aggregate_sentiment: mean of scores; 0.0 for empty"
      - "sentiment_to_signal: > threshold → 1; else → 0"
      - "Fault tolerance: 0.0 default when parsing fails"
      - "Next: SentimentSignal — the stateful class with history"
    narration: >
      The functional pipeline is complete. The last lesson adds the stateful
      SentimentSignal class, which wraps the pipeline and records every score
      for auditing. This is the form you would use in a real trading system —
      a class with history, not raw functions.
""",

    """\
day: "093"
lesson: 4
title: "SentimentSignal — The Stateful Class"
slides:
  - type: title
    heading: "SentimentSignal"
    subheading: "Stateful wrapper with history — the Section 6 pattern"
    narration: >
      SentimentSignal follows the same four-method design used throughout
      Section 6 for agents and tools: a constructor that stores configuration,
      a primary action method, a batch version, and a history for auditability.
      The difference from Section 6 is that the 'action' here is not an LLM
      chat — it is a structured scoring pipeline. The result is a trading signal
      rather than a text response.

  - type: concept
    label: "Class design"
    heading: "SentimentSignal: Constructor and State"
    body: >
      Two configuration parameters; one stateful list.
    bullets:
      - "__init__(llm_fn=None, threshold=0.1)"
      - "_llm_fn: the injected or None LLM callable"
      - "_threshold: minimum positive score to go long"
      - "_history: list of {headline, score} dicts — append on every score"
      - "history() returns a copy — internal state is not exposed directly"
    narration: >
      Storing the LLM function at construction time means you set it once and
      call score or score_many many times without repeating the argument. The
      threshold is similarly fixed at construction — in a live system you would
      calibrate it on historical data before deploying. The history list is an
      internal detail — callers get a copy from history() so they cannot mutate
      the internal record.

  - type: code
    label: "SentimentSignal"
    heading: "The Full Class"
    body: >
      Twelve lines; follows the Section 6 agent pattern.
    code: |
      class SentimentSignal:
          def __init__(self, llm_fn=None, threshold=0.1):
              self._llm_fn    = llm_fn
              self._threshold = threshold
              self._history   = []

          def score(self, headline):
              s = score_headline(headline, self._llm_fn)
              self._history.append({"headline": headline, "score": s})
              return s

          def score_many(self, headlines):
              return [self.score(h) for h in headlines]

          def signal_from(self, headlines):
              scores = self.score_many(headlines)
              return sentiment_to_signal(
                  aggregate_sentiment(scores), self._threshold)

          def history(self): return list(self._history)
          def clear_history(self): self._history.clear()
    narration: >
      score_many calls self.score (not the module-level score_headline directly)
      so that every call is recorded in history. signal_from calls score_many
      for the same reason — every headline in a batch is recorded. After running
      a full day of signals, history() gives you a complete audit trail: every
      headline, its score, and by extension every position the system took.
      This is essential for explaining trading decisions in a regulated context.

  - type: concept
    label: "Auditability"
    heading: "Why History Matters for AI Trading"
    body: >
      AI-driven signals must be explainable — history() provides the evidence.
    bullets:
      - "Regulators: 'Why did your system go long on March 15th?'"
      - "Answer: three bullish headlines, mean score 0.65, above threshold 0.1"
      - "history() provides the complete headline→score→decision chain"
      - "Without history: black box — unusable in regulated environments"
      - "With history: white box — every decision is reproducible and auditable"
    narration: >
      The history pattern is not just good engineering — in financial services
      it may be a regulatory requirement. MiFID II in Europe, for example,
      requires firms to document the basis for algorithmic trading decisions.
      An LLM that reads headlines and produces signals must have a log of
      which headlines were read, what scores were assigned, and what signal
      was generated. history() is the start of that log. A production system
      would also persist history to a database and include timestamps, model
      versions, and headline sources.

  - type: exercise
    heading: "Exercise 5 — Implement SentimentSignal"
    prompt: >
      Implement the five methods of SentimentSignal. The stub has the correct
      constructor — implement score (calls score_headline + appends to history),
      score_many (calls self.score), signal_from (calls score_many, aggregate,
      threshold), history (returns copy), clear_history (clears in-place).
    hint: >
      Check 4 tests that history() returns a COPY by mutating the returned list
      and checking that the internal state is unchanged. If check 4 fails, you
      returned self._history directly instead of list(self._history).
    narration: >
      The most common mistake is check 4: returning self._history instead of
      list(self._history). The copy is important — callers can iterate or
      modify the returned list without corrupting the internal record.

  - type: summary
    heading: "What You Learned"
    bullets:
      - "SentimentSignal: follows Section 6 four-method agent pattern"
      - "score() records every call in history — audit trail"
      - "score_many() calls self.score — not the module function — for recording"
      - "signal_from() integrates batch → aggregate → threshold in one call"
      - "history() returns a copy; clear_history() resets the record"
    narration: >
      SentimentSignal is complete. The next lesson puts it all together:
      how to build a daily signal Series for a full year of synthetic data
      and connect it to the backtest engine. That is the integration that
      ties Days 89 through 93 into one coherent pipeline.
""",

    """\
day: "093"
lesson: 5
title: "Connecting Sentiment to the Backtest"
slides:
  - type: title
    heading: "Sentiment → Signal → Backtest"
    subheading: "The full Section 7 stack in one pipeline"
    narration: >
      The final lesson shows how to connect the sentiment pipeline to the
      backtest engine. The bridge is simple: build a pd.Series of signals
      aligned to the OHLCV index, where each day's signal comes from that
      day's headlines. Pass the series to run_backtest. The rest is identical
      to the price-based strategies from Day 92 — the backtester does not know
      or care whether signals came from RSI or from LLM-scored headlines.

  - type: concept
    label: "Signal construction"
    heading: "Building a Sentiment Signal Series"
    body: >
      Map headlines to signals over the OHLCV date range.
    bullets:
      - "For each date in df.index: collect headlines for that date"
      - "ss.signal_from(day_headlines) → 0 or 1"
      - "pd.Series(signals_dict, index=df.index) → aligned Series"
      - "Pass to run_backtest(df, signal_series)"
      - "Shift is applied inside run_backtest — same as price-based signals"
    narration: >
      In a live system, you would fetch real headlines from a financial news API
      such as NewsAPI, Reuters, or Bloomberg. In the course exercises, you use
      the keyword-based mock that returns deterministic scores. The code structure
      is identical — swap the mock for a real API call and the pipeline produces
      live signals. This is the modular design that makes the injection pattern
      valuable: the backtest code never changes, only the LLM and the headline
      source change.

  - type: concept
    label: "Combining signals"
    heading: "Sentiment + Technical: Combined Alpha"
    body: >
      Sentiment and price-based signals are independent — combine them for higher confidence.
    bullets:
      - "Sentiment signal: news says bullish"
      - "SMA crossover: price trend says bullish"
      - "Combined: long only when BOTH agree"
      - "Same confluence pattern as Day 92's combined_signal"
      - "More filters = fewer trades = higher quality per entry"
    narration: >
      Sentiment and technical signals are generated from completely different
      data sources — news text versus price history — so they are largely
      independent. When both point in the same direction, the probability of
      a profitable trade is higher than when only one does. Day 94 will add
      risk management on top of this multi-signal foundation. By Day 95,
      you will have a paper-trading bot that combines sentiment, technical
      signals, and risk filters into an automated system.

  - type: code
    label: "Full pipeline"
    heading: "Sentiment Signal in 10 Lines"
    body: >
      Generating a daily signal Series from headlines.
    code: |
      import pandas as pd

      # Synthetic: one headline per day based on price direction
      ss  = SentimentSignal(llm_fn=_mock_llm, threshold=0.1)
      raw_signals = {}

      for i, date in enumerate(df.index):
          direction = df["Close"].iloc[i] - df["Close"].iloc[max(0, i-1)]
          if direction > 1.0:
              headlines = ["Markets rally on strong momentum"]
          elif direction < -1.0:
              headlines = ["Markets decline on selling pressure"]
          else:
              headlines = ["Markets trade mixed in quiet session"]
          raw_signals[date] = ss.signal_from(headlines)

      signal_series = pd.Series(raw_signals, index=df.index)
      result = run_backtest(df, signal_series, "Sentiment")
    narration: >
      The loop generates one headline per day based on the synthetic price
      direction — when prices rise, a bullish headline; when they fall, a
      bearish one. In production, headline_fn would fetch real news. The
      structure of the loop is identical regardless of the headline source.
      run_backtest applies shift(1) inside, so today's headline signal
      enters the portfolio tomorrow — correct causal structure.

  - type: exercise
    heading: "Project — Sentiment Pipeline Dashboard"
    prompt: >
      The project notebook walks through the complete pipeline: score batches
      of bullish, bearish, and neutral headlines with the mock LLM, build a
      signal Series over 20 days, run the backtest, and print the metrics.
      No Ollama required — the mock LLM provides deterministic, instant scores.
    hint: >
      The project uses a helper that maps headline type to signal for 20 days.
      After running, check that result["n_trades"] > 0 — if signals never
      change, there are zero trades. If all signals are 0 (flat), check that
      your aggregate_sentiment returns a value above 0.1 for bullish headlines.
    narration: >
      This is the payoff for Day 93: an LLM-based signal running through a
      proper backtest. The signal source is AI; the evaluation framework is
      the same as any price-based strategy. After today, all the signals —
      SMA, RSI, MACD, combined, sentiment — can be compared in the same table.
      Tomorrow, Day 94, you add risk management: position sizing, stop-losses,
      and drawdown limits.

  - type: summary
    heading: "Day 93 Complete"
    bullets:
      - "parse_score: regex extract + clamp — robust against LLM format variance"
      - "build_sentiment_prompt: system (score format) + user (headline)"
      - "score_headline / score_headlines: LLM call with injection pattern"
      - "aggregate_sentiment: mean + clamp; 0.0 for empty list"
      - "sentiment_to_signal: > threshold → 1; else → 0"
      - "SentimentSignal: stateful class with history for auditing"
    narration: >
      Six functions and one class. The Section 7 signal layer now has five
      generators: SMA crossover, RSI mean reversion, MACD crossover, combined
      technical, and news sentiment. Each produces a {0,1} Series that can be
      backtested with the same run_backtest call. Day 94 adds the final control
      layer: risk management — the module that keeps the strategy from blowing
      up when signals are wrong.
""",
]

# ══════════════════════════════════════════════════════════════════════════════
# Project + solution
# ══════════════════════════════════════════════════════════════════════════════

_FULL_P = _P_BASE + _P_PARSE + _P_SCORE_ONE + _P_SCORE_MANY + _P_AGG + _P_CLASS

_BACKTEST_P = """\
import math
def _synthetic(n=20):
    prices = [100.0*(1+0.3*math.sin(i*2*math.pi/20)) for i in range(n)]
    dates  = __import__("pandas").date_range("2023-01-01", periods=n, freq="B")
    close  = __import__("pandas").Series(prices, index=dates)
    return __import__("pandas").DataFrame({
        "Open": close.shift(1).fillna(close.iloc[0]),
        "High": close*1.01, "Low": close*0.99,
        "Close": close,
        "Volume": __import__("pandas").Series([1_000_000]*n, index=dates),
    })

def _compute_returns(df): return df["Close"].pct_change()
def _compute_equity(r):   return (1+r.fillna(0)).cumprod()
def _max_dd(eq):
    peak = eq.cummax(); return float(((eq-peak)/peak).min())
def _sharpe(r):
    c = r.dropna()
    if len(c)==0 or c.std()==0: return 0.0
    return float(c.mean()/c.std()*(252**0.5))
def run_backtest(df, signals, label=""):
    mr  = _compute_returns(df)
    pos = signals.shift(1).fillna(0)
    sr  = pos * mr; eq = _compute_equity(sr)
    c   = sr.dropna(); n = len(c); tr = float(eq.iloc[-1]-1.0)
    base = 1.0+tr
    ar  = float(base**(252.0/max(n,1))-1) if base>0 else -1.0
    pd = __import__("pandas")
    return {
        "label": label, "total_return": tr, "annualized_return": ar,
        "sharpe_ratio": _sharpe(sr), "max_drawdown": _max_dd(eq),
        "win_rate": float((c>0).sum()/max(n,1)),
        "n_trades": int((pos.diff().fillna(0)!=0).sum()),
        "equity": eq,
    }
"""

PROJECT_NB = _nb([
    _md(f"# Day {DAY} Project — Sentiment Pipeline Dashboard\n\n"
        "Score batches of bullish, bearish, and neutral headlines with the mock "
        "LLM, build a 20-day sentiment signal Series, run the backtest, and print "
        "the metrics. No Ollama required — all calls use `_mock_llm`."),
    _code(_FULL_P + _BACKTEST_P),
    _code("""\
import pandas as pd

# One batch of headlines per day (cycle through 3 scenarios)
SCENARIOS = [
    BULLISH_HEADLINES[:2],  # days 0,3,6,...
    NEUTRAL_HEADLINES[:2],  # days 1,4,7,...
    BEARISH_HEADLINES[:2],  # days 2,5,8,...
]

df = _synthetic(n=20)
ss = SentimentSignal(llm_fn=_mock_llm, threshold=0.1)
raw_signals = {}
for i, date in enumerate(df.index):
    raw_signals[date] = ss.signal_from(SCENARIOS[i % 3])

signal_series = pd.Series(raw_signals, index=df.index)
print("Signal counts:", signal_series.value_counts().to_dict())
print(f"Total scored:  {len(ss.history())} headlines")
"""),
    _code("""\
result = run_backtest(df, signal_series, "Sentiment")
bah    = run_backtest(df, pd.Series(1, index=df.index), "Buy-Hold")

for label, r in [("Sentiment", result), ("Buy-Hold", bah)]:
    print(f"\\n── {label} ─────────────────────")
    print(f"  Total return:    {r['total_return']:.2%}")
    print(f"  Sharpe ratio:    {r['sharpe_ratio']:.3f}")
    print(f"  Max drawdown:    {r['max_drawdown']:.2%}")
    print(f"  Trades:          {r['n_trades']}")
    print(f"  Win rate:        {r['win_rate']:.2%}")
"""),
])

SOLUTION_NB = _nb([
    _md(f"# Day {DAY} Solution — Sentiment Pipeline Dashboard"),
    _code(_FULL_P + _BACKTEST_P),
    _code("""\
import pandas as pd

SCENARIOS = [BULLISH_HEADLINES[:2], NEUTRAL_HEADLINES[:2], BEARISH_HEADLINES[:2]]
df = _synthetic(n=20)
ss = SentimentSignal(llm_fn=_mock_llm, threshold=0.1)
raw_signals = {}
for i, date in enumerate(df.index):
    raw_signals[date] = ss.signal_from(SCENARIOS[i % 3])

signal_series = pd.Series(raw_signals, index=df.index)
result = run_backtest(df, signal_series, "Sentiment")
bah    = run_backtest(df, pd.Series(1, index=df.index), "Buy-Hold")

# Assertions
assert len(ss.history()) == len(df.index) * 2, \
    f"expected {len(df.index)*2} history entries, got {len(ss.history())}"
assert set(signal_series.unique()).issubset({0, 1})
assert not signal_series.isna().any()
assert abs(result["equity"].iloc[-1] - (1 + result["total_return"])) < 1e-9
assert result["max_drawdown"] <= 1e-9
assert result["n_trades"] >= 0

# Bullish-only signals
ss2 = SentimentSignal(llm_fn=_mock_llm)
bull_sig = ss2.signal_from(BULLISH_HEADLINES)
assert bull_sig == 1, f"bullish → expected 1, got {bull_sig}"
bear_sig = ss2.signal_from(BEARISH_HEADLINES)
assert bear_sig == 0, f"bearish → expected 0, got {bear_sig}"

for label, r in [("Sentiment", result), ("Buy-Hold", bah)]:
    print(f"\\n── {label} ─────────────────────")
    print(f"  Total return:    {r['total_return']:.2%}")
    print(f"  Sharpe ratio:    {r['sharpe_ratio']:.3f}")
    print(f"  Max drawdown:    {r['max_drawdown']:.2%}")
    print(f"  Trades:          {r['n_trades']}")
print("\\nSolution smoke-test passed.")
"""),
])

# ══════════════════════════════════════════════════════════════════════════════
# Gate
# ══════════════════════════════════════════════════════════════════════════════

GATE_PY = f"""\
import importlib.util, sys, re
spec = importlib.util.spec_from_file_location(
    "{SLUG}", r"{DIR / (SLUG + '.py')}"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def _mock_llm(messages):
    user_text = next(
        (m.get("content","") for m in messages if m.get("role")=="user"), ""
    ).lower()
    if any(w in user_text for w in ["surge","rally","rise","gain","bull","strong"]): return "0.75"
    if any(w in user_text for w in ["crash","fall","decline","bear","weak","loss"]):  return "-0.60"
    return "0.10"

BULLISH = ["Markets surge on AI earnings beat",
           "S&P 500 rallies on strong jobs data"]
BEARISH = ["Stocks crash amid recession fears",
           "Markets decline on weak economic data"]

# parse_score
assert abs(mod.parse_score("0.8") - 0.8) < 1e-9
assert abs(mod.parse_score("-0.5") - (-0.5)) < 1e-9
assert abs(mod.parse_score("Score: 0.75") - 0.75) < 1e-9
assert abs(mod.parse_score("-1.9") - (-1.0)) < 1e-9
assert abs(mod.parse_score("1.9")  -   1.0)  < 1e-9
assert mod.parse_score("no numbers") == 0.0

# build_sentiment_prompt
p = mod.build_sentiment_prompt("Test headline")
assert isinstance(p, list) and len(p) == 2
roles = [m["role"] for m in p]
assert "system" in roles and "user" in roles
user_m = next(m for m in p if m["role"] == "user")
assert "Test headline" in user_m["content"]

# score_headline
s = mod.score_headline("Markets surge!", llm_fn=_mock_llm)
assert isinstance(s, float) and s > 0, f"expected positive, got {{s}}"
s = mod.score_headline("Markets crash!", llm_fn=_mock_llm)
assert isinstance(s, float) and s < 0, f"expected negative, got {{s}}"
def _bad_llm(m): return "no number"
assert mod.score_headline("anything", llm_fn=_bad_llm) == 0.0

# score_headlines
scores = mod.score_headlines(BULLISH, llm_fn=_mock_llm)
assert isinstance(scores, list) and len(scores) == len(BULLISH)
assert all(isinstance(v, float) and -1 <= v <= 1 for v in scores)
assert mod.score_headlines([], llm_fn=_mock_llm) == []

# aggregate_sentiment
assert mod.aggregate_sentiment([]) == 0.0
assert abs(mod.aggregate_sentiment([0.4, 0.6]) - 0.5) < 1e-9

# sentiment_to_signal
assert mod.sentiment_to_signal(0.5)  == 1
assert mod.sentiment_to_signal(0.1)  == 0   # not strictly greater than threshold
assert mod.sentiment_to_signal(0.11) == 1
assert mod.sentiment_to_signal(-0.5) == 0

# SentimentSignal
ss = mod.SentimentSignal(llm_fn=_mock_llm)
s  = ss.score("Markets surge today")
assert isinstance(s, float) and s > 0
assert len(ss.history()) == 1
h = ss.history()[0]
assert "headline" in h and "score" in h

scores = ss.score_many(BULLISH)
assert len(scores) == len(BULLISH)
assert len(ss.history()) == 1 + len(BULLISH)

hist_copy = ss.history(); hist_copy.append({{"headline":"x","score":99}})
assert len(ss.history()) == 1 + len(BULLISH), "history() must return a copy"

bull_sig = mod.SentimentSignal(llm_fn=_mock_llm).signal_from(BULLISH)
assert bull_sig == 1, f"bullish → expected 1, got {{bull_sig}}"
bear_sig = mod.SentimentSignal(llm_fn=_mock_llm).signal_from(BEARISH)
assert bear_sig == 0, f"bearish → expected 0, got {{bear_sig}}"

ss.clear_history()
assert len(ss.history()) == 0, "clear_history must empty history"

print("Gate: all inline checks passed")
"""

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import subprocess, sys, re

    (DIR / "exercises").mkdir(parents=True, exist_ok=True)
    (DIR / "lessons").mkdir(parents=True, exist_ok=True)
    (DIR / "project" / "solution").mkdir(parents=True, exist_ok=True)

    (DIR / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")
    (DIR / "project" / "solution" / f"{SLUG}.py").write_text(DELIVERABLE, encoding="utf-8")

    for i, nb in enumerate(EXERCISES, 1):
        (DIR / "exercises" / f"exercise_{i:02d}.ipynb").write_text(
            json.dumps(nb, indent=1), encoding="utf-8")

    for i, yaml_text in enumerate(LESSONS, 1):
        (DIR / "lessons" / f"day_{DAY}_lesson_{i:02d}.yaml").write_text(
            yaml_text, encoding="utf-8")

    (DIR / "project" / "project.ipynb").write_text(
        json.dumps(PROJECT_NB, indent=1), encoding="utf-8")
    (DIR / "project" / "solution" / "solution.ipynb").write_text(
        json.dumps(SOLUTION_NB, indent=1), encoding="utf-8")

    print(f"[gen_day{DAY}] files written — running gate …")

    result = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", GATE_PY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("GATE FAILED (inline)\n", result.stdout, result.stderr)
        sys.exit(1)
    print(result.stdout.strip())

    nb_paths = (
        [DIR / "exercises" / f"exercise_{i:02d}.ipynb" for i in range(1, 6)]
        + [DIR / "project" / "solution" / "solution.ipynb"]
    )
    nbclient_script = "import nbformat, nbclient\n"
    for p in nb_paths:
        nbclient_script += (
            f"nb = nbformat.read(r'{p}', as_version=4)\n"
            f"nbclient.NotebookClient(nb, timeout=60, kernel_name='python3',"
            f" resources={{'metadata': {{'path': r'{p.parent}'}}}}).execute()\n"
            f"errs = [c for c in nb.cells if any(o.get('output_type')=='error'"
            f" for o in c.get('outputs',[]))]\n"
            f"assert not errs, 'Notebook {p.name} had errors'\n"
            f"print('  OK {p.name}')\n"
        )
    result2 = subprocess.run(
        ["conda", "run", "-n", "ai-course", "--no-capture-output",
         "python", "-c", nbclient_script],
        capture_output=True, text=True,
    )
    if result2.returncode != 0:
        print("GATE FAILED (nbclient)\n", result2.stdout, result2.stderr)
        sys.exit(1)
    print(result2.stdout.strip())

    src = DELIVERABLE + "\n".join(
        json.dumps(nb) for nb in EXERCISES + [PROJECT_NB, SOLUTION_NB]
    )
    for pattern in ["openai", "anthropic", r"\beval\b"]:
        if re.search(pattern, src):
            print(f"GATE FAILED: banned pattern '{pattern}' found")
            sys.exit(1)
    print("Gate: adversarial grep clean")
    print(f"\n[gen_day{DAY}] gate-green ✓")


if __name__ == "__main__":
    main()
