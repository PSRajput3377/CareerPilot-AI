"""Integration tests for the User Profile API (Module 1)."""

from __future__ import annotations


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_create_and_get_profile(client):
    payload = {
        "name": "Grace Hopper",
        "email": "grace@example.com",
        "preferred_role": "Compiler Engineer",
        "preferred_companies": ["IBM", "US Navy"],
        "skills": [{"name": "COBOL", "proficiency": "expert"}],
        "experiences": [{"company": "US Navy", "title": "Rear Admiral"}],
        "educations": [{"institution": "Yale", "degree": "PhD"}],
    }
    resp = await client.post("/api/v1/profiles", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] >= 1
    assert body["preferred_companies"] == ["IBM", "US Navy"]
    assert body["skills"][0]["name"] == "COBOL"

    pid = body["id"]
    got = await client.get(f"/api/v1/profiles/{pid}")
    assert got.status_code == 200
    assert got.json()["email"] == "grace@example.com"


async def test_duplicate_email_returns_409(client):
    payload = {"name": "A", "email": "dup@example.com"}
    assert (await client.post("/api/v1/profiles", json=payload)).status_code == 201
    second = await client.post("/api/v1/profiles", json=payload)
    assert second.status_code == 409


async def test_get_missing_returns_404(client):
    resp = await client.get("/api/v1/profiles/424242")
    assert resp.status_code == 404


async def test_patch_updates_profile(client):
    created = await client.post(
        "/api/v1/profiles", json={"name": "Edsger", "email": "ed@example.com"}
    )
    pid = created.json()["id"]
    patched = await client.patch(
        f"/api/v1/profiles/{pid}", json={"preferred_role": "Distinguished Engineer"}
    )
    assert patched.status_code == 200
    assert patched.json()["preferred_role"] == "Distinguished Engineer"


async def test_delete_then_404(client):
    created = await client.post(
        "/api/v1/profiles", json={"name": "Temp", "email": "temp@example.com"}
    )
    pid = created.json()["id"]
    assert (await client.delete(f"/api/v1/profiles/{pid}")).status_code == 204
    assert (await client.get(f"/api/v1/profiles/{pid}")).status_code == 404


async def test_invalid_salary_range_rejected(client):
    resp = await client.post(
        "/api/v1/profiles",
        json={
            "name": "Bad",
            "email": "bad@example.com",
            "preferred_salary_min": 200000,
            "preferred_salary_max": 100000,
        },
    )
    assert resp.status_code == 422
