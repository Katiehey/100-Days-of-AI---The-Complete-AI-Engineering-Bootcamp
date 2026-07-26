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
