"""API tests for the Application Tracker (Module 13)."""

from __future__ import annotations


async def _profile(client) -> int:
    resp = await client.post(
        "/api/v1/profiles",
        json={"name": "Jane Engineer", "email": "jane@example.com"},
    )
    return resp.json()["id"]


async def _company(client, name: str = "Stripe") -> int:
    resp = await client.post("/api/v1/companies", json={"name": name})
    return resp.json()["id"]


async def test_track_and_read(client):
    pid = await _profile(client)
    cid = await _company(client)

    resp = await client.post(
        f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "saved"
    assert len(body["events"]) == 1

    app_id = body["id"]
    got = await client.get(f"/api/v1/applications/{app_id}")
    assert got.status_code == 200
    assert got.json()["id"] == app_id


async def test_track_idempotent(client):
    pid = await _profile(client)
    cid = await _company(client)

    first = await client.post(
        f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
    )
    second = await client.post(
        f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
    )
    assert first.json()["id"] == second.json()["id"]


async def test_advance_status(client):
    pid = await _profile(client)
    cid = await _company(client)
    app_id = (
        await client.post(
            f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
        )
    ).json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "applied", "note": "Submitted online"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "applied"
    assert body["events"][-1]["note"] == "Submitted online"


async def test_invalid_transition_returns_422(client):
    pid = await _profile(client)
    cid = await _company(client)
    app_id = (
        await client.post(
            f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
        )
    ).json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/status", json={"status": "offer"}
    )
    assert resp.status_code == 422


async def test_add_note(client):
    pid = await _profile(client)
    cid = await _company(client)
    app_id = (
        await client.post(
            f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
        )
    ).json()["id"]

    resp = await client.post(
        f"/api/v1/applications/{app_id}/notes", json={"note": "Referred by Sam"}
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Referred by Sam"


async def test_list_with_status_filter(client):
    pid = await _profile(client)
    cid = await _company(client)
    app_id = (
        await client.post(
            f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/applications/{app_id}/status", json={"status": "applied"}
    )

    resp = await client.get(
        f"/api/v1/profiles/{pid}/applications", params={"status": "applied"}
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] == app_id

    none = await client.get(
        f"/api/v1/profiles/{pid}/applications", params={"status": "offer"}
    )
    assert none.json() == []


async def test_delete(client):
    pid = await _profile(client)
    cid = await _company(client)
    app_id = (
        await client.post(
            f"/api/v1/profiles/{pid}/applications", json={"company_id": cid}
        )
    ).json()["id"]

    resp = await client.delete(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 204
    got = await client.get(f"/api/v1/applications/{app_id}")
    assert got.status_code == 404


async def test_track_unknown_profile_404(client):
    cid = await _company(client)
    resp = await client.post(
        "/api/v1/profiles/999999/applications", json={"company_id": cid}
    )
    assert resp.status_code == 404
