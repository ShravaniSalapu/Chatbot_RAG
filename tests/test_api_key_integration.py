"""Integration tests for API key database auth (requires PostgreSQL)."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() in ("1", "true", "yes"),
    reason="Set SKIP_INTEGRATION_TESTS=false and run PostgreSQL to enable",
)


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_register_login_and_api_key_flow(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"test_{suffix}@example.com"
    password = "testpass123"

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "tenant_name": f"Test Org {suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    key_resp = client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "integration-test-key"},
    )
    assert key_resp.status_code == 201, key_resp.text
    api_key = key_resp.json()["api_key"]
    assert api_key.startswith("rag_")

    me = client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
    assert me.status_code == 200
    assert me.json()["email"] == email

    cache = client.get("/api/v1/cache/test", headers={"X-API-Key": api_key})
    assert cache.status_code == 200
    body = cache.json()
    assert "redis" in body
