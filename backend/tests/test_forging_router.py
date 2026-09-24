# NOTICE: This file is protected under RCF-PL
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.config import settings
from app.database import get_db
from app.main import app
from app.routers import forging as forging_router
from app.security import get_current_user

@pytest.fixture
def forging_client(monkeypatch):
    async def fake_db():
        yield object()
    async def fake_user():
        return SimpleNamespace(id=42)
    async def fake_mongo(db, user_id):
        return object()
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr(forging_router, "_mongo", fake_mongo)
    monkeypatch.setattr(forging_router, "_require_edition", lambda: None)
    try:
        yield TestClient(app, raise_server_exceptions=True), forging_router
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

def test_freeze_forwards_custom_ratios(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_freeze(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return {
            "version": 3, "frozen": 10,
            "counts": {"train": 7, "validation": 2, "heldout": 1},
            "status": "ready", "frozen_at": datetime.now(timezone.utc),
            "min_reward": 0.6, "human_only": True, "replaced": False, "warnings": []
        }
    monkeypatch.setattr(router_mod, "freeze_golden_set", fake_freeze)
    ratios = {"train": 0.8, "validation": 0.1, "heldout": 0.1}
    resp = client.post("/api/forging/golden-set", json={"min_reward": 0.6, "human_only": True, "limit": 100, "ratios": ratios})
    assert resp.status_code == 200
    assert captured["ratios"] == ratios

def test_freeze_invalid_ratios_returns_422(forging_client, monkeypatch):
    client, router_mod = forging_client
    async def fake_freeze(mdb, user_id, **kwargs):
        raise ValueError("Invalid split ratios")
    monkeypatch.setattr(router_mod, "freeze_golden_set", fake_freeze)
    resp = client.post("/api/forging/golden-set", json={"ratios": {"train": 0.5, "validation": 0.1, "heldout": 0.1}})
    assert resp.status_code == 422

def test_list_golden_defaults_to_latest(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_get(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return [{"_id": "mongo-1", "input": "hi", "expected": "hello", "split": "train"}]
    monkeypatch.setattr(router_mod, "get_golden_set", fake_get)
    resp = client.get("/api/forging/golden-set")
    assert resp.status_code == 200
    assert captured.get("version") is None
    assert captured.get("split") is None
    assert "_id" not in resp.json()[0]

def test_list_golden_explicit_version_and_split(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_get(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr(router_mod, "get_golden_set", fake_get)
    resp = client.get("/api/forging/golden-set?version=2&split=heldout")
    assert resp.status_code == 200
    assert captured.get("version") == 2
    assert captured.get("split") == "heldout"

def test_freeze_forwards_custom_ratios(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_freeze(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return {
            "version": 3, "frozen": 10,
            "counts": {"train": 7, "validation": 2, "heldout": 1},
            "status": "ready", "frozen_at": datetime.now(timezone.utc),
            "min_reward": 0.6, "human_only": True, "replaced": False, "warnings": []
        }
    monkeypatch.setattr(router_mod, "freeze_golden_set", fake_freeze)
    ratios = {"train": 0.8, "validation": 0.1, "heldout": 0.1}
    resp = client.post("/api/forging/golden-set", json={"min_reward": 0.6, "human_only": True, "limit": 100, "ratios": ratios})
    assert resp.status_code == 200
    assert captured["ratios"] == ratios

def test_freeze_invalid_ratios_returns_422(forging_client, monkeypatch):
    client, router_mod = forging_client
    async def fake_freeze(mdb, user_id, **kwargs):
        raise ValueError("Invalid split ratios")
    monkeypatch.setattr(router_mod, "freeze_golden_set", fake_freeze)
    resp = client.post("/api/forging/golden-set", json={"ratios": {"train": 0.5, "validation": 0.1, "heldout": 0.1}})
    assert resp.status_code == 422

def test_list_golden_defaults_to_latest(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_get(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return [{"_id": "mongo-1", "input": "hi", "expected": "hello", "split": "train"}]
    monkeypatch.setattr(router_mod, "get_golden_set", fake_get)
    resp = client.get("/api/forging/golden-set")
    assert resp.status_code == 200
    assert captured.get("version") is None
    assert captured.get("split") is None
    assert "_id" not in resp.json()[0]

def test_list_golden_explicit_version_and_split(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_get(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr(router_mod, "get_golden_set", fake_get)
    resp = client.get("/api/forging/golden-set?version=2&split=heldout")
    assert resp.status_code == 200
    assert captured.get("version") == 2
    assert captured.get("split") == "heldout"

def test_export_defaults_to_train_summary(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_export(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return {
            "format": "sft", "split": kwargs.get("split", "train"),
            "dataset_version": 2, "examples": 5, "golden_available": 5,
            "jsonl": '{"prompt": "q"}', "warnings": []
        }
    monkeypatch.setattr(router_mod, "export_golden_set", fake_export)
    resp = client.get("/api/forging/golden-set/export?format=sft&download=false")
    assert resp.status_code == 200
    assert captured.get("split") == "train"

def test_export_download_includes_metadata_headers(forging_client, monkeypatch):
    client, router_mod = forging_client
    async def fake_export(mdb, user_id, **kwargs):
        return {
            "format": "sft", "split": "heldout", "dataset_version": 3,
            "examples": 1, "golden_available": 1, "jsonl": '{"prompt": "q"}',
            "warnings": []
        }
    monkeypatch.setattr(router_mod, "export_golden_set", fake_export)
    resp = client.get("/api/forging/golden-set/export?format=sft&version=3&split=heldout&download=true")
    assert resp.status_code == 200
    assert resp.headers.get("x-dataset-split") == "heldout"
    assert resp.headers.get("x-dataset-version") == "3"

def test_harness_forwards_version_split_and_provider_ids(forging_client, monkeypatch):
    client, router_mod = forging_client
    captured = {}
    async def fake_provider(db, user_id, provider_id):
        return SimpleNamespace(id=provider_id, name="p")
    async def fake_run_harness(mdb, user_id, **kwargs):
        captured.update(kwargs)
        return {
            "evaluated": 1, "split": kwargs.get("split"),
            "dataset_version": kwargs.get("version"),
            "base_model": "b", "forged_model": "f",
            "mean_base": 0.5, "mean_forged": 0.9, "delta": 0.4,
            "message": None, "examples": []
        }
    monkeypatch.setattr(router_mod, "_provider", fake_provider)
    monkeypatch.setattr(router_mod, "run_harness", fake_run_harness)
    payload = {
        "version": 2, "split": "heldout",
        "base_provider_id": 1, "base_model": "b",
        "forged_provider_id": 2, "forged_model": "f",
        "system_prompt": "", "limit": 10
    }
    resp = client.post("/api/forging/harness", json=payload)
    assert resp.status_code == 200
    assert captured.get("version") == 2
    assert captured.get("split") == "heldout"

def test_edition_gate_blocks_community_edition(monkeypatch):
    monkeypatch.setattr(settings, "edition", "community")
    async def fake_user():
        return SimpleNamespace(id=42)
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = fake_user
    try:
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/forging/golden-set")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
