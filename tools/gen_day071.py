#!/usr/bin/env python3
"""gen_day071.py — generate Day 071: Vision + RAG."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "071"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: visual_search.py ────────────────────────────────────────────
_SEARCH_SRC = '''\
"""visual_search.py — Day 071: Vision + RAG.

Content-based image retrieval: describe images with a vision LLM,
embed descriptions with a text model, search by text or image query.

Setup (real usage):
    ollama pull llava              # vision model
    ollama pull nomic-embed-text   # embedding model

Usage:
    from visual_search import ImageSearchEngine
    from PIL import Image

    # Offline testing — inject mocks
    mock_describe = lambda b64, p: "a red car on a road"
    mock_embed    = lambda text: [0.1, 0.9, 0.2, 0.4]
    engine = ImageSearchEngine(describe_fn=mock_describe, embed_fn=mock_embed)
    img = Image.new("RGB", (64, 64), "red")
    engine.add_image("img1", img, metadata={"label": "car"})
    results = engine.search("car", n=1)
    print(results[0]["id"], results[0]["score"])
"""
import base64
import io
import math
import numpy as np
from PIL import Image
from typing import Optional, Callable

_SEARCH_PROMPT = (
    "Describe this image in detail for use in a semantic search index. "
    "Include: main subjects, colors, textures, setting, and any visible text. "
    "Write one concise paragraph of 2-3 sentences."
)


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buf = io.BytesIO()
    out = img
    if format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "P"):
        out = img.convert("RGB")
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()


def cosine_similarity(a, b) -> float:
    """Cosine similarity between two vectors. Returns 0.0 if either is zero."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class ImageIndex:
    """In-memory image search index backed by cosine similarity."""

    def __init__(self) -> None:
        self._items: list = []

    def add(self, image_id: str, description: str, embedding,
            metadata: Optional[dict] = None) -> None:
        """Add an image to the index."""
        self._items.append({
            "id":          image_id,
            "description": description,
            "embedding":   np.array(embedding, dtype=np.float32),
            "metadata":    metadata or {},
        })

    def search(self, query_embedding, n: int = 5) -> list:
        """Return top-n results sorted by cosine similarity (descending).

        Each result dict has keys: id, description, score, metadata.
        """
        if not self._items:
            return []
        q = np.array(query_embedding, dtype=np.float32)
        scored = [
            (cosine_similarity(q, item["embedding"]), item)
            for item in self._items
        ]
        scored.sort(key=lambda x: -x[0])
        top = scored[:min(n, len(scored))]
        return [
            {
                "id":          item["id"],
                "description": item["description"],
                "score":       float(score),
                "metadata":    item["metadata"],
            }
            for score, item in top
        ]

    def __len__(self) -> int:
        return len(self._items)


def describe_image_for_search(img: Image.Image,
                               describe_fn: Optional[Callable] = None) -> str:
    """Generate a text description of an image for search indexing.

    Args:
        img:         PIL Image
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        Text description string
    """
    img_b64 = image_to_base64(img)
    if describe_fn is not None:
        return describe_fn(img_b64, _SEARCH_PROMPT)
    import ollama
    resp = ollama.chat(
        model="llava",
        messages=[{
            "role":    "user",
            "content": _SEARCH_PROMPT,
            "images":  [img_b64],
        }],
    )
    return resp["message"]["content"].strip()


def embed_text(text: str, embed_fn: Optional[Callable] = None) -> list:
    """Embed text to a float vector.

    Args:
        text:     Input string
        embed_fn: callable(text) -> list[float] for testing
    Returns:
        list of float (embedding vector)
    """
    if embed_fn is not None:
        return embed_fn(text)
    import ollama
    resp = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return resp["embedding"]


def index_images(images_with_ids: list,
                 describe_fn: Optional[Callable] = None,
                 embed_fn: Optional[Callable] = None) -> "ImageIndex":
    """Describe, embed, and index a batch of images.

    Args:
        images_with_ids: list of (image_id, img, metadata) tuples
        describe_fn:     callable(img_b64, prompt) -> str for testing
        embed_fn:        callable(text) -> list[float] for testing
    Returns:
        Populated ImageIndex
    """
    index = ImageIndex()
    for image_id, img, metadata in images_with_ids:
        desc = describe_image_for_search(img, describe_fn=describe_fn)
        emb  = embed_text(desc, embed_fn=embed_fn)
        index.add(image_id, desc, emb, metadata or {})
    return index


def search_by_text(query: str, index: "ImageIndex",
                   embed_fn: Optional[Callable] = None,
                   n: int = 5) -> list:
    """Search the index by a text query.

    Args:
        query:    Text search query
        index:    Populated ImageIndex
        embed_fn: callable(text) -> list[float] for testing
        n:        Maximum number of results
    Returns:
        list of result dicts (id, description, score, metadata)
    """
    q_emb = embed_text(query, embed_fn=embed_fn)
    return index.search(q_emb, n=n)


def search_by_image(img: Image.Image, index: "ImageIndex",
                    describe_fn: Optional[Callable] = None,
                    embed_fn: Optional[Callable] = None,
                    n: int = 5) -> list:
    """Search the index using an image as the query.

    Args:
        img:         Query PIL Image
        index:       Populated ImageIndex
        describe_fn: callable(img_b64, prompt) -> str for testing
        embed_fn:    callable(text) -> list[float] for testing
        n:           Maximum number of results
    Returns:
        list of result dicts (id, description, score, metadata)
    """
    desc  = describe_image_for_search(img, describe_fn=describe_fn)
    q_emb = embed_text(desc, embed_fn=embed_fn)
    return index.search(q_emb, n=n)


class ImageSearchEngine:
    """Content-based image search engine.

    Inject describe_fn and embed_fn for testing without Ollama::

        engine = ImageSearchEngine(
            describe_fn=lambda b64, p: "a sunny beach",
            embed_fn=lambda t: [0.5, 0.3, 0.8],
        )
    """

    def __init__(self, describe_fn: Optional[Callable] = None,
                 embed_fn: Optional[Callable] = None) -> None:
        self._describe_fn = describe_fn
        self._embed_fn    = embed_fn
        self._index       = ImageIndex()

    def add_image(self, image_id: str, img: Image.Image,
                  metadata: Optional[dict] = None) -> str:
        """Index one image. Returns the generated description."""
        desc = describe_image_for_search(img, describe_fn=self._describe_fn)
        emb  = embed_text(desc, embed_fn=self._embed_fn)
        self._index.add(image_id, desc, emb, metadata or {})
        return desc

    def add_batch(self, images_with_ids: list) -> list:
        """Index a batch of (image_id, img, metadata) tuples.

        Returns list of generated description strings.
        """
        return [
            self.add_image(image_id, img, metadata)
            for image_id, img, metadata in images_with_ids
        ]

    def search(self, query: str, n: int = 5) -> list:
        """Search by text query. Returns list of result dicts."""
        return search_by_text(query, self._index,
                              embed_fn=self._embed_fn, n=n)

    def search_by_image(self, img: Image.Image, n: int = 5) -> list:
        """Search by image query. Returns list of result dicts."""
        return search_by_image(img, self._index,
                               describe_fn=self._describe_fn,
                               embed_fn=self._embed_fn, n=n)

    def __len__(self) -> int:
        return len(self._index)
'''

# ── notebook helpers ──────────────────────────────────────────────────────────
def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"}},
        "cells": cells,
    }

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None}

def save(path, notebook):
    Path(path).write_text(json.dumps(notebook, indent=1))

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "071"
lesson: 1
title: "Vision RAG — Concept and Architecture"
slides:
  - type: title
    heading: "Vision + RAG"
    subheading: "Day 71 — Content-based image search with vision LLMs"
    narration: >
      Days 67 through 70 built the vision half of this day: describing images,
      extracting structured data, generating images. Days 11 through 13 built
      the search half: embeddings, vector databases, and RAG. Today you combine
      them. Vision RAG is content-based image retrieval — find images by what
      they contain, not by their filename or tag.

  - type: concept
    label: "The problem"
    heading: "Why You Cannot Keyword-Search Images"
    body: >
      A JPEG has no built-in text content. Traditional keyword search only
      finds images whose filenames or tags were manually entered. Vision RAG
      solves this by generating text automatically.
    bullets:
      - "Filename search: only finds cars if someone named the file car.jpg"
      - "Manual tagging: expensive, inconsistent, incomplete at scale"
      - "Vision RAG: let the LLM read the image and generate searchable text"
      - "Result: search 10,000 images by content with no human labelling"
    narration: >
      Every image-heavy app eventually hits the same wall: users search for
      a concept and get back nothing because the relevant image was never
      manually tagged. Vision RAG bypasses this entirely. The vision LLM acts
      as an automatic tagger — one that reads colour, subject, setting, mood,
      and visible text. The text description is then embedded in the same
      vector space as text queries, so searching by text and searching by
      content become the same operation.

  - type: how_it_works
    label: "Pipeline"
    heading: "The Vision RAG Pipeline"
    body: >
      Four stages: describe, embed, store, retrieve. Two of these stages
      run at index time, two at query time.
    bullets:
      - "Index: image → vision LLM → description string"
      - "Index: description → text embedding model → float vector → store"
      - "Query: user query text → same embedding model → float vector"
      - "Retrieve: cosine similarity between query vector and all stored vectors"
    narration: >
      Indexing is the offline phase: run it once per image. For each image,
      call the vision LLM to get a text description, then call the embedding
      model to convert that description to a float vector. Store both the
      vector and the original description in the index. At query time, embed
      the query text (or describe a query image first), then compute cosine
      similarity against every stored vector and return the top N. The two
      embedding calls use the same model, so the query and document vectors
      are in the same space.

  - type: code
    label: "Mocking"
    heading: "The Two Injection Points"
    code: |
      from PIL import Image

      # Injection point 1: vision LLM
      # describe_fn(img_b64: str, prompt: str) -> str
      mock_describe = lambda b64, p: 'a red car on a sunny road'

      # Injection point 2: text embedding model
      # embed_fn(text: str) -> list[float]
      mock_embed = lambda text: [0.1, 0.9, 0.3, 0.5]

      # Both injected at engine construction time
      from visual_search import ImageSearchEngine
      engine = ImageSearchEngine(
          describe_fn=mock_describe,
          embed_fn=mock_embed,
      )
      img = Image.new('RGB', (64, 64), 'red')
      desc = engine.add_image('car_001', img, {'label': 'car'})
      print(desc)   # a red car on a sunny road
    narration: >
      Two injection points means two independently mockable components.
      In tests you can inject a describe_fn that returns a fixed string and
      an embed_fn that returns a fixed vector — no Ollama required, no GPU
      required, gate runs in under a second. In production you swap both
      None values back in and the real Ollama calls run. None of the routing
      or search logic changes.

  - type: concept
    label: "vs Day 13"
    heading: "Vision RAG vs Text RAG (Day 13)"
    body: >
      Text RAG stores chunks of text documents. Vision RAG stores
      LLM-generated image descriptions. The retrieval mechanism is identical.
    bullets:
      - "Text RAG: split document → embed chunk → store → embed query → retrieve"
      - "Vision RAG: describe image → embed description → store → embed query → retrieve"
      - "Same cosine similarity search either way"
      - "Difference: the source of the indexed text (chunks vs LLM descriptions)"
    narration: >
      The retrieval half of Vision RAG is exactly the same as Day 13. The
      difference is in what gets indexed. Instead of splitting a PDF into
      chunks, you run each image through a vision LLM to produce a text
      chunk. From the vector store's perspective, both look identical: a
      text string and a float vector. This means any vector database from
      Day 12 — ChromaDB, FAISS, or a pure-numpy in-memory index — works
      unchanged for Vision RAG.

  - type: exercise
    heading: "Exercise 1: cosine_similarity + ImageIndex"
    prompt: >
      Implement cosine_similarity(a, b) -> float: compute dot(a, b) /
      (norm(a) * norm(b)). Return 0.0 if either norm is zero.
      Then implement ImageIndex with add(image_id, description, embedding,
      metadata=None), search(query_embedding, n=5) -> list[dict], and __len__().
      search returns dicts with keys id, description, score, metadata,
      sorted by score descending.
    hint: >
      cosine_similarity: np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)).
      search: score each item, sort by -score, slice [:n], return without embedding key.
    narration: >
      cosine_similarity and ImageIndex are the retrieval core of Vision RAG.
      Everything else — description, embedding, indexing — just feeds data into
      these two pieces.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Vision RAG = image → LLM description → embedding → vector search"
      - "Two injection points: describe_fn (vision LLM) and embed_fn (text embedder)"
      - "Index time: describe + embed + store. Query time: embed + cosine search"
      - "Same retrieval mechanism as Text RAG (Day 13)"
      - "cosine_similarity: dot(a,b)/(norm_a * norm_b), 0.0 on zero vector"
    narration: >
      The concept and the retrieval core are settled. Next: the two
      transformation functions that feed the index — describing images and
      embedding text.
"""

_LESSON_02 = """\
day: "071"
lesson: 2
title: "Describing and Embedding Images"
slides:
  - type: title
    heading: "Describing and Embedding Images"
    subheading: "describe_image_for_search and embed_text"
    narration: >
      The ImageIndex from Lesson 1 needs float vectors to search against.
      This lesson builds the two functions that produce those vectors:
      describe_image_for_search converts a PIL Image to a text description,
      and embed_text converts that text to a float vector. Both accept mock
      callables so they run in tests without Ollama.

  - type: concept
    label: "Search prompt"
    heading: "Writing a Search-Optimised Description Prompt"
    body: >
      The search prompt is different from the general describe prompt in
      Day 67. It asks for indexable, searchable content rather than a
      narrative sentence.
    bullets:
      - "Day 67 prompt: describe what you see in one sentence"
      - "Search prompt: list subjects, colours, setting, visible text, mood"
      - "Richer description = more attributes to match queries against"
      - "Consistent format = more uniform embedding space"
    narration: >
      A general-purpose description like "A man sitting in a chair" embeds
      differently from a search-optimised description like "A middle-aged man
      in a blue shirt seated at a wooden desk in an office, with bookshelves
      behind him, warm lighting, casual professional setting." The second
      version has far more query-matchable attributes. When a user searches
      for "office" or "bookshelves" or "warm lighting", the richer description
      produces a higher cosine similarity than the sparse one.

  - type: code
    label: "describe_image_for_search"
    heading: "describe_image_for_search"
    code: |
      _SEARCH_PROMPT = (
          'Describe this image in detail for use in a semantic search index. '
          'Include: main subjects, colors, textures, setting, and visible text. '
          'Write one concise paragraph of 2-3 sentences.'
      )

      def describe_image_for_search(img, describe_fn=None):
          img_b64 = image_to_base64(img)
          if describe_fn is not None:
              return describe_fn(img_b64, _SEARCH_PROMPT)
          import ollama
          resp = ollama.chat(
              model='llava',
              messages=[{'role': 'user', 'content': _SEARCH_PROMPT,
                         'images': [img_b64]}],
          )
          return resp['message']['content'].strip()
    narration: >
      The function follows the same describe_fn=None injection pattern
      established on Day 67. image_to_base64 is called once to get the
      base64 string, then describe_fn is called with that string and the
      search-optimised prompt. When describe_fn is None, a real Ollama llava
      call runs instead. The `.strip()` removes any leading or trailing
      whitespace from the model's response before storing in the index.

  - type: concept
    label: "embed_text"
    heading: "Text Embeddings for Search"
    body: >
      The same embedding model must be used for both indexing and querying.
      Ollama supports nomic-embed-text, a fast 768-dim text embedding model.
    bullets:
      - "ollama pull nomic-embed-text (run once before real usage)"
      - "ollama.embeddings(model='nomic-embed-text', prompt=text) -> {'embedding': [...]}"
      - "Dimensions: 768 floats per text string"
      - "embed_fn=None injection: same pattern as describe_fn"
    narration: >
      nomic-embed-text is a dedicated embedding model, not a chat model.
      It converts any text string to a 768-dimensional float vector that
      captures semantic meaning. The same model must be used for both
      document embedding (at index time) and query embedding (at search time)
      so both live in the same vector space and cosine similarity is
      meaningful. For tests, the mock embed_fn returns a small fixed vector
      of any dimension — cosine similarity works on any dimension.

  - type: code
    label: "embed_text"
    heading: "embed_text Implementation"
    code: |
      def embed_text(text, embed_fn=None):
          if embed_fn is not None:
              return embed_fn(text)
          import ollama
          resp = ollama.embeddings(model='nomic-embed-text', prompt=text)
          return resp['embedding']

      # Mock for testing — returns a deterministic 4-dim vector
      import hashlib

      def _mock_embed(text):
          h = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
          return [((h >> (i * 8)) & 0xff) / 128.0 - 1.0 for i in range(4)]

      print(_mock_embed('a red car'))   # e.g. [0.34, -0.12, 0.88, -0.5]
      print(_mock_embed('a blue sky'))  # different vector
    narration: >
      The hashlib-based mock is deterministic — same text always returns the
      same vector. Different texts return different vectors. This makes tests
      reliable without needing a running Ollama instance. The vector is 4
      dimensions (arbitrary), which is fine for cosine similarity — the math
      works on any dimension. In production, nomic-embed-text returns 768
      dimensions.

  - type: exercise
    heading: "Exercise 2: describe_image_for_search + embed_text"
    prompt: >
      Implement describe_image_for_search(img, describe_fn=None) -> str:
      call image_to_base64(img) then describe_fn(img_b64, _SEARCH_PROMPT)
      if describe_fn is not None, else use ollama.chat with model='llava'.
      Strip the result.
      Implement embed_text(text, embed_fn=None) -> list[float]:
      call embed_fn(text) if not None, else use
      ollama.embeddings(model='nomic-embed-text', prompt=text).
    hint: >
      describe: img_b64 = image_to_base64(img); if describe_fn: return describe_fn(img_b64, _SEARCH_PROMPT).strip().
      embed: if embed_fn: return embed_fn(text); else import ollama; return ollama.embeddings(...)['embedding'].
    narration: >
      These two functions are the data pipeline into the index. Together
      they take a PIL Image and return a float vector — converting visual
      content to a point in semantic space.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "Search prompt: richer than general describe — lists subjects, colours, setting, text"
      - "describe_image_for_search: image_to_base64 → describe_fn or ollama.chat llava"
      - "embed_text: embed_fn or ollama.embeddings nomic-embed-text"
      - "Both use fn=None injection — same pattern as Day 67"
      - "Mock embed: hashlib MD5 → deterministic 4-dim vector"
    narration: >
      The data pipeline into the index is ready. Next: building the full
      index from a batch of images with index_images.
"""

_LESSON_03 = """\
day: "071"
lesson: 3
title: "Building the Image Index"
slides:
  - type: title
    heading: "Building the Image Index"
    subheading: "index_images — batch describe, embed, store"
    narration: >
      With describe_image_for_search and embed_text in place, indexing a
      collection is a simple loop. This lesson builds index_images, which
      takes a list of images and returns a populated ImageIndex ready to
      query.

  - type: how_it_works
    label: "index_images"
    heading: "index_images: Input Format and Logic"
    body: >
      Input is a list of tuples: (image_id, img, metadata). Output is a
      populated ImageIndex. One loop body: describe → embed → add.
    bullets:
      - "Each tuple: (str image_id, PIL Image, dict metadata)"
      - "Describe: call describe_image_for_search(img, describe_fn)"
      - "Embed: call embed_text(desc, embed_fn)"
      - "Store: index.add(image_id, desc, emb, metadata)"
    narration: >
      The tuple input format keeps the function signature clean: one argument
      per image item, no parallel lists to keep in sync. Using a list of
      tuples also means the caller can zip together separate id and image lists
      if they already have them that way. The metadata dict holds any extra
      information about the image — filename, date, category, source — that
      should be returned with search results without being part of the
      embedding.

  - type: code
    label: "index_images"
    heading: "index_images Implementation"
    code: |
      def index_images(images_with_ids, describe_fn=None, embed_fn=None):
          index = ImageIndex()
          for image_id, img, metadata in images_with_ids:
              desc = describe_image_for_search(img, describe_fn=describe_fn)
              emb  = embed_text(desc, embed_fn=embed_fn)
              index.add(image_id, desc, emb, metadata or {})
          return index

      # Usage
      from PIL import Image
      imgs = [
          ('img_001', Image.new('RGB', (64,64), 'red'),   {'category': 'red'}),
          ('img_002', Image.new('RGB', (64,64), 'blue'),  {'category': 'blue'}),
          ('img_003', Image.new('RGB', (64,64), 'green'), {'category': 'green'}),
      ]
      index = index_images(imgs, describe_fn=mock_describe, embed_fn=mock_embed)
      print(len(index))   # 3
    narration: >
      The loop is three lines: describe, embed, add. The simplicity is
      intentional. There is no batching logic, no progress bar, no retry —
      those would be appropriate additions for a production indexer over
      10,000 images but would obscure the core logic here. For a production
      indexer, you would add concurrent describe calls (using a thread pool
      since Ollama is I/O-bound) and progress tracking via tqdm. For the
      course, the sequential version is exactly right.

  - type: concept
    label: "Metadata"
    heading: "Why Store Metadata Alongside Embeddings"
    body: >
      The vector index only stores floats. The metadata dict stores anything
      else you need to show in search results.
    bullets:
      - "Common metadata: filename, capture date, category, photographer"
      - "Returned in every search result dict — no second lookup needed"
      - "Not embedded — metadata is not part of similarity calculation"
      - "Example: retrieve the S3 URL from metadata to show the image"
    narration: >
      Without metadata, a search result would only give you back the image_id
      and description — not enough to display or link to the actual image.
      Storing the filename or URL in metadata means search results are
      immediately actionable: you have everything you need to render the image
      in a UI without a second database lookup. The metadata is never used in
      the cosine similarity calculation — it is passenger data that travels
      with the indexed item.

  - type: exercise
    heading: "Exercise 3: index_images"
    prompt: >
      Implement index_images(images_with_ids, describe_fn=None, embed_fn=None)
      -> ImageIndex. Create an ImageIndex, then for each (image_id, img,
      metadata) in images_with_ids: call describe_image_for_search, then
      embed_text, then index.add. Return the populated index.
    hint: >
      index = ImageIndex(); for image_id, img, metadata in images_with_ids:
      desc = describe_image_for_search(img, describe_fn=describe_fn);
      emb = embed_text(desc, embed_fn=embed_fn);
      index.add(image_id, desc, emb, metadata or {}).
    narration: >
      index_images is the bridge between a file system full of images and a
      queryable vector index. Call it once on your collection, persist the
      index if needed, then serve search queries against it.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "index_images input: list of (image_id, img, metadata) tuples"
      - "Three-line loop body: describe → embed → add"
      - "Metadata stored alongside vector but excluded from similarity math"
      - "Production addition: concurrent describe calls (Ollama is I/O-bound)"
      - "index_images returns a ready-to-query ImageIndex"
    narration: >
      Indexing is complete. Next: querying the index by text and by image.
"""

_LESSON_04 = """\
day: "071"
lesson: 4
title: "Querying the Index"
slides:
  - type: title
    heading: "Querying the Index"
    subheading: "search_by_text and search_by_image"
    narration: >
      With an index built, there are two ways to search it: with text and
      with an image. This lesson implements both query paths. Both end with
      the same index.search call — they differ only in how the query vector
      is produced.

  - type: how_it_works
    label: "search_by_text"
    heading: "search_by_text: Text Query Path"
    body: >
      One step: embed the query text, then call index.search. The embedding
      model is the same model used at index time.
    narration: >
      search_by_text is intentionally thin. All the retrieval logic is in
      ImageIndex.search; all the embedding logic is in embed_text. search_by_text
      just connects them with the query string as input and the ranked result
      list as output. The n parameter is passed through to index.search so the
      caller controls how many results to return.

  - type: code
    label: "search_by_text"
    heading: "search_by_text Implementation"
    code: |
      def search_by_text(query, index, embed_fn=None, n=5):
          q_emb = embed_text(query, embed_fn=embed_fn)
          return index.search(q_emb, n=n)

      results = search_by_text('a red object', index, embed_fn=mock_embed, n=3)
      for r in results:
          print(r['id'], f"{r['score']:.3f}", r['description'][:40])
    narration: >
      search_by_text embeds the query with the same embed_fn used at index
      time. This is essential — if index time uses nomic-embed-text and query
      time uses a different model, the vectors would be in incompatible spaces
      and cosine similarity would be meaningless. The mock embed_fn is the
      same function passed to index_images, ensuring test results are
      consistent.

  - type: how_it_works
    label: "search_by_image"
    heading: "search_by_image: Image Query Path"
    body: >
      Two steps: describe the query image, then embed the description.
      After that, identical to search_by_text.
    bullets:
      - "Describe query image: describe_image_for_search(img, describe_fn)"
      - "Embed description: embed_text(desc, embed_fn)"
      - "Search: index.search(q_emb, n)"
      - "Result: images similar in content to the query image"
    narration: >
      search_by_image is the powerful form. A user can drag an image into a
      search box and get back visually similar images from the index — a
      reverse image search powered by the same vision LLM and embedding model
      used at index time. The function describes the query image into the same
      text space as the indexed descriptions, then the cosine search finds
      the closest descriptions. Two images of sunsets will get similar
      embeddings because their LLM descriptions share words like sunset,
      golden, horizon, orange sky.

  - type: code
    label: "search_by_image"
    heading: "search_by_image Implementation"
    code: |
      def search_by_image(img, index, describe_fn=None, embed_fn=None, n=5):
          desc  = describe_image_for_search(img, describe_fn=describe_fn)
          q_emb = embed_text(desc, embed_fn=embed_fn)
          return index.search(q_emb, n=n)

      query_img = Image.new('RGB', (64, 64), 'darkred')
      results = search_by_image(query_img, index,
                                describe_fn=mock_describe,
                                embed_fn=mock_embed, n=2)
      for r in results:
          print(r['id'], f"{r['score']:.3f}")
    narration: >
      The two-line body mirrors the description → embedding pipeline: describe
      the query image the same way indexed images were described, then embed
      that description the same way indexed descriptions were embedded. The
      result is a query vector in the same space as all indexed vectors, so
      cosine similarity finds genuinely similar images.

  - type: exercise
    heading: "Exercise 4: search_by_text + search_by_image"
    prompt: >
      Implement search_by_text(query, index, embed_fn=None, n=5) -> list[dict]:
      embed_text(query, embed_fn) then index.search(q_emb, n).
      Implement search_by_image(img, index, describe_fn=None, embed_fn=None,
      n=5) -> list[dict]: describe_image_for_search(img, describe_fn), then
      embed_text(desc, embed_fn), then index.search(q_emb, n).
      Both return list of dicts with id, description, score, metadata.
    hint: >
      search_by_text: q_emb = embed_text(query, embed_fn=embed_fn); return index.search(q_emb, n=n).
      search_by_image: desc = describe_image_for_search(img, describe_fn=describe_fn); q_emb = embed_text(desc, embed_fn=embed_fn); return index.search(q_emb, n=n).
    narration: >
      The two search functions are deliberately thin. They compose the
      building blocks built across the last three exercises, showing how the
      whole pipeline assembles from small tested pieces.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "search_by_text: embed query → index.search"
      - "search_by_image: describe query image → embed → index.search"
      - "Same embed_fn must be used at index time and query time"
      - "Result dicts: id, description, score (cosine sim), metadata"
      - "Reverse image search powered by LLM descriptions in shared embedding space"
    narration: >
      Both search paths work. The final lesson wraps everything into
      ImageSearchEngine — the class that holds state and provides a clean
      API for any application.
"""

_LESSON_05 = """\
day: "071"
lesson: 5
title: "ImageSearchEngine — Full Pipeline"
slides:
  - type: title
    heading: "ImageSearchEngine"
    subheading: "Full pipeline class — image to pixel to answer"
    narration: >
      Lessons 1-4 built and tested every component of Vision RAG. This lesson
      assembles them into ImageSearchEngine — a class that binds describe_fn
      and embed_fn at construction time and exposes add_image, add_batch,
      search, and search_by_image.

  - type: how_it_works
    label: "ImageSearchEngine"
    heading: "ImageSearchEngine Design"
    body: >
      Four public methods. The class holds its own ImageIndex. Both mock
      functions are bound at construction time.
    bullets:
      - "ImageSearchEngine(describe_fn=None, embed_fn=None)"
      - "add_image(image_id, img, metadata=None) -> str (returns description)"
      - "add_batch(images_with_ids) -> list[str] (returns descriptions)"
      - "search(query, n=5) -> list[dict]"
      - "search_by_image(img, n=5) -> list[dict]"
    narration: >
      The class pattern is the same as VisionAnalyzer on Day 67 and
      ImageExtractor on Day 69 and ImageGenerator on Day 70. The
      describe_fn and embed_fn are bound at construction time so the
      caller does not pass them on every method call. The internal ImageIndex
      is private — callers interact with the engine, not the index.

  - type: code
    label: "Implementation"
    heading: "ImageSearchEngine Implementation"
    code: |
      class ImageSearchEngine:
          def __init__(self, describe_fn=None, embed_fn=None):
              self._describe_fn = describe_fn
              self._embed_fn    = embed_fn
              self._index       = ImageIndex()

          def add_image(self, image_id, img, metadata=None):
              desc = describe_image_for_search(img,
                         describe_fn=self._describe_fn)
              emb  = embed_text(desc, embed_fn=self._embed_fn)
              self._index.add(image_id, desc, emb, metadata or {})
              return desc

          def add_batch(self, images_with_ids):
              return [self.add_image(iid, img, meta)
                      for iid, img, meta in images_with_ids]

          def search(self, query, n=5):
              return search_by_text(query, self._index,
                                    embed_fn=self._embed_fn, n=n)

          def search_by_image(self, img, n=5):
              return search_by_image(img, self._index,
                                     describe_fn=self._describe_fn,
                                     embed_fn=self._embed_fn, n=n)

          def __len__(self):
              return len(self._index)
    narration: >
      Each method delegates to the module-level function. add_image
      delegates to describe_image_for_search and embed_text. search
      delegates to search_by_text. search_by_image delegates to the
      module-level search_by_image. This avoids duplicating logic in the
      class: the class is a thin stateful wrapper over the tested functions.
      add_image returns the description so callers can verify or log what
      the vision LLM generated for each image.

  - type: code
    label: "Usage"
    heading: "Full Pipeline Usage"
    code: |
      import hashlib
      from PIL import Image
      from visual_search import ImageSearchEngine

      # Mocks
      def _desc(b64, p):
          h = int(hashlib.md5(b64.encode()).hexdigest()[:4], 16)
          return ['a red car', 'a blue sky', 'a green forest'][h % 3]
      def _emb(t):
          h = int(hashlib.md5(t.encode()).hexdigest()[:8], 16)
          return [((h >> (i*8)) & 0xff) / 128.0 - 1.0 for i in range(4)]

      engine = ImageSearchEngine(describe_fn=_desc, embed_fn=_emb)
      items = [
          ('img1', Image.new('RGB',(64,64),'red'),   {'cat':'transport'}),
          ('img2', Image.new('RGB',(64,64),'blue'),  {'cat':'nature'}),
          ('img3', Image.new('RGB',(64,64),'green'), {'cat':'nature'}),
      ]
      descs = engine.add_batch(items)
      print(len(engine))   # 3

      results = engine.search('car', n=2)
      print(results[0]['id'], results[0]['metadata']['cat'])
    narration: >
      The engine is now a single object that encapsulates the full Vision RAG
      pipeline. To swap from mocked testing to real production, change two
      lines: the constructor arguments. All routes, all business logic, all
      search result handling stays the same.

  - type: exercise
    heading: "Exercise 5: ImageSearchEngine Class"
    prompt: >
      Implement ImageSearchEngine:
      __init__(describe_fn=None, embed_fn=None): store both, create an ImageIndex.
      add_image(image_id, img, metadata=None) -> str: describe, embed, add to index, return description.
      add_batch(images_with_ids) -> list[str]: list comprehension over add_image.
      search(query, n=5) -> list[dict]: delegates to search_by_text with self._embed_fn.
      search_by_image(img, n=5) -> list[dict]: delegates to module search_by_image with both fns.
      __len__() -> int: return len(self._index).
    hint: >
      add_image: desc = describe_image_for_search(img, describe_fn=self._describe_fn);
      emb = embed_text(desc, embed_fn=self._embed_fn); self._index.add(...); return desc.
      search: return search_by_text(query, self._index, embed_fn=self._embed_fn, n=n).
    narration: >
      ImageSearchEngine is the Day 71 deliverable. It completes the Vision
      RAG arc that started with embedding theory on Day 11.

  - type: summary
    heading: "Lesson 5 Summary — Day 71 Complete"
    bullets:
      - "ImageSearchEngine: describe_fn + embed_fn bound at construction"
      - "add_image returns description — useful for logging and verification"
      - "add_batch = list comprehension over add_image"
      - "search delegates to search_by_text; search_by_image delegates to module fn"
      - "Tomorrow (Day 72): Speech-to-Text with openai-whisper (local package, free)"
    narration: >
      Day 71 is complete. You can now build a searchable image library with
      no manual tagging, powered by a local vision LLM and a local embedding
      model. Tomorrow is the audio half of multimodal: transcribing speech
      to text with the Whisper model running entirely on your local machine.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared helpers ────────────────────────────────────────────────────────────
_HELPER_SRC = """\
import base64, hashlib, io
import numpy as np
from PIL import Image

_SEARCH_PROMPT = (
    'Describe this image in detail for use in a semantic search index. '
    'Include: main subjects, colors, textures, setting, and visible text. '
    'Write one concise paragraph of 2-3 sentences.'
)

def image_to_base64(img, format='PNG'):
    buf = io.BytesIO()
    out = img
    if format.upper() in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
        out = img.convert('RGB')
    out.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode()

def cosine_similarity(a, b):
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)

class ImageIndex:
    def __init__(self):
        self._items = []
    def add(self, image_id, description, embedding, metadata=None):
        self._items.append({'id': image_id, 'description': description,
                            'embedding': np.array(embedding, dtype=np.float32),
                            'metadata': metadata or {}})
    def search(self, query_embedding, n=5):
        if not self._items:
            return []
        q = np.array(query_embedding, dtype=np.float32)
        scored = [(cosine_similarity(q, item['embedding']), item) for item in self._items]
        scored.sort(key=lambda x: -x[0])
        top = scored[:min(n, len(scored))]
        return [{'id': item['id'], 'description': item['description'],
                 'score': float(score), 'metadata': item['metadata']}
                for score, item in top]
    def __len__(self):
        return len(self._items)

def describe_image_for_search(img, describe_fn=None):
    img_b64 = image_to_base64(img)
    if describe_fn is not None:
        return describe_fn(img_b64, _SEARCH_PROMPT)
    import ollama
    resp = ollama.chat(model='llava',
                       messages=[{'role': 'user', 'content': _SEARCH_PROMPT, 'images': [img_b64]}])
    return resp['message']['content'].strip()

def embed_text(text, embed_fn=None):
    if embed_fn is not None:
        return embed_fn(text)
    import ollama
    resp = ollama.embeddings(model='nomic-embed-text', prompt=text)
    return resp['embedding']

def index_images(images_with_ids, describe_fn=None, embed_fn=None):
    index = ImageIndex()
    for image_id, img, metadata in images_with_ids:
        desc = describe_image_for_search(img, describe_fn=describe_fn)
        emb  = embed_text(desc, embed_fn=embed_fn)
        index.add(image_id, desc, emb, metadata or {})
    return index

def search_by_text(query, index, embed_fn=None, n=5):
    q_emb = embed_text(query, embed_fn=embed_fn)
    return index.search(q_emb, n=n)

def search_by_image(img, index, describe_fn=None, embed_fn=None, n=5):
    desc  = describe_image_for_search(img, describe_fn=describe_fn)
    q_emb = embed_text(desc, embed_fn=embed_fn)
    return index.search(q_emb, n=n)
"""

_MOCK_SRC = """\
def _mock_describe(img_b64, prompt):
    h = int(hashlib.md5(img_b64.encode()).hexdigest()[:4], 16)
    labels = ['a red apple on a table', 'a blue ocean wave',
              'a green forest path', 'a yellow sunflower field']
    return labels[h % len(labels)]

def _mock_embed(text):
    h = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    return [((h >> (i * 8)) & 0xff) / 128.0 - 1.0 for i in range(4)]
"""

# ── EXERCISE 1 — cosine_similarity + ImageIndex ───────────────────────────────
_EX1_GIVEN = "import numpy as np\n"

_EX1_STUB = """\
def cosine_similarity(a, b) -> float:
    \"\"\"Cosine similarity between two vectors.

    Returns 0.0 if either vector has zero norm.
    \"\"\"
    raise NotImplementedError


class ImageIndex:
    \"\"\"In-memory image search index using cosine similarity.\"\"\"

    def __init__(self) -> None:
        raise NotImplementedError

    def add(self, image_id: str, description: str, embedding,
            metadata=None) -> None:
        \"\"\"Add an image to the index.\"\"\"
        raise NotImplementedError

    def search(self, query_embedding, n: int = 5) -> list:
        \"\"\"Return top-n results sorted by cosine similarity (descending).

        Each result dict: {id, description, score, metadata}.
        \"\"\"
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
"""

_EX1_SOLUTION = """\
def cosine_similarity(a, b) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class ImageIndex:
    def __init__(self):
        self._items = []

    def add(self, image_id, description, embedding, metadata=None):
        self._items.append({
            'id':          image_id,
            'description': description,
            'embedding':   np.array(embedding, dtype=np.float32),
            'metadata':    metadata or {},
        })

    def search(self, query_embedding, n=5):
        if not self._items:
            return []
        q = np.array(query_embedding, dtype=np.float32)
        scored = [(cosine_similarity(q, item['embedding']), item)
                  for item in self._items]
        scored.sort(key=lambda x: -x[0])
        top = scored[:min(n, len(scored))]
        return [
            {'id':          item['id'],
             'description': item['description'],
             'score':       float(score),
             'metadata':    item['metadata']}
            for score, item in top
        ]

    def __len__(self):
        return len(self._items)
"""

_EX1_CHECKS = """\
score, total = 0, 5
try:
    # cosine_similarity: identical vectors = 1.0
    sim = cosine_similarity([1, 0, 0], [1, 0, 0])
    assert abs(sim - 1.0) < 1e-5, f"Expected 1.0, got {sim}"
    score += 1; print("\\u2705 cosine_similarity: identical vectors = 1.0")

    # cosine_similarity: orthogonal = 0.0
    sim2 = cosine_similarity([1, 0], [0, 1])
    assert abs(sim2) < 1e-5, f"Expected 0.0, got {sim2}"
    score += 1; print("\\u2705 cosine_similarity: orthogonal vectors = 0.0")

    # cosine_similarity: zero vector → 0.0
    sim3 = cosine_similarity([0, 0, 0], [1, 2, 3])
    assert sim3 == 0.0
    score += 1; print("\\u2705 cosine_similarity: zero vector returns 0.0")

    # ImageIndex: add and len
    idx = ImageIndex()
    idx.add('a', 'red car', [1.0, 0.0], {'tag': 'car'})
    idx.add('b', 'blue sky', [0.0, 1.0], {'tag': 'sky'})
    assert len(idx) == 2
    score += 1; print("\\u2705 ImageIndex: add + __len__")

    # search: sorted by score desc, correct keys
    results = idx.search([1.0, 0.0], n=2)
    assert len(results) == 2
    assert results[0]['id'] == 'a', f"Expected 'a', got {results[0]['id']}"
    assert results[0]['score'] > results[1]['score']
    assert 'description' in results[0] and 'metadata' in results[0]
    score += 1; print("\\u2705 search: sorted descending, correct keys")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 071 — Exercise 1: cosine_similarity + ImageIndex\n\n"
       "**What you'll build:** The retrieval core of Vision RAG — "
       "`cosine_similarity` and `ImageIndex` with `add`, `search`, and `__len__`.\n\n"
       "**Why it matters:** Everything else in Vision RAG feeds data into these "
       "two pieces. Getting them right means the search results are correct."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "**`cosine_similarity(a, b) -> float`:**\n"
       "- Convert both to `np.float32` arrays\n"
       "- `denom = np.linalg.norm(va) * np.linalg.norm(vb)`\n"
       "- Return `0.0` if `denom == 0.0`, else `float(np.dot(va, vb) / denom)`\n\n"
       "**`ImageIndex`:**\n"
       "- `__init__`: `self._items = []`\n"
       "- `add`: append `{id, description, embedding (as np.float32 array), metadata}`\n"
       "- `search`: score all items with `cosine_similarity`, sort descending, "
       "return top-n as dicts with keys `id, description, score, metadata` (no embedding)\n"
       "- `__len__`: return `len(self._items)`"),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why `np.float32` not `float64`?** float32 halves memory usage with "
       "negligible precision loss for cosine similarity. Embedding models "
       "typically output float32.\n\n"
       "**Why exclude `embedding` from results?** A 768-dim embedding is "
       "~3 KB per result — 10 results would add 30 KB to every search response. "
       "Callers never need the raw embedding back.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EXERCISE 2 — describe_image_for_search + embed_text ──────────────────────
_EX2_GIVEN = _HELPER_SRC.split("def describe_image_for_search")[0]  # up to cosine+ImageIndex
_EX2_GIVEN += "\nimport hashlib\n" + _MOCK_SRC

_EX2_STUB = """\
_SEARCH_PROMPT = (
    'Describe this image in detail for use in a semantic search index. '
    'Include: main subjects, colors, textures, setting, and visible text. '
    'Write one concise paragraph of 2-3 sentences.'
)


def describe_image_for_search(img, describe_fn=None) -> str:
    \"\"\"Generate a text description of an image for search indexing.

    Args:
        img:         PIL Image
        describe_fn: callable(img_b64, prompt) -> str for testing
    Returns:
        Text description string
    \"\"\"
    raise NotImplementedError


def embed_text(text, embed_fn=None) -> list:
    \"\"\"Embed text to a float vector.

    Args:
        text:     Input string
        embed_fn: callable(text) -> list[float] for testing
    Returns:
        list of float
    \"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
_SEARCH_PROMPT = (
    'Describe this image in detail for use in a semantic search index. '
    'Include: main subjects, colors, textures, setting, and visible text. '
    'Write one concise paragraph of 2-3 sentences.'
)


def describe_image_for_search(img, describe_fn=None):
    img_b64 = image_to_base64(img)
    if describe_fn is not None:
        return describe_fn(img_b64, _SEARCH_PROMPT)
    import ollama
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': _SEARCH_PROMPT, 'images': [img_b64]}],
    )
    return resp['message']['content'].strip()


def embed_text(text, embed_fn=None):
    if embed_fn is not None:
        return embed_fn(text)
    import ollama
    resp = ollama.embeddings(model='nomic-embed-text', prompt=text)
    return resp['embedding']
"""

_EX2_CHECKS = """\
score, total = 0, 5
try:
    img = Image.new('RGB', (32, 32), 'tomato')

    # describe returns a string
    desc = describe_image_for_search(img, describe_fn=_mock_describe)
    assert isinstance(desc, str) and len(desc) > 0
    score += 1; print("\\u2705 describe_image_for_search returns non-empty string")

    # describe_fn receives img_b64 (str) and prompt
    received = {}
    def _capture_desc(b64, prompt):
        received['b64']    = b64
        received['prompt'] = prompt
        return 'captured description'
    describe_image_for_search(img, describe_fn=_capture_desc)
    assert isinstance(received.get('b64'), str) and len(received['b64']) > 10
    assert received.get('prompt') == _SEARCH_PROMPT
    score += 1; print("\\u2705 describe_fn receives base64 string and correct prompt")

    # embed_text returns a list of floats
    emb = embed_text('a red car', embed_fn=_mock_embed)
    assert isinstance(emb, list) and len(emb) > 0
    assert all(isinstance(v, float) for v in emb)
    score += 1; print("\\u2705 embed_text returns list of floats")

    # embed_fn receives the text string
    received2 = {}
    def _capture_emb(text):
        received2['text'] = text
        return [0.1, 0.2]
    embed_text('hello world', embed_fn=_capture_emb)
    assert received2.get('text') == 'hello world'
    score += 1; print("\\u2705 embed_fn receives the input text")

    # same text → same embedding (deterministic mock)
    emb1 = embed_text('a sunny beach', embed_fn=_mock_embed)
    emb2 = embed_text('a sunny beach', embed_fn=_mock_embed)
    assert emb1 == emb2
    score += 1; print("\\u2705 embed_text is deterministic for same input")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 071 — Exercise 2: describe_image_for_search + embed_text\n\n"
       "**What you'll build:** The two data transformation functions that "
       "convert a PIL Image into a float vector ready for the index.\n\n"
       "**Why it matters:** The quality of search results depends on the "
       "richness of the description and the alignment of the embedding space. "
       "These two functions are where that quality is determined."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "**`describe_image_for_search(img, describe_fn=None) -> str`:**\n"
       "1. `img_b64 = image_to_base64(img)`\n"
       "2. If `describe_fn is not None`: `return describe_fn(img_b64, _SEARCH_PROMPT)`\n"
       "3. Else: `ollama.chat(model='llava', messages=[{role, content: _SEARCH_PROMPT, images: [img_b64]}])` "
       "→ return `resp['message']['content'].strip()`\n\n"
       "**`embed_text(text, embed_fn=None) -> list[float]`:**\n"
       "1. If `embed_fn is not None`: `return embed_fn(text)`\n"
       "2. Else: `ollama.embeddings(model='nomic-embed-text', prompt=text)` → return `resp['embedding']`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why `.strip()` on the description?** LLMs sometimes prepend or "
       "append whitespace or newlines. Stripping keeps the stored descriptions "
       "clean and avoids spurious differences in the embedding space.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EXERCISE 3 — index_images ─────────────────────────────────────────────────
_EX3_GIVEN = _HELPER_SRC + "\nimport hashlib\n" + _MOCK_SRC

_EX3_STUB = """\
def index_images(images_with_ids: list,
                 describe_fn=None,
                 embed_fn=None) -> ImageIndex:
    \"\"\"Describe, embed, and index a batch of images.

    Args:
        images_with_ids: list of (image_id, img, metadata) tuples
        describe_fn:     callable(img_b64, prompt) -> str for testing
        embed_fn:        callable(text) -> list[float] for testing
    Returns:
        Populated ImageIndex
    \"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def index_images(images_with_ids, describe_fn=None, embed_fn=None):
    index = ImageIndex()
    for image_id, img, metadata in images_with_ids:
        desc = describe_image_for_search(img, describe_fn=describe_fn)
        emb  = embed_text(desc, embed_fn=embed_fn)
        index.add(image_id, desc, emb, metadata or {})
    return index
"""

_EX3_CHECKS = """\
score, total = 0, 5
try:
    imgs = [
        ('img_r', Image.new('RGB', (16,16), (220, 50, 50)), {'tag': 'red'}),
        ('img_b', Image.new('RGB', (16,16), (50, 100, 220)), {'tag': 'blue'}),
        ('img_g', Image.new('RGB', (16,16), (50, 180, 80)), {'tag': 'green'}),
    ]

    idx = index_images(imgs, describe_fn=_mock_describe, embed_fn=_mock_embed)

    # returns ImageIndex with 3 items
    assert isinstance(idx, ImageIndex)
    assert len(idx) == 3
    score += 1; print("\\u2705 index_images returns ImageIndex with correct item count")

    # search returns dicts with expected keys
    results = idx.search([0.5, 0.5, -0.5, -0.5], n=3)
    assert len(results) == 3
    assert all('id' in r and 'description' in r and 'score' in r and 'metadata' in r
               for r in results)
    score += 1; print("\\u2705 indexed items have all required keys")

    # descriptions are non-empty strings
    assert all(isinstance(r['description'], str) and len(r['description']) > 0
               for r in results)
    score += 1; print("\\u2705 all descriptions are non-empty strings")

    # metadata is preserved correctly
    ids_in_results = {r['id'] for r in results}
    assert ids_in_results == {'img_r', 'img_b', 'img_g'}
    tags = {r['id']: r['metadata'].get('tag') for r in results}
    assert tags['img_r'] == 'red' and tags['img_b'] == 'blue'
    score += 1; print("\\u2705 metadata preserved per image_id")

    # results sorted descending by score
    scores = [r['score'] for r in results]
    assert scores == sorted(scores, reverse=True), f"Not sorted: {scores}"
    score += 1; print("\\u2705 results sorted by score descending")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 071 — Exercise 3: index_images\n\n"
       "**What you'll build:** `index_images(images_with_ids, describe_fn, embed_fn) -> ImageIndex` — "
       "the batch pipeline that describes and embeds a collection of images.\n\n"
       "**Why it matters:** This is the offline indexing step. Run it once on "
       "your image collection; then search it instantly any number of times."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "Implement `index_images`:\n\n"
       "1. Create `index = ImageIndex()`\n"
       "2. `for image_id, img, metadata in images_with_ids:`\n"
       "   - `desc = describe_image_for_search(img, describe_fn=describe_fn)`\n"
       "   - `emb = embed_text(desc, embed_fn=embed_fn)`\n"
       "   - `index.add(image_id, desc, emb, metadata or {})`\n"
       "3. Return `index`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why `metadata or {}`?** If the caller passes `None` as metadata "
       "(or omits it), storing `None` in the index would cause `KeyError` "
       "when result dicts are built. The `or {}` guard makes the index "
       "robust to caller mistakes.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EXERCISE 4 — search_by_text + search_by_image ────────────────────────────
_EX4_GIVEN = _HELPER_SRC + "\nimport hashlib\n" + _MOCK_SRC + """\

# Pre-built index for checks
_imgs = [
    ('img_r', Image.new('RGB', (16,16), (220, 50, 50)), {'tag': 'red'}),
    ('img_b', Image.new('RGB', (16,16), (50, 100, 220)), {'tag': 'blue'}),
    ('img_g', Image.new('RGB', (16,16), (50, 180, 80)), {'tag': 'green'}),
]
_index = index_images(_imgs, describe_fn=_mock_describe, embed_fn=_mock_embed)
"""

_EX4_STUB = """\
def search_by_text(query: str, index: ImageIndex,
                   embed_fn=None, n: int = 5) -> list:
    \"\"\"Search the index by a text query.

    Embeds the query, then returns top-n results from index.search.
    \"\"\"
    raise NotImplementedError


def search_by_image(img, index: ImageIndex,
                    describe_fn=None, embed_fn=None, n: int = 5) -> list:
    \"\"\"Search the index using an image as the query.

    Describes the query image, embeds the description, returns top-n results.
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = """\
def search_by_text(query, index, embed_fn=None, n=5):
    q_emb = embed_text(query, embed_fn=embed_fn)
    return index.search(q_emb, n=n)


def search_by_image(img, index, describe_fn=None, embed_fn=None, n=5):
    desc  = describe_image_for_search(img, describe_fn=describe_fn)
    q_emb = embed_text(desc, embed_fn=embed_fn)
    return index.search(q_emb, n=n)
"""

_EX4_CHECKS = """\
score, total = 0, 5
try:
    # search_by_text returns a list
    results = search_by_text('a red object', _index, embed_fn=_mock_embed, n=3)
    assert isinstance(results, list)
    score += 1; print("\\u2705 search_by_text returns a list")

    # n=3 returns at most 3 results
    assert len(results) <= 3
    score += 1; print("\\u2705 search_by_text respects n limit")

    # each result has required keys
    assert all('id' in r and 'score' in r and 'description' in r and 'metadata' in r
               for r in results)
    score += 1; print("\\u2705 search_by_text results have all required keys")

    # search_by_image returns a list with correct keys
    query_img = Image.new('RGB', (16, 16), (200, 80, 80))
    img_results = search_by_image(query_img, _index,
                                  describe_fn=_mock_describe,
                                  embed_fn=_mock_embed, n=2)
    assert isinstance(img_results, list) and len(img_results) <= 2
    assert all('id' in r and 'score' in r for r in img_results)
    score += 1; print("\\u2705 search_by_image returns correct result list")

    # results sorted descending by score
    if len(results) >= 2:
        assert results[0]['score'] >= results[1]['score']
    score += 1; print("\\u2705 results sorted by score descending")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 071 — Exercise 4: search_by_text + search_by_image\n\n"
       "**What you'll build:** The two query functions for Vision RAG — text "
       "search and reverse image search.\n\n"
       "**Why it matters:** These are the two user-facing interfaces. A product "
       "search feature might expose both: type a query or upload a photo to "
       "find similar items."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "**`search_by_text(query, index, embed_fn=None, n=5) -> list[dict]`:**\n"
       "- `q_emb = embed_text(query, embed_fn=embed_fn)`\n"
       "- `return index.search(q_emb, n=n)`\n\n"
       "**`search_by_image(img, index, describe_fn=None, embed_fn=None, n=5) -> list[dict]`:**\n"
       "- `desc = describe_image_for_search(img, describe_fn=describe_fn)`\n"
       "- `q_emb = embed_text(desc, embed_fn=embed_fn)`\n"
       "- `return index.search(q_emb, n=n)`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why are both functions so short?** All the logic is in the "
       "components they compose. Short functions that do one thing and "
       "compose other tested functions are easier to debug than long functions "
       "with mixed concerns.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EXERCISE 5 — ImageSearchEngine ───────────────────────────────────────────
_EX5_GIVEN = _HELPER_SRC + "\nimport hashlib\n" + _MOCK_SRC

_EX5_STUB = """\
class ImageSearchEngine:
    \"\"\"Content-based image search engine.

    Inject describe_fn and embed_fn for testing without Ollama.
    \"\"\"

    def __init__(self, describe_fn=None, embed_fn=None) -> None:
        raise NotImplementedError

    def add_image(self, image_id: str, img, metadata=None) -> str:
        \"\"\"Index one image. Returns the generated description.\"\"\"
        raise NotImplementedError

    def add_batch(self, images_with_ids: list) -> list:
        \"\"\"Index a batch of (image_id, img, metadata) tuples.

        Returns list of generated description strings.
        \"\"\"
        raise NotImplementedError

    def search(self, query: str, n: int = 5) -> list:
        \"\"\"Search by text query. Returns list of result dicts.\"\"\"
        raise NotImplementedError

    def search_by_image(self, img, n: int = 5) -> list:
        \"\"\"Search by image query. Returns list of result dicts.\"\"\"
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class ImageSearchEngine:
    def __init__(self, describe_fn=None, embed_fn=None):
        self._describe_fn = describe_fn
        self._embed_fn    = embed_fn
        self._index       = ImageIndex()

    def add_image(self, image_id, img, metadata=None):
        desc = describe_image_for_search(img, describe_fn=self._describe_fn)
        emb  = embed_text(desc, embed_fn=self._embed_fn)
        self._index.add(image_id, desc, emb, metadata or {})
        return desc

    def add_batch(self, images_with_ids):
        return [self.add_image(iid, img, meta)
                for iid, img, meta in images_with_ids]

    def search(self, query, n=5):
        return search_by_text(query, self._index,
                              embed_fn=self._embed_fn, n=n)

    def search_by_image(self, img, n=5):
        return search_by_image(img, self._index,
                               describe_fn=self._describe_fn,
                               embed_fn=self._embed_fn, n=n)

    def __len__(self):
        return len(self._index)
"""

_EX5_CHECKS = """\
score, total = 0, 5
try:
    engine = ImageSearchEngine(describe_fn=_mock_describe, embed_fn=_mock_embed)
    assert len(engine) == 0
    score += 1; print("\\u2705 empty engine has len 0")

    # add_image returns a description string
    img = Image.new('RGB', (16, 16), (220, 50, 50))
    desc = engine.add_image('img1', img, {'tag': 'red'})
    assert isinstance(desc, str) and len(desc) > 0
    assert len(engine) == 1
    score += 1; print("\\u2705 add_image returns description, __len__ increments")

    # add_batch indexes multiple images
    batch = [
        ('img2', Image.new('RGB', (16,16), (50, 100, 220)), {'tag': 'blue'}),
        ('img3', Image.new('RGB', (16,16), (50, 180, 80)),  {'tag': 'green'}),
    ]
    descs = engine.add_batch(batch)
    assert len(descs) == 2 and all(isinstance(d, str) for d in descs)
    assert len(engine) == 3
    score += 1; print("\\u2705 add_batch adds all items, returns descriptions")

    # search returns sorted results with correct keys
    results = engine.search('a red object', n=2)
    assert len(results) <= 2
    assert all('id' in r and 'score' in r and 'metadata' in r for r in results)
    if len(results) >= 2:
        assert results[0]['score'] >= results[1]['score']
    score += 1; print("\\u2705 search returns sorted results with correct keys")

    # search_by_image returns results
    q_img = Image.new('RGB', (16, 16), (200, 100, 100))
    img_results = engine.search_by_image(q_img, n=2)
    assert isinstance(img_results, list) and len(img_results) <= 2
    score += 1; print("\\u2705 search_by_image returns list of result dicts")

except Exception as e:
    print(f"\\u274c {e}")

print(f"\\n{score}/{total} checks passed")
if score == total:
    print("\\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 071 — Exercise 5: ImageSearchEngine\n\n"
       "**What you'll build:** `ImageSearchEngine` — the complete Vision RAG "
       "pipeline as a single reusable class.\n\n"
       "**Why it matters:** The class is the deliverable that a developer "
       "drops into any app. One constructor call to configure, then "
       "`.add_image` to index and `.search` to query."),
    code(_EX5_GIVEN),
    md("## Task\n\nImplement `ImageSearchEngine`:\n\n"
       "- `__init__(describe_fn=None, embed_fn=None)`: store both, `self._index = ImageIndex()`\n"
       "- `add_image(image_id, img, metadata=None) -> str`: describe → embed → add to index → return desc\n"
       "- `add_batch(images_with_ids) -> list[str]`: `[self.add_image(iid, img, meta) for ...]`\n"
       "- `search(query, n=5) -> list[dict]`: `search_by_text(query, self._index, embed_fn=self._embed_fn, n=n)`\n"
       "- `search_by_image(img, n=5) -> list[dict]`: module-level `search_by_image` with both fns\n"
       "- `__len__() -> int`: `len(self._index)`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why does `search_by_image` call the module-level function "
       "rather than being re-implemented?** The module-level function is "
       "already tested. Calling it avoids duplicate logic. The class method "
       "only adds the `self._describe_fn` and `self._embed_fn` arguments — "
       "that's the entire reason the class method exists.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md("# Day 071 — Project: Visual Search Engine\n\n"
       "## What You're Building\n\n"
       "`visual_search.py` — an `ImageSearchEngine` for content-based image retrieval.\n\n"
       "**Deliverable:** A class and utility functions that describe images with a vision LLM, "
       "embed descriptions with a text model, and return ranked search results for text or image queries.\n\n"
       "## Setup (for real usage)\n\n"
       "```bash\n"
       "ollama pull llava             # vision model\n"
       "ollama pull nomic-embed-text  # embedding model\n"
       "```\n\n"
       "## Design\n\n"
       "```\n"
       "cosine_similarity(a, b) -> float\n"
       "ImageIndex.add / .search / __len__\n"
       "describe_image_for_search(img, describe_fn=None) -> str\n"
       "embed_text(text, embed_fn=None) -> list[float]\n"
       "index_images(images_with_ids, describe_fn, embed_fn) -> ImageIndex\n"
       "search_by_text(query, index, embed_fn, n) -> list[dict]\n"
       "search_by_image(img, index, describe_fn, embed_fn, n) -> list[dict]\n"
       "ImageSearchEngine(describe_fn, embed_fn)\n"
       "  .add_image / .add_batch / .search / .search_by_image / __len__\n"
       "```"),
    code("# Your implementation here — build ImageSearchEngine and write visual_search.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SEARCH_SRC = {repr(_SEARCH_SRC)}\n"
    "from pathlib import Path\n"
    "Path('visual_search.py').write_text(_SEARCH_SRC, encoding='utf-8')\n"
    "print('visual_search.py written.')"
)

_SOL_CELL2 = """\
import hashlib
from PIL import Image
from visual_search import (
    cosine_similarity, ImageIndex,
    describe_image_for_search, embed_text,
    index_images, search_by_text, search_by_image,
    ImageSearchEngine,
)

def _mock_desc(b64, p):
    h = int(hashlib.md5(b64.encode()).hexdigest()[:4], 16)
    return ['a red apple', 'a blue ocean', 'a green forest'][h % 3]

def _mock_emb(t):
    h = int(hashlib.md5(t.encode()).hexdigest()[:8], 16)
    return [((h >> (i*8)) & 0xff) / 128.0 - 1.0 for i in range(4)]

# 1. cosine_similarity
assert abs(cosine_similarity([1,0], [1,0]) - 1.0) < 1e-5
assert abs(cosine_similarity([1,0], [0,1]))       < 1e-5
assert cosine_similarity([0,0], [1,2]) == 0.0
print("\\u2705 cosine_similarity correct")

# 2. ImageIndex
idx = ImageIndex()
idx.add('a', 'red car', [1.0, 0.0])
idx.add('b', 'blue sky', [0.0, 1.0])
assert len(idx) == 2
results = idx.search([1.0, 0.0], n=2)
assert results[0]['id'] == 'a' and results[0]['score'] > results[1]['score']
print("\\u2705 ImageIndex correct")

# 3. describe_image_for_search
img = Image.new('RGB', (16,16), 'red')
desc = describe_image_for_search(img, describe_fn=_mock_desc)
assert isinstance(desc, str) and len(desc) > 0
print("\\u2705 describe_image_for_search correct")

# 4. embed_text
emb = embed_text('a red car', embed_fn=_mock_emb)
assert isinstance(emb, list) and len(emb) == 4
print("\\u2705 embed_text correct")

# 5. index_images
imgs = [('i1', Image.new('RGB',(16,16),(220,50,50)), {'tag':'red'}),
        ('i2', Image.new('RGB',(16,16),(50,100,220)), {'tag':'blue'})]
built_idx = index_images(imgs, describe_fn=_mock_desc, embed_fn=_mock_emb)
assert len(built_idx) == 2
print("\\u2705 index_images correct")

# 6. search_by_text
r = search_by_text('apple', built_idx, embed_fn=_mock_emb, n=2)
assert len(r) <= 2 and all('score' in x for x in r)
print("\\u2705 search_by_text correct")

# 7. search_by_image
q = Image.new('RGB', (16,16), 'blue')
r2 = search_by_image(q, built_idx, describe_fn=_mock_desc, embed_fn=_mock_emb, n=1)
assert len(r2) == 1 and 'id' in r2[0]
print("\\u2705 search_by_image correct")

# 8. ImageSearchEngine
engine = ImageSearchEngine(describe_fn=_mock_desc, embed_fn=_mock_emb)
for iid, img_x, meta in imgs:
    engine.add_image(iid, img_x, meta)
assert len(engine) == 2
sr = engine.search('blue ocean', n=1)
assert len(sr) == 1 and sr[0]['score'] >= -1.0
print("\\u2705 ImageSearchEngine correct")

print("\\nVisual Search Engine complete!")
"""

SOLUTION = nb([
    md("# Day 071 — Solution: Visual Search Engine"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "visual_search.py").write_text(_SEARCH_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_071_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + visual_search.py")
