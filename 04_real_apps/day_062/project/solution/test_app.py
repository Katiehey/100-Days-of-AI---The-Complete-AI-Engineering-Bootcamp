"""test_app.py — Day 062: pytest test suite for a simple CRUD API.

Run:  pytest test_app.py -v
      pytest test_app.py -v -k "delete"   # filter by name
      pytest test_app.py --tb=short        # compact tracebacks
"""
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.testclient import TestClient


# ── app under test ─────────────────────────────────────────────────────────────
class Item(BaseModel):
    name:  str   = Field(min_length=1)
    price: float = Field(gt=0)


def build_app() -> FastAPI:
    """Simple item CRUD API — the subject under test."""
    app  = FastAPI()
    _db  = {}
    _nxt = {"id": 1}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/items")
    def list_items():
        return {"items": list(_db.values())}

    @app.post("/items", status_code=201)
    def create_item(item: Item):
        iid         = _nxt["id"]
        _nxt["id"] += 1
        _db[iid]    = {"id": iid, **item.model_dump()}
        return _db[iid]

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        if item_id not in _db:
            raise HTTPException(status_code=404, detail="Not found")
        return _db[item_id]

    @app.delete("/items/{item_id}", status_code=204)
    def delete_item(item_id: int):
        if item_id not in _db:
            raise HTTPException(status_code=404, detail="Not found")
        del _db[item_id]

    return app


# ── pytest fixture ─────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    """Fresh TestClient (and fresh app state) for every test."""
    return TestClient(build_app())


# ── health tests ───────────────────────────────────────────────────────────────
def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_health_status_is_ok(client):
    r = client.get("/health")
    assert r.json()["status"] == "ok"


# ── list tests ─────────────────────────────────────────────────────────────────
def test_list_items_empty_on_start(client):
    r = client.get("/items")
    assert r.status_code == 200
    assert r.json()["items"] == []


# ── create tests ───────────────────────────────────────────────────────────────
def test_create_item_returns_201(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert r.status_code == 201


def test_create_item_has_id(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert "id" in r.json()


def test_create_item_preserves_fields(client):
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    data = r.json()
    assert data["name"]  == "Widget"
    assert data["price"] == 9.99


@pytest.mark.parametrize("name,price,expected_status", [
    ("Widget", 9.99,  201),   # valid
    ("",       9.99,  422),   # empty name
    ("Widget", 0.0,   422),   # price must be > 0
    ("Widget", -1.0,  422),   # negative price
])
def test_create_item_validation(client, name, price, expected_status):
    r = client.post("/items", json={"name": name, "price": price})
    assert r.status_code == expected_status, (
        f"name={name!r}, price={price}: expected {expected_status}, got {r.status_code}")


# ── get tests ──────────────────────────────────────────────────────────────────
def test_get_item_after_create(client):
    created = client.post("/items", json={"name": "Gadget", "price": 14.99}).json()
    r = client.get(f"/items/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Gadget"


def test_get_item_not_found(client):
    r = client.get("/items/999")
    assert r.status_code == 404


# ── delete tests ───────────────────────────────────────────────────────────────
def test_delete_item_returns_204(client):
    created = client.post("/items", json={"name": "Thing", "price": 1.0}).json()
    r = client.delete(f"/items/{created['id']}")
    assert r.status_code == 204


def test_deleted_item_is_gone(client):
    created = client.post("/items", json={"name": "Thing", "price": 1.0}).json()
    client.delete(f"/items/{created['id']}")
    r = client.get(f"/items/{created['id']}")
    assert r.status_code == 404


def test_delete_item_not_found(client):
    r = client.delete("/items/999")
    assert r.status_code == 404
