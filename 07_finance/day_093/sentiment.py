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
