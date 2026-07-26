"""test_shipped_app.py — pytest test suite for shipped_app.

Run:
  pytest test_shipped_app.py -v
  pytest test_shipped_app.py -v -k generate
"""
import pytest
from starlette.testclient import TestClient
from shipped_app import build_api


@pytest.fixture
def client():
    return TestClient(build_api(plan="free", process_fn=str.upper),
                      raise_server_exceptions=False)


@pytest.fixture
def pro_client():
    return TestClient(build_api(plan="pro", process_fn=str.upper),
                      raise_server_exceptions=False)


@pytest.fixture
def at_limit_client():
    return TestClient(
        build_api(plan="free", process_fn=str.upper, initial_usage=5),
        raise_server_exceptions=False,
    )


# ── infrastructure ─────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert "timestamp" in d and "version" in d


def test_plan(client):
    r = client.get("/plan")
    assert r.status_code == 200
    d = r.json()
    assert d["plan"] == "free"
    assert d["usage_today"] == 0
    assert d["limit"] == 5


def test_templates(client):
    r = client.get("/templates")
    assert r.status_code == 200
    assert isinstance(r.json()["templates"], list)
    assert len(r.json()["templates"]) > 0


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    d = r.json()
    for key in ("requests", "errors", "avg_latency_ms", "error_rate"):
        assert key in d, f"Missing key: {key}"


# ── generation ─────────────────────────────────────────────────────────────────

def test_generate_ok(client):
    r = client.post("/generate", json={"prompt": "hello", "user_id": "u1"})
    assert r.status_code == 200
    d = r.json()
    assert "content_id" in d
    assert d["content"] == "HELLO"
    assert d["user_id"] == "u1"


@pytest.mark.parametrize("body,expected", [
    ({"prompt": "", "user_id": "u1"}, 422),    # empty prompt
    ({"prompt": "hi"}, 422),                   # missing user_id
    ({}, 422),                                  # empty body
])
def test_generate_validation(client, body, expected):
    r = client.post("/generate", json=body)
    assert r.status_code == expected, f"got {r.status_code}: {r.text[:120]}"


def test_generate_rate_limit(at_limit_client):
    r = at_limit_client.post("/generate",
                             json={"prompt": "hi", "user_id": "u1"})
    assert r.status_code == 429


def test_generate_usage_increments(client):
    client.post("/generate", json={"prompt": "a", "user_id": "u1"})
    client.post("/generate", json={"prompt": "b", "user_id": "u1"})
    r = client.get("/plan")
    assert r.json()["usage_today"] == 2


# ── history ────────────────────────────────────────────────────────────────────

def test_history_empty(client):
    r = client.get("/history/nobody")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_history_after_generate(client):
    client.post("/generate", json={"prompt": "x", "user_id": "alice"})
    client.post("/generate", json={"prompt": "y", "user_id": "alice"})
    client.post("/generate", json={"prompt": "z", "user_id": "bob"})
    r = client.get("/history/alice")
    assert r.json()["count"] == 2
    assert all(i["user_id"] == "alice" for i in r.json()["items"])


def test_content_get(client):
    rg  = client.post("/generate", json={"prompt": "hi", "user_id": "u"})
    cid = rg.json()["content_id"]
    rc  = client.get(f"/content/{cid}")
    assert rc.status_code == 200
    assert rc.json()["content_id"] == cid


def test_content_not_found(client):
    assert client.get("/content/does_not_exist").status_code == 404


# ── feature gating ─────────────────────────────────────────────────────────────

def test_improve_requires_pro(client):
    r = client.post("/improve", json={"text": "hello", "user_id": "u1"})
    assert r.status_code == 403


def test_improve_works_for_pro(pro_client):
    r = pro_client.post("/improve", json={"text": "hello", "user_id": "u1"})
    assert r.status_code == 200
    assert "improved" in r.json()


# ── state isolation ────────────────────────────────────────────────────────────

def test_isolation_between_clients():
    c1 = TestClient(build_api(plan="free", process_fn=str.upper),
                    raise_server_exceptions=False)
    c2 = TestClient(build_api(plan="free", process_fn=str.upper),
                    raise_server_exceptions=False)
    c1.post("/generate", json={"prompt": "a", "user_id": "u"})
    assert c2.get("/history/u").json()["count"] == 0
