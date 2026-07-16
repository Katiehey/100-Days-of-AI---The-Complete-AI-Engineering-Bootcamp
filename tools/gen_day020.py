#!/usr/bin/env python3
"""Generate all Day 020 notebooks: exercises 1-5, project, solution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY_DIR = ROOT / "01_text_ai" / "day_020"

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
            "kernelspec": {"display_name": "ai-course", "language": "python", "name": "ai-course"},
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


def write_nb(path: Path, cells: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb(cells), indent=1), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Shared provided-code blocks
# ---------------------------------------------------------------------------

CHUNK_TEXT_IMPL = """\
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    step = chunk_size - overlap
    if step <= 0:
        step = 1
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks\
"""

EMBED_TEXT_IMPL = """\
def embed_text(text: str, model: str = "nomic-embed-text") -> list[float]:
    return ollama.embeddings(model=model, prompt=text)["embedding"]\
"""

BUILD_INDEX_IMPL = """\
def build_index(
    docs: dict,
    collection_name: str = "second_brain",
    chunk_size: int = 300,
    overlap: int = 50,
):
    client = chromadb.Client()
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(collection_name)
    for source, text in docs.items():
        chunks = chunk_text(text, chunk_size, overlap)
        ids, embeddings, documents, metadatas = [], [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{source}__{i}")
            embeddings.append(embed_text(chunk))
            documents.append(chunk)
            metadatas.append({"source": source, "chunk_index": i})
        if ids:
            collection.add(
                ids=ids, embeddings=embeddings,
                documents=documents, metadatas=metadatas,
            )
    return collection\
"""

RETRIEVE_IMPL = """\
def retrieve(query: str, collection, n_results: int = 3) -> list[dict]:
    if collection.count() == 0:
        return []
    emb = embed_text(query)
    actual_n = min(n_results, collection.count())
    results = collection.query(query_embeddings=[emb], n_results=actual_n)
    return [
        {"text": doc, "source": meta["source"], "distance": dist}
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]\
"""

BUILD_CITED_PROMPT_IMPL = """\
def build_cited_prompt(question: str, chunks: list[dict]) -> str:
    context = "\\n\\n".join(
        f"[{i+1}] Source: {c['source']}\\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    return f"Context:\\n{context}\\n\\nQuestion: {question}"\
"""

RAG_SYSTEM_PROMPT_CONST = """\
RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions using ONLY the "
    "provided context. Cite the source numbers you used (e.g. [1], [2]). "
    "If the answer is not in the context, say 'I don't know.'"
)\
"""

RAG_ANSWER_IMPL = """\
def rag_answer(
    question: str,
    collection,
    model: str = "llama3.2",
    n_results: int = 3,
) -> dict:
    chunks = retrieve(question, collection, n_results)
    if not chunks:
        return {"answer": "I don't know.", "sources": []}
    prompt = build_cited_prompt(question, chunks)
    response = ollama.chat(model=model, messages=[
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ])
    answer  = response["message"]["content"]
    sources = list(dict.fromkeys(c["source"] for c in chunks))
    return {"answer": answer, "sources": sources}\
"""

# ---------------------------------------------------------------------------
# Exercise 01 — chunk_text
# ---------------------------------------------------------------------------

def ex01():
    global _cid; _cid = 0
    return [
        md("# Day 020 — Exercise 1: chunk_text\n\n"
           "**Goal:** Implement `chunk_text(text, chunk_size, overlap)` that splits "
           "text into overlapping word windows. `chunk_size` is words per chunk; "
           "`overlap` is words shared between adjacent chunks."),
        md("## Your Implementation"),
        code(
            "def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:\n"
            '    """\n'
            "    Split text into overlapping word windows.\n"
            "    Returns a list of non-empty strings (each chunk is space-joined words).\n"
            '    """\n'
            "    # TODO: words = text.split()\n"
            "    # TODO: step = chunk_size - overlap  (max(step, 1) for safety)\n"
            "    # TODO: loop i in range(0, len(words), step)\n"
            '    # TODO: chunk = " ".join(words[i : i + chunk_size]) — skip if empty\n'
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
            "        assert 'chunk_text' in globals()\n"
            "        passed += 1; print('✅ Check 1: chunk_text defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: returns a list\n"
            "    try:\n"
            "        result = chunk_text('hello world this is a test', chunk_size=3, overlap=1)\n"
            "        assert isinstance(result, list), f'expected list, got {type(result)}'\n"
            "        passed += 1; print('✅ Check 2: chunk_text returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: empty string returns []\n"
            "    try:\n"
            "        assert chunk_text('', chunk_size=10, overlap=2) == [], 'empty string should return []'\n"
            "        passed += 1; print('✅ Check 3: empty string returns []')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: chunk_size respected\n"
            "    try:\n"
            "        words = ' '.join([f'w{i}' for i in range(50)])\n"
            "        chunks = chunk_text(words, chunk_size=10, overlap=2)\n"
            "        assert len(chunks) > 0, 'no chunks produced'\n"
            "        for c in chunks:\n"
            "            assert len(c.split()) <= 10, f'chunk has {len(c.split())} words, expected <= 10'\n"
            "        passed += 1; print('✅ Check 4: each chunk has <= chunk_size words')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: chunk_size — {e}')\n"
            "\n"
            "    # Check 5: overlap — last N words of chunk[i] == first N words of chunk[i+1]\n"
            "    try:\n"
            "        words_list = [f'w{i}' for i in range(20)]\n"
            "        words = ' '.join(words_list)\n"
            "        chunks = chunk_text(words, chunk_size=8, overlap=3)\n"
            "        assert len(chunks) >= 2, 'need at least 2 chunks to test overlap'\n"
            "        tail = chunks[0].split()[-3:]\n"
            "        head = chunks[1].split()[:3]\n"
            "        assert tail == head, f'overlap mismatch: tail={tail}, head={head}'\n"
            "        passed += 1; print('✅ Check 5: overlap words match between adjacent chunks')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: overlap — {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + CHUNK_TEXT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 02 — build_index
# ---------------------------------------------------------------------------

def ex02():
    global _cid; _cid = 100
    return [
        md("# Day 020 — Exercise 2: build_index\n\n"
           "**Goal:** Implement `build_index(docs, collection_name, chunk_size, overlap)` "
           "that chunks each document, embeds each chunk with `nomic-embed-text`, and stores "
           "everything in a ChromaDB collection with `{source, chunk_index}` metadata. "
           "**One real Ollama embedding call per chunk** in the checks."),
        code("import ollama\nimport chromadb"),
        md("## Provided: chunk_text and embed_text"),
        code(CHUNK_TEXT_IMPL + "\n\n\n" + EMBED_TEXT_IMPL),
        md("## Your Implementation"),
        code(
            "def build_index(\n"
            "    docs: dict,\n"
            "    collection_name: str = 'second_brain',\n"
            "    chunk_size: int = 300,\n"
            "    overlap: int = 50,\n"
            "):\n"
            '    """\n'
            "    Chunk all docs, embed each chunk, store in a ChromaDB collection.\n"
            "    Returns the collection object.\n"
            '    """\n'
            "    # TODO: chromadb.Client() — create client\n"
            "    # TODO: delete collection if it exists (try/except), then create_collection\n"
            "    # TODO: for each source, text: chunk → embed → accumulate lists\n"
            "    # TODO: collection.add(ids, embeddings, documents, metadatas)\n"
            "    # TODO: ID format: f\"{source}__{i}\"\n"
            "    # TODO: metadata: {'source': source, 'chunk_index': i}\n"
            "    # TODO: return collection\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "TEST_DOCS = {\n"
            '    "note_a.txt": "Python is a versatile programming language used for data science and AI.",\n'
            '    "note_b.txt": "Machine learning is a branch of artificial intelligence that learns from data.",\n'
            "}\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    col = None\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'build_index' in globals()\n"
            "        passed += 1; print('✅ Check 1: build_index defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: returns a collection (2 embed calls)\n"
            "    try:\n"
            "        col = build_index(TEST_DOCS, collection_name='test_build_020', chunk_size=20, overlap=5)\n"
            "        assert col is not None, 'build_index returned None'\n"
            "        assert hasattr(col, 'query'), 'returned object has no .query method'\n"
            "        passed += 1; print('✅ Check 2: build_index returns a collection')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: collection has documents\n"
            "    try:\n"
            "        assert col is not None, 'collection is None (Check 2 failed)'\n"
            "        count = col.count()\n"
            "        assert count > 0, f'collection is empty (count={count})'\n"
            "        passed += 1; print(f'✅ Check 3: collection has {count} chunk(s)')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: metadata has 'source' key\n"
            "    try:\n"
            "        assert col is not None, 'collection is None'\n"
            "        peek = col.peek(1)\n"
            "        metas = peek['metadatas']\n"
            "        assert len(metas) > 0 and 'source' in metas[0], f\"metadata missing 'source': {metas}\"\n"
            "        passed += 1; print(\"✅ Check 4: metadata contains 'source' key\")\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: collection is queryable (1 embed call)\n"
            "    try:\n"
            "        assert col is not None, 'collection is None'\n"
            "        emb = embed_text('python programming')\n"
            "        res = col.query(query_embeddings=[emb], n_results=1)\n"
            "        assert len(res['documents'][0]) == 1\n"
            "        passed += 1; print('✅ Check 5: collection is queryable')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + BUILD_INDEX_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 03 — retrieve
# ---------------------------------------------------------------------------

def ex03():
    global _cid; _cid = 200
    return [
        md("# Day 020 — Exercise 3: retrieve\n\n"
           "**Goal:** Implement `retrieve(query, collection, n_results)` that embeds the "
           "query and returns the n most similar chunks as `list[{text, source, distance}]`. "
           "**One real Ollama call** (for the query embedding) per check."),
        code("import ollama\nimport chromadb"),
        md("## Provided: chunk_text, embed_text, build_index"),
        code(CHUNK_TEXT_IMPL + "\n\n\n" + EMBED_TEXT_IMPL + "\n\n\n" + BUILD_INDEX_IMPL),
        md("## Your Implementation"),
        code(
            "def retrieve(query: str, collection, n_results: int = 3) -> list[dict]:\n"
            '    """\n'
            "    Semantic search. Returns list[{'text': str, 'source': str, 'distance': float}].\n"
            "    Returns [] if the collection is empty.\n"
            '    """\n'
            "    # TODO: handle empty collection — return [] if collection.count() == 0\n"
            "    # TODO: emb = embed_text(query)\n"
            "    # TODO: actual_n = min(n_results, collection.count())\n"
            "    # TODO: results = collection.query(query_embeddings=[emb], n_results=actual_n)\n"
            "    # TODO: zip results['documents'][0], results['metadatas'][0], results['distances'][0]\n"
            "    # TODO: return list of dicts with keys 'text', 'source', 'distance'\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "TEST_DOCS_3 = {\n"
            '    "python.txt": "Python is a high-level programming language with clean syntax.",\n'
            '    "history.txt": "Artificial intelligence research began in the 1950s with Alan Turing.",\n'
            "}\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    col = build_index(TEST_DOCS_3, collection_name='test_retrieve_020', chunk_size=20, overlap=3)\n"
            "    results = None\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'retrieve' in globals()\n"
            "        passed += 1; print('✅ Check 1: retrieve defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: returns a list (1 embed call)\n"
            "    try:\n"
            "        results = retrieve('python programming', col, n_results=2)\n"
            "        assert isinstance(results, list), f'expected list, got {type(results)}'\n"
            "        passed += 1; print('✅ Check 2: retrieve returns a list')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: items have required keys\n"
            "    try:\n"
            "        assert results is not None and len(results) > 0, 'results list is empty'\n"
            "        for r in results:\n"
            "            for key in ('text', 'source', 'distance'):\n"
            "                assert key in r, f\"missing key '{key}' in result: {r}\"\n"
            "        passed += 1; print('✅ Check 3: each result has text, source, distance')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: n_results limits output (1 embed call)\n"
            "    try:\n"
            "        r1 = retrieve('language', col, n_results=1)\n"
            "        assert len(r1) <= 1, f'expected <= 1 result, got {len(r1)}'\n"
            "        passed += 1; print('✅ Check 4: n_results limits the number of results')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: empty collection returns []\n"
            "    try:\n"
            "        _client = chromadb.Client()\n"
            "        try: _client.delete_collection('empty020col')\n"
            "        except: pass\n"
            "        _empty = _client.create_collection('empty020col')\n"
            "        empty_res = retrieve('anything', _empty, n_results=3)\n"
            "        assert empty_res == [], f'expected [] for empty collection, got {empty_res}'\n"
            "        passed += 1; print('✅ Check 5: empty collection returns []')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: empty collection — {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + RETRIEVE_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 04 — build_cited_prompt
# ---------------------------------------------------------------------------

def ex04():
    global _cid; _cid = 300
    return [
        md("# Day 020 — Exercise 4: build_cited_prompt\n\n"
           "**Goal:** Implement `build_cited_prompt(question, chunks)` — a pure function "
           "that formats retrieved chunks with `[1][2]` citation labels and appends the "
           "question. No model calls — all checks use synthetic data."),
        md("## Your Implementation"),
        code(
            "def build_cited_prompt(question: str, chunks: list[dict]) -> str:\n"
            '    """\n'
            "    Format context chunks with citation numbers for the RAG prompt.\n"
            "    Pure function — no model calls.\n"
            "\n"
            "    Each chunk formatted as:\n"
            "        [1] Source: filename.txt\n"
            "        <chunk text>\n"
            "\n"
            "    Return value:\n"
            "        Context:\n"
            "        <all chunks joined by blank line>\n"
            "\n"
            "        Question: <question>\n"
            '    """\n'
            "    # TODO: context = '\\n\\n'.join(f'[{i+1}] Source: {c[\"source\"]}\\n{c[\"text\"]}' ...)\n"
            "    # TODO: return f'Context:\\n{context}\\n\\nQuestion: {question}'\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "SAMPLE_CHUNKS = [\n"
            "    {'text': 'Python is a high-level language.', 'source': 'python.txt', 'distance': 0.1},\n"
            "    {'text': 'Guido van Rossum created Python in 1991.', 'source': 'history.txt', 'distance': 0.3},\n"
            "]\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    prompt = None\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'build_cited_prompt' in globals()\n"
            "        passed += 1; print('✅ Check 1: build_cited_prompt defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: returns a string\n"
            "    try:\n"
            "        prompt = build_cited_prompt('What is Python?', SAMPLE_CHUNKS)\n"
            "        assert isinstance(prompt, str), f'expected str, got {type(prompt)}'\n"
            "        passed += 1; print('✅ Check 2: build_cited_prompt returns a string')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: {e}')\n"
            "\n"
            "    # Check 3: contains Context: header\n"
            "    try:\n"
            "        assert prompt is not None, 'prompt is None (Check 2 failed)'\n"
            "        assert 'Context:' in prompt, \"missing 'Context:' header\"\n"
            "        passed += 1; print('✅ Check 3: prompt contains \"Context:\" header')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: citation labels [1] and [2]\n"
            "    try:\n"
            "        assert '[1]' in prompt, 'missing citation label [1]'\n"
            "        assert '[2]' in prompt, 'missing citation label [2]'\n"
            "        passed += 1; print('✅ Check 4: citation labels [1] and [2] present')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: question appended\n"
            "    try:\n"
            "        assert 'What is Python?' in prompt, 'question not found in prompt'\n"
            "        passed += 1; print('✅ Check 5: question appears in prompt')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + BUILD_CITED_PROMPT_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Exercise 05 — rag_answer
# ---------------------------------------------------------------------------

def ex05():
    global _cid; _cid = 400
    return [
        md("# Day 020 — Exercise 5: rag_answer\n\n"
           "**Goal:** Implement `rag_answer(question, collection, model, n_results)` — "
           "the full RAG pipeline: retrieve → build_cited_prompt → ollama.chat. "
           "Returns `{'answer': str, 'sources': list[str]}`. "
           "**One embed + one LLM call** in the checks."),
        code("import ollama\nimport chromadb"),
        md("## Provided: all pipeline functions"),
        code(
            CHUNK_TEXT_IMPL + "\n\n\n"
            + EMBED_TEXT_IMPL + "\n\n\n"
            + BUILD_INDEX_IMPL + "\n\n\n"
            + RETRIEVE_IMPL + "\n\n\n"
            + BUILD_CITED_PROMPT_IMPL + "\n\n\n"
            + RAG_SYSTEM_PROMPT_CONST
        ),
        md("## Your Implementation"),
        code(
            "def rag_answer(\n"
            "    question: str,\n"
            "    collection,\n"
            "    model: str = 'llama3.2',\n"
            "    n_results: int = 3,\n"
            ") -> dict:\n"
            '    """\n'
            "    Full RAG pipeline. Returns {'answer': str, 'sources': list[str]}.\n"
            "    If no chunks found, returns {'answer': \"I don't know.\", 'sources': []}.\n"
            '    """\n'
            "    # TODO: chunks = retrieve(question, collection, n_results)\n"
            "    # TODO: if not chunks: return guard response\n"
            "    # TODO: prompt = build_cited_prompt(question, chunks)\n"
            "    # TODO: ollama.chat with RAG_SYSTEM_PROMPT + user prompt\n"
            "    # TODO: sources = list(dict.fromkeys(c['source'] for c in chunks))\n"
            "    # TODO: return {'answer': str, 'sources': list}\n"
            "    pass"
        ),
        md("## Check Your Work"),
        code(
            "TEST_DOCS_5 = {\n"
            '    "ai_notes.txt": (\n'
            '        "Neural networks learn from data by adjusting weights during training. "\n'
            '        "Deep learning uses many stacked layers to find complex patterns."\n'
            "    ),\n"
            "}\n"
            "\n"
            "def _run_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "    col = build_index(TEST_DOCS_5, collection_name='test_rag_020', chunk_size=20, overlap=3)\n"
            "    result = None\n"
            "\n"
            "    # Check 1: defined\n"
            "    try:\n"
            "        assert 'rag_answer' in globals()\n"
            "        passed += 1; print('✅ Check 1: rag_answer defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: empty collection guard (no LLM call)\n"
            "    try:\n"
            "        _client = chromadb.Client()\n"
            "        try: _client.delete_collection('emptyragcol')\n"
            "        except: pass\n"
            "        _empty = _client.create_collection('emptyragcol')\n"
            "        guard = rag_answer('test question', _empty)\n"
            "        assert guard['answer'] == \"I don't know.\", f\"got: {guard['answer']!r}\"\n"
            "        assert guard['sources'] == [], f\"got: {guard['sources']}\"\n"
            "        passed += 1; print(\"✅ Check 2: empty collection returns I don't know.\")\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: empty guard — {e}')\n"
            "\n"
            "    # Check 3: returns dict with answer + sources (1 embed + 1 LLM call)\n"
            "    try:\n"
            "        result = rag_answer('What do neural networks do?', col)\n"
            "        assert isinstance(result, dict), f'expected dict, got {type(result)}'\n"
            "        assert 'answer' in result and 'sources' in result, f'missing keys: {list(result)}'\n"
            "        passed += 1; print('✅ Check 3: returns dict with answer and sources')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: {e}')\n"
            "\n"
            "    # Check 4: answer is a non-empty string\n"
            "    try:\n"
            "        assert result is not None, 'result is None (Check 3 failed)'\n"
            "        assert isinstance(result['answer'], str) and len(result['answer']) > 0\n"
            "        passed += 1; print('✅ Check 4: answer is a non-empty string')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: {e}')\n"
            "\n"
            "    # Check 5: sources is list[str]\n"
            "    try:\n"
            "        assert isinstance(result['sources'], list), f\"expected list, got {type(result['sources'])}\"\n"
            "        for s in result['sources']:\n"
            "            assert isinstance(s, str), f'source is not a string: {s!r}'\n"
            "        passed += 1; print(f\"✅ Check 5: sources is list[str] — {result['sources']}\")\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Exercise complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_checks()"
        ),
        md(
            "## Solution\n\n"
            "<details>\n"
            "<summary>Click to reveal</summary>\n\n"
            "```python\n"
            + RAG_ANSWER_IMPL + "\n"
            "```\n\n"
            "</details>"
        ),
    ]


# ---------------------------------------------------------------------------
# Project notebook (student template)
# ---------------------------------------------------------------------------

SECOND_BRAIN_CHATBOT_IMPL = """\
class SecondBrainChatbot:
    def __init__(self, docs: dict, model: str = "llama3.2",
                 chunk_size: int = 300, overlap: int = 50):
        self.model = model
        self.collection = build_index(docs, chunk_size=chunk_size, overlap=overlap)
        self._history: list[dict] = []

    def ask(self, question: str) -> dict:
        result = rag_answer(question, self.collection, self.model)
        self._history.append({
            "q": question,
            "a": result["answer"],
            "sources": result["sources"],
        })
        return result

    def summary(self) -> str:
        return f"Questions asked: {len(self._history)}"\
"""


def project_nb():
    global _cid; _cid = 500
    return [
        md(
            "# Day 020 Project — Second Brain Chatbot\n\n"
            "Build a `SecondBrainChatbot` that wraps the RAG pipeline you built in "
            "Exercises 1–5 into a usable Q&A assistant over your personal knowledge base.\n\n"
            "## Project Requirements\n\n"
            "1. Define at least **3 documents** as string constants (your knowledge base)\n"
            "2. Implement `SecondBrainChatbot` with `__init__(docs, model, chunk_size, overlap)` and `ask(question) -> dict`\n"
            "3. Ask at least **3 scripted questions** and print each answer with sources\n"
            "4. Define at least **3 `TestCase` objects** and run a mini eval with `contains_any` scoring\n"
            "5. Run the checks below to verify correctness\n"
        ),
        code(
            "import re\n"
            "import ollama\n"
            "import chromadb\n"
            "from dataclasses import dataclass, field\n"
        ),
        md("## Provided: RAG Pipeline"),
        code(
            CHUNK_TEXT_IMPL + "\n\n\n"
            + EMBED_TEXT_IMPL + "\n\n\n"
            + BUILD_INDEX_IMPL + "\n\n\n"
            + RETRIEVE_IMPL + "\n\n\n"
            + BUILD_CITED_PROMPT_IMPL + "\n\n\n"
            + RAG_SYSTEM_PROMPT_CONST + "\n\n\n"
            + RAG_ANSWER_IMPL
        ),
        md("## Provided: Eval Helpers (Day 19)"),
        code(
            "@dataclass\n"
            "class TestCase:\n"
            "    question: str\n"
            "    expected_keywords: list[str] = field(default_factory=list)\n"
            "    expected_answer: str = ''\n"
            "\n"
            "\n"
            "def contains_any(response: str, keywords: list[str]) -> bool:\n"
            "    resp_lower = response.lower()\n"
            "    return any(kw.lower() in resp_lower for kw in keywords)\n"
        ),
        md("## Your Implementation\n\n"
           "Define your documents and implement `SecondBrainChatbot`."),
        code(
            "# --- Your knowledge base ---\n"
            "DOCS = {\n"
            "    'doc1.txt': 'Your first document text here...',\n"
            "    'doc2.txt': 'Your second document text here...',\n"
            "    'doc3.txt': 'Your third document text here...',\n"
            "}\n"
            "\n"
            "\n"
            "class SecondBrainChatbot:\n"
            "    def __init__(self, docs: dict, model: str = 'llama3.2',\n"
            "                 chunk_size: int = 300, overlap: int = 50):\n"
            "        # TODO: store model, build collection with build_index, init history\n"
            "        pass\n"
            "\n"
            "    def ask(self, question: str) -> dict:\n"
            "        # TODO: call rag_answer, append to history, return result\n"
            "        pass\n"
            "\n"
            "    def summary(self) -> str:\n"
            "        # TODO: return a summary string with question count\n"
            "        pass\n"
        ),
        md("## Ask Questions"),
        code(
            "# Build chatbot and ask 3 scripted questions\n"
            "# bot = SecondBrainChatbot(DOCS)\n"
            "# result = bot.ask('Your question here?')\n"
            "# print(result['answer'])\n"
            "# print('Sources:', result['sources'])\n"
        ),
        md("## Mini Eval Run"),
        code(
            "EVAL_CASES = [\n"
            "    # TestCase('question', expected_keywords=['keyword1', 'keyword2']),\n"
            "]\n"
            "\n"
            "# eval_results = []\n"
            "# for tc in EVAL_CASES:\n"
            "#     answer = bot.ask(tc.question)['answer']\n"
            "#     matched = [kw for kw in tc.expected_keywords if kw.lower() in answer.lower()]\n"
            "#     passed_check = bool(matched) if tc.expected_keywords else True\n"
            "#     icon = '✅' if passed_check else '❌'\n"
            "#     print(f'{icon} {tc.question[:60]}')\n"
            "#     if matched: print(f'   Keywords: {matched}')\n"
            "#     eval_results.append(passed_check)\n"
            "# pass_rate = sum(eval_results) / len(eval_results) if eval_results else 0.0\n"
            "# print(f'\\nEval pass rate: {pass_rate*100:.1f}%')\n"
        ),
        md("## Checks"),
        code(
            "def _run_project_checks():\n"
            "    total = 5\n"
            "    passed = 0\n"
            "\n"
            "    # Check 1: SecondBrainChatbot class defined with required methods\n"
            "    try:\n"
            "        assert 'SecondBrainChatbot' in globals()\n"
            "        assert hasattr(SecondBrainChatbot, 'ask')\n"
            "        assert hasattr(SecondBrainChatbot, 'summary')\n"
            "        passed += 1; print('✅ Check 1: SecondBrainChatbot class defined')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 1: {e}')\n"
            "\n"
            "    # Check 2: DOCS has at least 3 documents\n"
            "    try:\n"
            "        assert 'DOCS' in globals(), 'DOCS not defined'\n"
            "        assert len(DOCS) >= 3, f'Need >= 3 docs, got {len(DOCS)}'\n"
            "        passed += 1; print(f'✅ Check 2: DOCS has {len(DOCS)} documents')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 2: DOCS — {e}')\n"
            "\n"
            "    # Check 3: chatbot builds and ask() works (embed + LLM call)\n"
            "    try:\n"
            "        _bot = SecondBrainChatbot(DOCS)\n"
            "        assert _bot is not None\n"
            "        _result = _bot.ask(list(DOCS.keys())[0])  # ask a question about first doc name\n"
            "        assert isinstance(_result, dict), f'ask() must return dict, got {type(_result)}'\n"
            "        assert 'answer' in _result and 'sources' in _result\n"
            "        passed += 1; print('✅ Check 3: chatbot builds and ask() returns valid dict')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 3: chatbot.ask() — {e}')\n"
            "\n"
            "    # Check 4: EVAL_CASES has at least 3 cases\n"
            "    try:\n"
            "        assert 'EVAL_CASES' in globals(), 'EVAL_CASES not defined'\n"
            "        assert len(EVAL_CASES) >= 3, f'Need >= 3 eval cases, got {len(EVAL_CASES)}'\n"
            "        passed += 1; print(f'✅ Check 4: EVAL_CASES has {len(EVAL_CASES)} cases')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 4: EVAL_CASES — {e}')\n"
            "\n"
            "    # Check 5: history grows with each ask()\n"
            "    try:\n"
            "        _b2 = SecondBrainChatbot({'note.txt': 'Python is a programming language.'})\n"
            "        _b2.ask('What is Python?')\n"
            "        _b2.ask('Tell me more.')\n"
            "        assert len(_b2._history) == 2, f'expected 2 history entries, got {len(_b2._history)}'\n"
            "        passed += 1; print('✅ Check 5: history accumulates with each ask()')\n"
            "    except Exception as e:\n"
            "        print(f'❌ Check 5: history — {e}')\n"
            "\n"
            "    if passed == total:\n"
            "        print('🎉 Project complete!')\n"
            "    print(f'\\nScore: {passed}/{total}')\n"
            "\n"
            "_run_project_checks()\n"
        ),
        md(
            "## Bonus Challenges\n\n"
            "- Use ChromaDB's `PersistentClient` so the index survives between sessions\n"
            "- Add token tracking from Day 18: include `UsageTracker` in `SecondBrainChatbot` "
            "and print total token usage in `summary()`\n"
            "- Filter low-quality retrieved chunks by `distance` threshold before building the prompt\n"
            "- Add an `llm_judge` eval run (Day 19) to score answer quality alongside keyword checks\n"
            "- Try different `chunk_size`/`overlap` values and observe how retrieval quality changes"
        ),
    ]


# ---------------------------------------------------------------------------
# Solution notebook
# ---------------------------------------------------------------------------

def solution_nb():
    global _cid; _cid = 600

    python_notes = (
        "Python is a high-level, general-purpose programming language known for its "
        "clean and readable syntax. It was created by Guido van Rossum and first released "
        "in 1991. Python supports multiple programming paradigms including procedural, "
        "object-oriented, and functional programming. It is widely used in data science, "
        "machine learning, web development, and automation. The Python Package Index (PyPI) "
        "hosts hundreds of thousands of third-party libraries. Python uses indentation to "
        "define code blocks, which enforces readable code structure. Common data structures "
        "in Python include lists, tuples, dictionaries, and sets."
    )

    ai_history = (
        "The field of artificial intelligence began in the 1950s. Alan Turing proposed the "
        "Turing Test in 1950 as a measure of machine intelligence. The Dartmouth Conference "
        "in 1956 is widely regarded as the birthplace of AI as a formal discipline. Early AI "
        "research focused on symbolic reasoning and rule-based systems. The development of "
        "neural networks began in the 1950s with the perceptron, invented by Frank Rosenblatt. "
        "AI went through periods of reduced funding known as AI winters in the 1970s and 1980s. "
        "The deep learning revolution began around 2012 when convolutional neural networks "
        "dramatically improved image recognition accuracy."
    )

    llm_concepts = (
        "Large language models are neural networks trained on vast amounts of text data. "
        "They learn statistical patterns in language and can generate coherent text. "
        "The transformer architecture, introduced in 2017 in the paper Attention Is All You Need, "
        "is the foundation of modern LLMs. Transformers use self-attention mechanisms to "
        "model relationships between tokens in a sequence. GPT models are autoregressive, "
        "generating one token at a time based on the preceding context. Retrieval-augmented "
        "generation (RAG) combines LLMs with external knowledge retrieval to reduce hallucination. "
        "Context window refers to the maximum number of tokens a model can process at once."
    )

    chatbot_class = (
        "class SecondBrainChatbot:\n"
        "    def __init__(self, docs: dict, model: str = 'llama3.2',\n"
        "                 chunk_size: int = 300, overlap: int = 50):\n"
        "        self.model = model\n"
        "        self.collection = build_index(docs, chunk_size=chunk_size, overlap=overlap)\n"
        "        self._history: list[dict] = []\n"
        "\n"
        "    def ask(self, question: str) -> dict:\n"
        "        result = rag_answer(question, self.collection, self.model)\n"
        "        self._history.append({\n"
        "            'q': question,\n"
        "            'a': result['answer'],\n"
        "            'sources': result['sources'],\n"
        "        })\n"
        "        return result\n"
        "\n"
        "    def summary(self) -> str:\n"
        "        return f'Questions asked: {len(self._history)}'\n"
    )

    demo_questions = [
        "What programming language is known for clean syntax and was created by Guido van Rossum?",
        "When did the field of artificial intelligence begin, and who proposed the Turing Test?",
        "What architecture is the foundation of modern large language models?",
    ]

    eval_cases_code = (
        "from dataclasses import dataclass, field\n"
        "\n"
        "\n"
        "@dataclass\n"
        "class TestCase:\n"
        "    question: str\n"
        "    expected_keywords: list[str] = field(default_factory=list)\n"
        "\n"
        "\n"
        "def contains_any(response: str, keywords: list[str]) -> bool:\n"
        "    resp_lower = response.lower()\n"
        "    return any(kw.lower() in resp_lower for kw in keywords)\n"
        "\n"
        "\n"
        "EVAL_CASES = [\n"
        "    TestCase(\n"
        "        'What is Python used for?',\n"
        "        expected_keywords=['data science', 'machine learning', 'automation', 'web'],\n"
        "    ),\n"
        "    TestCase(\n"
        "        'What is the Turing Test?',\n"
        "        expected_keywords=['intelligence', 'machine', 'turing'],\n"
        "    ),\n"
        "    TestCase(\n"
        "        'What does RAG stand for and what does it do?',\n"
        "        expected_keywords=['retrieval', 'generation', 'hallucination', 'knowledge'],\n"
        "    ),\n"
        "]\n"
    )

    return [
        md("# Day 020 Project Solution — Second Brain Chatbot\n\n"
           "A complete RAG chatbot over a personal knowledge base, with scripted "
           "Q&A and a mini eval run."),
        code(
            "import ollama\n"
            "import chromadb\n"
        ),
        md("## RAG Pipeline"),
        code(
            CHUNK_TEXT_IMPL + "\n\n\n"
            + EMBED_TEXT_IMPL + "\n\n\n"
            + BUILD_INDEX_IMPL + "\n\n\n"
            + RETRIEVE_IMPL + "\n\n\n"
            + BUILD_CITED_PROMPT_IMPL + "\n\n\n"
            + RAG_SYSTEM_PROMPT_CONST + "\n\n\n"
            + RAG_ANSWER_IMPL
        ),
        md("## SecondBrainChatbot"),
        code(chatbot_class),
        md("## Knowledge Base"),
        code(
            f"PYTHON_NOTES = {repr(python_notes)}\n\n"
            f"AI_HISTORY = {repr(ai_history)}\n\n"
            f"LLM_CONCEPTS = {repr(llm_concepts)}\n\n"
            "DOCS = {\n"
            "    'python_notes.txt':  PYTHON_NOTES,\n"
            "    'ai_history.txt':    AI_HISTORY,\n"
            "    'llm_concepts.txt':  LLM_CONCEPTS,\n"
            "}\n\n"
            "bot = SecondBrainChatbot(DOCS)\n"
            'print("Knowledge base indexed.")\n'
        ),
        md("## Scripted Q&A Session"),
        code(
            f"QUESTIONS = {repr(demo_questions)}\n\n"
            "for i, q in enumerate(QUESTIONS, 1):\n"
            "    print(f'--- Q{i} ---')\n"
            "    print(f'Q: {q}')\n"
            "    result = bot.ask(q)\n"
            "    print(f\"A: {result['answer'][:300]}\")\n"
            "    print(f\"Sources: {result['sources']}\")\n"
            "    print()\n"
        ),
        md("## Mini Eval Run"),
        code(eval_cases_code),
        code(
            "eval_results = []\n"
            "for tc in EVAL_CASES:\n"
            "    answer = bot.ask(tc.question)['answer']\n"
            "    matched = [kw for kw in tc.expected_keywords\n"
            "               if kw.lower() in answer.lower()]\n"
            "    ok = bool(matched) if tc.expected_keywords else True\n"
            "    icon = '\\u2705' if ok else '\\u274c'\n"
            "    print(f'{icon} {tc.question[:60]}')\n"
            "    if matched:\n"
            "        print(f'   Keywords: {matched}')\n"
            "    eval_results.append(ok)\n"
            "\n"
            "pass_rate = sum(eval_results) / len(eval_results) if eval_results else 0.0\n"
            "print(f'\\nEval pass rate: {pass_rate*100:.1f}%')\n"
            "print(bot.summary())\n"
        ),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating Day 020 notebooks...")
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
    write_nb(proj_dir / "project.ipynb",   project_nb())
    write_nb(sol_dir  / "solution.ipynb",  solution_nb())
    print("Done.")


if __name__ == "__main__":
    main()
