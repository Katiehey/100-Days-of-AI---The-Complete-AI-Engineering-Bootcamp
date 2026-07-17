#!/usr/bin/env python3
"""Generate all Day 023 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "02_automation" / "day_023"

_cid = 0
SCRAPE_URL = "https://books.toscrape.com"

# Static HTML used in exercises 1-3 (no network calls needed)
HTML_SAMPLE = (
    "<!DOCTYPE html>\n"
    "<html>\n"
    "<head><title>Book Reviews</title></head>\n"
    "<body>\n"
    "  <h1>Top Books</h1>\n"
    '  <p class="intro">Curated reading list.</p>\n'
    "  <ul>\n"
    '    <li><a href="/books/python">Learn Python</a></li>\n'
    '    <li><a href="/books/ml">Machine Learning</a></li>\n'
    '    <li><a href="/books/data">Data Science</a></li>\n'
    "    <li><a>No Link</a></li>\n"
    "  </ul>\n"
    "  <h2>Fiction</h2>\n"
    "  <h2>Non-Fiction</h2>\n"
    '  <p class="highlight">Great content here.</p>\n'
    '  <p class="highlight">More highlights.</p>\n'
    "</body>\n"
    "</html>"
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
# Solution implementations (imports are in each notebook's own imports cell)
# ---------------------------------------------------------------------------

PARSE_HTML_IMPL = """\
def parse_html(html_string: str) -> BeautifulSoup:
    return BeautifulSoup(html_string, "html.parser")"""

FIND_ALL_LINKS_IMPL = """\
def find_all_links(soup: BeautifulSoup) -> list[dict]:
    links = []
    for a in soup.find_all("a", href=True):
        links.append({"text": a.get_text(strip=True), "href": a["href"]})
    return links"""

EXTRACT_BY_SELECTOR_IMPL = """\
def extract_by_selector(soup: BeautifulSoup, css_selector: str) -> list[str]:
    return [
        el.get_text(strip=True)
        for el in soup.select(css_selector)
        if el.get_text(strip=True)
    ]"""

FETCH_AND_PARSE_IMPL = """\
def fetch_and_parse(url: str, headers: dict | None = None) -> BeautifulSoup:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")"""

AI_EXTRACT_IMPL = """\
def ai_extract_from_page(html_content: str, question: str, model: str = "llama3.2") -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\\n", strip=True)
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a web page analyst. Answer questions about the page content concisely.",
            },
            {
                "role": "user",
                "content": f"Page content:\\n{text[:3000]}\\n\\nQuestion: {question}",
            },
        ],
    )
    return response["message"]["content"]"""

ALL_IMPLS = (
    PARSE_HTML_IMPL + "\n\n\n"
    + FIND_ALL_LINKS_IMPL + "\n\n\n"
    + EXTRACT_BY_SELECTOR_IMPL + "\n\n\n"
    + FETCH_AND_PARSE_IMPL + "\n\n\n"
    + AI_EXTRACT_IMPL
)

BOOK_SCRAPER_IMPL = """\
class BookScraper:
    BASE = "https://books.toscrape.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (educational scraper)"

    def get_soup(self, url: str | None = None) -> BeautifulSoup:
        url = url or self.BASE
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")

    def extract_books(self, soup: BeautifulSoup) -> list[dict]:
        books = []
        for article in soup.select("article.product_pod"):
            title_tag = article.select_one("h3 a")
            price_tag = article.select_one("p.price_color")
            rating_tag = article.select_one("p.star-rating")
            books.append({
                "title": title_tag.get("title", "") if title_tag else "",
                "price": price_tag.get_text(strip=True) if price_tag else "",
                "rating": (rating_tag.get("class") or ["", ""])[1] if rating_tag else "",
            })
        return books

    def ai_insights(self, books: list[dict], question: str, model: str = "llama3.2") -> str:
        catalog = json.dumps(books[:10], indent=2)
        r = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a book catalog analyst. Answer questions about the catalog concisely.",
                },
                {
                    "role": "user",
                    "content": f"Books:\\n{catalog}\\n\\nQuestion: {question}",
                },
            ],
        )
        return r["message"]["content"]\
"""


# ---------------------------------------------------------------------------
# Exercise 01 — parse_html
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    html_repr = repr(HTML_SAMPLE)
    return [
        md(
            "# Day 023 — Exercise 1: parse_html\n\n"
            "**What you'll build:** `parse_html(html_string)` — takes an HTML string and "
            "returns a `BeautifulSoup` object ready to query.\n\n"
            "**Why it matters:** BeautifulSoup is the foundation of every scraper. "
            "Wrapping the constructor in a one-liner lets you mock it easily in tests "
            "and ensures you always use the same parser (`html.parser` — no lxml install needed)."
        ),
        code("from bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def parse_html(html_string: str) -> BeautifulSoup:\n"
            '    """\n'
            "    Parse an HTML string and return a BeautifulSoup object.\n\n"
            "    Args:\n"
            "        html_string: Raw HTML as a string.\n\n"
            "    Returns:\n"
            "        BeautifulSoup object using the html.parser backend.\n"
            '    """\n'
            '    # TODO: return BeautifulSoup(html_string, "html.parser")\n'
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"HTML = {html_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'parse_html' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: parse_html defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    soup = None\n"
            "\n"
            "    # Check 2: returns a BeautifulSoup\n"
            "    try:\n"
            "        soup = parse_html(HTML)\n"
            "        assert isinstance(soup, BeautifulSoup), \\\n"
            "            f'expected BeautifulSoup, got {type(soup)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a BeautifulSoup')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: can find h1\n"
            "    try:\n"
            "        assert soup is not None, 'soup is None (Check 2 failed)'\n"
            "        h1 = soup.find('h1')\n"
            "        assert h1 is not None, 'soup.find(\"h1\") returned None'\n"
            "        assert h1.get_text(strip=True) == 'Top Books', \\\n"
            "            f\"h1 text should be 'Top Books', got {h1.get_text(strip=True)!r}\"\n"
            "        passed += 1; print('\\u2705 Check 3: soup.find(\"h1\") returns Top Books')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: title element found\n"
            "    try:\n"
            "        assert soup is not None, 'soup is None'\n"
            "        title = soup.find('title')\n"
            "        assert title is not None, 'soup.find(\"title\") returned None'\n"
            "        assert title.get_text(strip=True) == 'Book Reviews', \\\n"
            "            f\"title should be 'Book Reviews', got {title.get_text(strip=True)!r}\"\n"
            "        passed += 1; print('\\u2705 Check 4: soup.find(\"title\") returns Book Reviews')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: find_all returns multiple elements\n"
            "    try:\n"
            "        assert soup is not None, 'soup is None'\n"
            "        ps = soup.find_all('p')\n"
            "        assert len(ps) >= 3, f'expected >= 3 p elements, got {len(ps)}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: find_all(\"p\") returns {len(ps)} elements')\n"
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
            + PARSE_HTML_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — find_all_links
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    html_repr = repr(HTML_SAMPLE)
    return [
        md(
            "# Day 023 — Exercise 2: find_all_links\n\n"
            "**What you'll build:** `find_all_links(soup)` — extracts every link "
            "(`<a href=...>`) from a soup object and returns a list of `{text, href}` dicts.\n\n"
            "**Why it matters:** Links are the backbone of the web and the starting point "
            "for any crawler. `find_all('a', href=True)` skips anchor-tags without `href` "
            "so you never get empty hrefs in your list."
        ),
        code("from bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def find_all_links(soup: BeautifulSoup) -> list[dict]:\n"
            '    """\n'
            "    Extract all hyperlinks from a BeautifulSoup object.\n\n"
            "    Args:\n"
            "        soup: Parsed BeautifulSoup object.\n\n"
            "    Returns:\n"
            "        List of dicts with keys 'text' and 'href' for each <a href=...> tag.\n"
            "        Anchor tags without an href attribute are skipped.\n"
            '    """\n'
            "    # TODO: links = []\n"
            "    # TODO: for a in soup.find_all('a', href=True):\n"
            "    #           links.append({'text': a.get_text(strip=True), 'href': a['href']})\n"
            "    # TODO: return links\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"HTML = {html_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'find_all_links' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: find_all_links defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    soup = BeautifulSoup(HTML, 'html.parser')\n"
            "    links = None\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        links = find_all_links(soup)\n"
            "        assert isinstance(links, list), \\\n"
            "            f'expected list, got {type(links)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: skips anchor without href (4 a tags, 3 with href)\n"
            "    try:\n"
            "        assert links is not None, 'links is None (Check 2 failed)'\n"
            "        assert len(links) == 3, \\\n"
            "            f'expected 3 links (href=True skips anchor-without-href), got {len(links)}'\n"
            "        passed += 1; print('\\u2705 Check 3: returns exactly 3 links (href=True filter)')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: each item is a dict with text and href keys\n"
            "    try:\n"
            "        assert links is not None and len(links) > 0, 'links is empty'\n"
            "        for link in links:\n"
            "            assert isinstance(link, dict), f'item not a dict: {link}'\n"
            "            assert 'text' in link, f\"missing 'text' key: {link}\"\n"
            "            assert 'href' in link, f\"missing 'href' key: {link}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: each item is a dict with 'text' and 'href'\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: specific link present\n"
            "    try:\n"
            "        assert links is not None, 'links is None'\n"
            "        hrefs = [lk['href'] for lk in links]\n"
            "        assert '/books/python' in hrefs, \\\n"
            "            f\"expected '/books/python' in hrefs, got {hrefs}\"\n"
            "        python_link = next(lk for lk in links if lk['href'] == '/books/python')\n"
            "        assert python_link['text'] == 'Learn Python', \\\n"
            "            f\"expected 'Learn Python', got {python_link['text']!r}\"\n"
            "        passed += 1; print(\"\\u2705 Check 5: /books/python link has text 'Learn Python'\")\n"
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
            + FIND_ALL_LINKS_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — extract_by_selector
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    html_repr = repr(HTML_SAMPLE)
    return [
        md(
            "# Day 023 — Exercise 3: extract_by_selector\n\n"
            "**What you'll build:** `extract_by_selector(soup, css_selector)` — returns "
            "the text content of every element matching a CSS selector.\n\n"
            "**Why it matters:** CSS selectors are the most expressive way to target "
            "elements in HTML — class, ID, tag, nesting, attributes. "
            "`soup.select('.price_color')` is far cleaner than nested `find_all` calls. "
            "This function is your universal text extractor."
        ),
        code("from bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def extract_by_selector(soup: BeautifulSoup, css_selector: str) -> list[str]:\n"
            '    """\n'
            "    Extract text content of all elements matching a CSS selector.\n\n"
            "    Args:\n"
            "        soup:         Parsed BeautifulSoup object.\n"
            "        css_selector: CSS selector string (e.g. 'h2', '.price', '#main a').\n\n"
            "    Returns:\n"
            "        List of stripped text strings. Empty strings are excluded.\n"
            '    """\n'
            "    # TODO: elements = soup.select(css_selector)\n"
            "    # TODO: return [el.get_text(strip=True) for el in elements\n"
            "    #               if el.get_text(strip=True)]\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"HTML = {html_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'extract_by_selector' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: extract_by_selector defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    soup = BeautifulSoup(HTML, 'html.parser')\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = extract_by_selector(soup, 'h2')\n"
            "        assert isinstance(result, list), \\\n"
            "            f'expected list, got {type(result)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: tag selector finds 2 h2 elements\n"
            "    try:\n"
            "        result = extract_by_selector(soup, 'h2')\n"
            "        assert len(result) == 2, \\\n"
            "            f'expected 2 h2 elements, got {len(result)}: {result}'\n"
            "        passed += 1; print('\\u2705 Check 3: \"h2\" selector returns 2 items')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: items are strings\n"
            "    try:\n"
            "        result = extract_by_selector(soup, 'h2')\n"
            "        assert all(isinstance(s, str) for s in result), \\\n"
            "            'not all items are strings'\n"
            "        assert 'Fiction' in result, \\\n"
            "            f\"expected 'Fiction' in h2 texts, got {result}\"\n"
            "        passed += 1; print(\"\\u2705 Check 4: items are strings; 'Fiction' found\")\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: class selector works\n"
            "    try:\n"
            "        highlights = extract_by_selector(soup, '.highlight')\n"
            "        assert len(highlights) == 2, \\\n"
            "            f'expected 2 .highlight elements, got {len(highlights)}: {highlights}'\n"
            "        assert 'Great content here.' in highlights, \\\n"
            "            f\"expected 'Great content here.' in highlights, got {highlights}\"\n"
            "        passed += 1; print('\\u2705 Check 5: \".highlight\" selector returns 2 items')\n"
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
            + EXTRACT_BY_SELECTOR_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — fetch_and_parse
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md(
            "# Day 023 — Exercise 4: fetch_and_parse\n\n"
            "**What you'll build:** `fetch_and_parse(url, headers)` — makes an HTTP GET "
            "request and returns the response body parsed as a BeautifulSoup.\n\n"
            "**Why it matters:** This is the glue between the network and the parser. "
            "Use `response.text` (not `response.json()`) because HTML is not JSON. "
            "This is the entry point of every real scraper."
        ),
        code("import requests\nfrom bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def fetch_and_parse(url: str, headers: dict | None = None) -> BeautifulSoup:\n"
            '    """\n'
            "    Fetch a URL and return the response parsed as BeautifulSoup.\n\n"
            "    Args:\n"
            "        url:     The URL to fetch.\n"
            "        headers: Optional request headers.\n\n"
            "    Returns:\n"
            "        BeautifulSoup of the response HTML.\n\n"
            "    Raises:\n"
            "        requests.exceptions.HTTPError on 4xx/5xx responses.\n"
            '    """\n'
            "    # TODO: response = requests.get(url, headers=headers, timeout=10)\n"
            "    # TODO: response.raise_for_status()\n"
            "    # TODO: return BeautifulSoup(response.text, 'html.parser')\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f'SCRAPE_URL = "{SCRAPE_URL}"\n'
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'fetch_and_parse' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: fetch_and_parse defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    soup = None\n"
            "\n"
            "    # Check 2: returns BeautifulSoup (1 network call)\n"
            "    try:\n"
            "        soup = fetch_and_parse(SCRAPE_URL)\n"
            "        assert isinstance(soup, BeautifulSoup), \\\n"
            "            f'expected BeautifulSoup, got {type(soup)}'\n"
            "        passed += 1; print('\\u2705 Check 2: returns a BeautifulSoup')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: page has a title\n"
            "    try:\n"
            "        assert soup is not None, 'soup is None (Check 2 failed)'\n"
            "        assert soup.title is not None, 'page has no <title> element'\n"
            "        passed += 1; print(f'\\u2705 Check 3: page title = {soup.title.get_text(strip=True)!r}')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: page has book articles\n"
            "    try:\n"
            "        assert soup is not None, 'soup is None'\n"
            "        articles = soup.select('article.product_pod')\n"
            "        assert len(articles) > 0, \\\n"
            "            'no article.product_pod elements found — is this books.toscrape.com?'\n"
            "        passed += 1; print(f'\\u2705 Check 4: found {len(articles)} book articles')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: raises on bad URL\n"
            "    raised = False\n"
            "    try:\n"
            "        fetch_and_parse('http://localhost:9999/')\n"
            "    except Exception:\n"
            "        raised = True\n"
            "    try:\n"
            "        assert raised, 'fetch_and_parse should raise on an unreachable URL'\n"
            "        passed += 1; print('\\u2705 Check 5: raises on unreachable URL')\n"
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
            + FETCH_AND_PARSE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — ai_extract_from_page
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    # Use a static HTML snippet so the check harness needs no network
    html_repr = repr(HTML_SAMPLE)
    return [
        md(
            "# Day 023 — Exercise 5: ai_extract_from_page\n\n"
            "**What you'll build:** `ai_extract_from_page(html_content, question, model)` — "
            "strips HTML tags to plain text, then asks the LLM a question about the content.\n\n"
            "**Why it matters:** Scraped HTML is messy. Instead of writing fragile CSS selectors "
            "for every page layout, you can strip tags and let the LLM extract or answer "
            "questions in plain English — adaptive to any page structure."
        ),
        code("import ollama\nfrom bs4 import BeautifulSoup"),
        md("## Your Implementation"),
        code(
            "def ai_extract_from_page(html_content: str, question: str, model: str = \"llama3.2\") -> str:\n"
            '    """\n'
            "    Strip HTML tags and ask the LLM a question about the page content.\n\n"
            "    Args:\n"
            "        html_content: Raw HTML string.\n"
            "        question:     Plain-English question about the page.\n"
            "        model:        Ollama model name.\n\n"
            "    Returns:\n"
            "        LLM answer as a string. Never raises.\n"
            '    """\n'
            "    # TODO: soup = BeautifulSoup(html_content, 'html.parser')\n"
            "    # TODO: for tag in soup(['script', 'style']): tag.decompose()\n"
            '    # TODO: text = soup.get_text(separator="\\n", strip=True)\n'
            "    # TODO: call ollama.chat with system='web page analyst' and\n"
            "    #       user content = page text capped at 3000 chars + question\n"
            "    # TODO: return response['message']['content']\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            f"HTML = {html_repr}\n"
            "\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'ai_extract_from_page' in globals()\n"
            "        passed += 1; print('\\u2705 Check 1: ai_extract_from_page defined')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "        print(f'\\nScore: {passed}/{total}')\n"
            "        return\n"
            "\n"
            "    result = None\n"
            "\n"
            "    # Check 2: returns a string (1 LLM call)\n"
            "    try:\n"
            "        result = ai_extract_from_page(HTML, 'What is the main topic of this page?')\n"
            "        assert isinstance(result, str), \\\n"
            "            f'expected str, got {type(result)}'\n"
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
            "    # Check 4: result is a meaningful response\n"
            "    try:\n"
            "        assert result is not None, 'result is None'\n"
            "        assert len(result) > 10, \\\n"
            "            f'result too short ({len(result)} chars): {result!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 4: result has {len(result)} chars')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: works on minimal HTML — no crash (1 LLM call)\n"
            "    try:\n"
            "        empty_result = ai_extract_from_page('<html><body></body></html>', 'Any content?')\n"
            "        assert isinstance(empty_result, str), \\\n"
            "            f'expected str for minimal HTML, got {type(empty_result)}'\n"
            "        passed += 1; print('\\u2705 Check 5: works on minimal HTML without crashing')\n"
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
            + AI_EXTRACT_IMPL + "\n"
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
            "# Day 023 Project: Article Scraper\n\n"
            "## What You're Building\n\n"
            "A `BookScraper` class that fetches [books.toscrape.com](https://books.toscrape.com) "
            "— a site built specifically for scraping practice — extracts structured book data "
            "using CSS selectors, and uses the LLM to provide insights about the catalog.\n\n"
            "The same class structure applies to any content site: swap the CSS selectors "
            "and you have a scraper for Hacker News, a news aggregator, or a product catalogue.\n\n"
            "## Project Requirements\n\n"
            "1. Implement `BookScraper` with a `requests.Session` and a User-Agent header\n"
            "2. `get_soup(url=None)` — fetch a page and return BeautifulSoup\n"
            "3. `extract_books(soup)` — extract `{title, price, rating}` from each article\n"
            "4. `ai_insights(books, question)` — LLM analysis of the extracted catalog\n\n"
            "**Deliverable:** Run `scraper.extract_books(soup)`, print 5 titles, and get "
            "an AI answer to a question about the catalog."
        ),
        code(
            "import requests\n"
            "import json\n"
            "import ollama\n"
            "from bs4 import BeautifulSoup"
        ),
        md("## Provided: All Helper Functions"),
        code(ALL_IMPLS),
        md(
            "## Your Implementation\n\n"
            "Implement `BookScraper` using the helper functions above and CSS selectors.\n\n"
            "**Useful selectors on books.toscrape.com:**\n"
            "- `article.product_pod` — each book card\n"
            "- `h3 a` — link with `title` attribute (full book title)\n"
            "- `p.price_color` — price text\n"
            "- `p.star-rating` — rating via `class` list (e.g. `['star-rating', 'Three']`)"
        ),
        code(
            f'SCRAPE_URL = "{SCRAPE_URL}"\n'
            "\n"
            "\n"
            "class BookScraper:\n"
            "    BASE = SCRAPE_URL\n"
            "\n"
            "    def __init__(self):\n"
            "        # TODO: self.session = requests.Session()\n"
            "        # TODO: self.session.headers['User-Agent'] = 'Mozilla/5.0 (educational scraper)'\n"
            "        pass\n"
            "\n"
            "    def get_soup(self, url: str | None = None) -> BeautifulSoup:\n"
            "        # TODO: url = url or self.BASE\n"
            "        # TODO: r = self.session.get(url, timeout=10)\n"
            "        # TODO: r.raise_for_status()\n"
            "        # TODO: return BeautifulSoup(r.text, 'html.parser')\n"
            "        pass\n"
            "\n"
            "    def extract_books(self, soup: BeautifulSoup) -> list[dict]:\n"
            "        # TODO: loop over soup.select('article.product_pod')\n"
            "        #       for each: select_one('h3 a'), select_one('p.price_color'),\n"
            "        #                 select_one('p.star-rating')\n"
            "        #       return list of {title, price, rating} dicts\n"
            "        pass\n"
            "\n"
            "    def ai_insights(self, books: list[dict], question: str,\n"
            "                    model: str = 'llama3.2') -> str:\n"
            "        # TODO: json.dumps(books[:10]) → pass to ollama.chat as context\n"
            "        # TODO: return response['message']['content']\n"
            "        pass"
        ),
        md("## Use Your Scraper"),
        code(
            "# 1. Create the scraper\n"
            "# scraper = BookScraper()\n"
            "\n"
            "# 2. Fetch the front page\n"
            "# soup = scraper.get_soup()\n"
            "\n"
            "# 3. Extract books\n"
            "# books = scraper.extract_books(soup)\n"
            "# print(f'Found {len(books)} books')\n"
            "# for b in books[:5]:\n"
            "#     print(f\"  {b['title'][:50]} | {b['price']} | {b['rating']} stars\")\n"
        ),
        code(
            "# 4. AI insights\n"
            "# answer = scraper.ai_insights(books, 'What price ranges do you see in this catalog?')\n"
            "# print('\\nAI Insights:')\n"
            "# print(answer)\n"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: BookScraper class with required methods\n"
            "    try:\n"
            "        assert 'BookScraper' in globals(), 'BookScraper not defined'\n"
            "        for m in ('get_soup', 'extract_books', 'ai_insights'):\n"
            "            assert hasattr(BookScraper, m), f'BookScraper missing method: {m}'\n"
            "        passed += 1; print('\\u2705 Check 1: BookScraper has all required methods')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 1: {e}')\n"
            "\n"
            "    # Check 2: scraper is a BookScraper instance\n"
            "    try:\n"
            "        assert 'scraper' in globals(), 'scraper not defined'\n"
            "        assert isinstance(scraper, BookScraper), \\\n"
            "            f'scraper must be BookScraper, got {type(scraper)}'\n"
            "        passed += 1; print('\\u2705 Check 2: scraper is a BookScraper')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 2: {e}')\n"
            "\n"
            "    # Check 3: soup is a BeautifulSoup\n"
            "    try:\n"
            "        assert 'soup' in globals(), 'soup not defined'\n"
            "        assert isinstance(soup, BeautifulSoup), \\\n"
            "            f'soup must be BeautifulSoup, got {type(soup)}'\n"
            "        passed += 1; print('\\u2705 Check 3: soup is a BeautifulSoup')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 3: {e}')\n"
            "\n"
            "    # Check 4: books is a non-empty list with correct keys\n"
            "    try:\n"
            "        assert 'books' in globals(), 'books not defined'\n"
            "        assert isinstance(books, list) and len(books) > 0, \\\n"
            "            f'books must be non-empty list, got {books!r}'\n"
            "        for key in ('title', 'price', 'rating'):\n"
            "            assert key in books[0], f\"books[0] missing key '{key}': {books[0]}\"\n"
            "        passed += 1; print(f'\\u2705 Check 4: books has {len(books)} items with title/price/rating')\n"
            "    except Exception as e:\n"
            "        print(f'\\u274c Check 4: {e}')\n"
            "\n"
            "    # Check 5: answer is a non-empty string\n"
            "    try:\n"
            "        assert 'answer' in globals(), 'answer not defined'\n"
            "        assert isinstance(answer, str) and len(answer) > 10, \\\n"
            "            f'answer must be non-empty string, got {answer!r}'\n"
            "        passed += 1; print(f'\\u2705 Check 5: answer is {len(answer)} chars')\n"
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
            "- Add a `scrape_all_pages(max_pages=5)` method that follows the 'next' link "
            "on each page to collect books from multiple pages\n"
            "- Add a `save_csv(books, path)` method that writes the catalog to CSV "
            "(using the csv module from Day 21)\n"
            "- Try extracting from a different books.toscrape.com category page "
            "(e.g. `/catalogue/category/books/mystery_3/index.html`)\n"
            "- Use `ai_extract_from_page` on the raw HTML to get data without CSS selectors — "
            "compare accuracy with the selector-based approach\n"
            "- Add a `robots_allowed(url)` function that checks `/robots.txt` before scraping"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook (executed by gate — must run clean)
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    solution_all = (
        "import requests\n"
        "import json\n"
        "import ollama\n"
        "from bs4 import BeautifulSoup\n"
        "\n"
        "\n"
        + ALL_IMPLS
        + "\n"
        "\n"
        "\n"
        + BOOK_SCRAPER_IMPL
    )

    return [
        md(
            "# Day 023 Project Solution — Article Scraper\n\n"
            "A `BookScraper` that fetches books.toscrape.com, extracts structured data "
            "with CSS selectors, and provides AI insights about the catalog."
        ),
        code(solution_all),
        md("## Action 1 — Fetch Front Page and Extract Books"),
        code(
            f'scraper = BookScraper()\n'
            f'soup = scraper.get_soup()\n'
            f'books = scraper.extract_books(soup)\n'
            f'print(f"Found {{len(books)}} books on the front page:")\n'
            f'for b in books[:5]:\n'
            f'    print(f"  {{b[\'title\'][:55]}} | {{b[\'price\']}} | {{b[\'rating\']}}")'
        ),
        md("## Action 2 — Extract All Links from the Page"),
        code(
            "links = find_all_links(soup)\n"
            "print(f'\\nFound {len(links)} links on the page')\n"
            "# Show a few book links\n"
            "book_links = [lk for lk in links if 'catalogue' in lk['href']][:3]\n"
            "for lk in book_links:\n"
            "    print(f\"  {lk['href'][:60]}\")"
        ),
        md("## Action 3 — AI Insights on the Catalog"),
        code(
            "answer = scraper.ai_insights(\n"
            "    books,\n"
            "    'What price ranges do you see, and which rating appears most often?',\n"
            ")\n"
            "print('\\nAI Insights:')\n"
            "print(answer)\n"
            "print('\\nScraping complete!')"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 023 notebooks...")
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
