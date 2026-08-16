"""Accounts and sessions: sign-in, the rate limit, admin-only user management,
and (once routes are guarded) that no API route is reachable signed out."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.main as main
from server import auth, db
from server.scanner.scan import Scanner
from tests.helpers import ADMIN_CREDS, auth_env, sign_in_admin

DJ_CREDS = {"username": "sarah", "password": "sarahs-first-password"}


@pytest.fixture()
def anon_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A fresh app whose admin exists but where nobody has signed in yet."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "library.db")
    monkeypatch.setattr(main, "SCANNER", Scanner())
    monkeypatch.setattr(main, "_index_cache", None)
    auth_env(monkeypatch)
    auth.reset_rate_limits()
    with TestClient(main.app) as client:
        yield client
    auth.reset_rate_limits()


@pytest.fixture()
def client(anon_client: TestClient) -> TestClient:
    sign_in_admin(anon_client)
    return anon_client


def create_dj(client: TestClient) -> None:
    response = client.post(
        "/api/users",
        json={"username": DJ_CREDS["username"], "display_name": "Sarah V.",
              "password": DJ_CREDS["password"]},
    )
    assert response.status_code == 201, response.text


def sign_in(client: TestClient, creds: dict) -> None:
    client.post("/api/auth/logout")
    response = client.post("/api/auth/login", json=creds)
    assert response.status_code == 200, response.text


# --- passwords ---------------------------------------------------------------

def test_password_hash_round_trip() -> None:
    stored = auth.hash_password("hunter2-but-longer")
    assert auth.verify_password("hunter2-but-longer", stored)
    assert not auth.verify_password("hunter2-but-wrong", stored)


def test_password_hashes_are_salted() -> None:
    assert auth.hash_password("same input") != auth.hash_password("same input")


def test_malformed_stored_hash_never_verifies() -> None:
    for stored in ("", "plaintext", "scrypt$oops", "md5$1$1$1$00$00"):
        assert not auth.verify_password("anything", stored)


# --- sign in / out -----------------------------------------------------------

def test_admin_bootstrap_and_login(anon_client: TestClient) -> None:
    response = anon_client.post("/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    assert "rm_session" in anon_client.cookies

    me = anon_client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user"]["username"] == ADMIN_CREDS["username"]


def test_bootstrap_never_overwrites_an_existing_admin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "a-brand-new-password")
    auth.ensure_admin_from_env()
    sign_in(client, ADMIN_CREDS)  # the original password still works


def test_wrong_password_and_unknown_user_read_the_same(anon_client: TestClient) -> None:
    for username in (ADMIN_CREDS["username"], "nobody"):
        response = anon_client.post(
            "/api/auth/login", json={"username": username, "password": "wrong-wrong"}
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "BAD_CREDENTIALS"


def test_logout_kills_the_session(client: TestClient) -> None:
    assert client.get("/api/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/me").status_code == 401


def test_login_rate_limit_counts_failures_only(anon_client: TestClient) -> None:
    bad = {"username": ADMIN_CREDS["username"], "password": "wrong-wrong"}
    for _ in range(auth.RATE_MAX_FAILURES):
        assert anon_client.post("/api/auth/login", json=bad).status_code == 401
    # Even the right password is refused now — the window has to slide first.
    blocked = anon_client.post("/api/auth/login", json=ADMIN_CREDS)
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMITED"


# --- admin: DJ accounts ------------------------------------------------------

def test_admin_creates_a_dj_who_can_sign_in(client: TestClient) -> None:
    create_dj(client)
    sign_in(client, DJ_CREDS)
    me = client.get("/api/me").json()["user"]
    assert me == {"id": me["id"], "username": "sarah",
                  "display_name": "Sarah V.", "role": "dj"}


def test_duplicate_username_is_refused(client: TestClient) -> None:
    create_dj(client)
    response = client.post(
        "/api/users",
        json={"username": "Sarah", "password": "another-long-password"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DUPLICATE_USERNAME"


def test_short_passwords_are_refused(client: TestClient) -> None:
    response = client.post("/api/users", json={"username": "kim", "password": "short"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "WEAK_PASSWORD"


def test_password_reset_via_patch(client: TestClient) -> None:
    create_dj(client)
    user_id = next(
        u["id"] for u in client.get("/api/users").json()["users"]
        if u["username"] == "sarah"
    )
    assert client.patch(
        f"/api/users/{user_id}", json={"password": "a-new-longer-password"}
    ).status_code == 200
    sign_in(client, {"username": "sarah", "password": "a-new-longer-password"})


def test_disabling_a_dj_kills_their_session_and_login(client: TestClient) -> None:
    create_dj(client)
    users = client.get("/api/users").json()["users"]
    dj_id = next(u["id"] for u in users if u["username"] == "sarah")

    sign_in(client, DJ_CREDS)
    dj_cookie = client.cookies["rm_session"]

    sign_in(client, ADMIN_CREDS)
    assert client.patch(f"/api/users/{dj_id}", json={"disabled": True}).status_code == 200

    # The DJ's old session is dead, and a fresh sign-in is refused.
    client.cookies.set("rm_session", dj_cookie)
    assert client.get("/api/me").status_code == 401
    client.post("/api/auth/logout")
    refused = client.post("/api/auth/login", json=DJ_CREDS)
    assert refused.status_code == 403
    assert refused.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_djs_cannot_manage_accounts(client: TestClient) -> None:
    create_dj(client)
    sign_in(client, DJ_CREDS)
    assert client.get("/api/users").status_code == 403
    assert client.post(
        "/api/users", json={"username": "mole", "password": "mole-password-1"}
    ).status_code == 403


def test_the_admin_account_is_protected(client: TestClient) -> None:
    admin_id = client.get("/api/me").json()["user"]["id"]
    for response in (
        client.delete(f"/api/users/{admin_id}"),
        client.patch(f"/api/users/{admin_id}", json={"disabled": True}),
    ):
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "LAST_ADMIN"


def test_deleting_a_dj(client: TestClient) -> None:
    create_dj(client)
    dj_id = next(
        u["id"] for u in client.get("/api/users").json()["users"]
        if u["username"] == "sarah"
    )
    assert client.delete(f"/api/users/{dj_id}").status_code == 200
    assert client.delete(f"/api/users/{dj_id}").status_code == 404
