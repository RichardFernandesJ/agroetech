"""Testes de cadastro, login e proteção por token."""

from httpx import AsyncClient


async def test_register_returns_public_user(
    client: AsyncClient,
    user_payload: dict[str, str],
) -> None:
    response = await client.post("/api/v1/auth/register", json=user_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == user_payload["email"]
    assert body["username"] == user_payload["username"]
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


async def test_login_accepts_email_or_username(
    client: AsyncClient,
    user_payload: dict[str, str],
) -> None:
    await client.post("/api/v1/auth/register", json=user_payload)

    for login in (user_payload["email"], user_payload["username"]):
        response = await client.post(
            "/api/v1/auth/login",
            json={"login": login, "password": user_payload["password"]},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["expires_in"] > 0


async def test_register_rejects_duplicate_email_and_username(
    client: AsyncClient,
    user_payload: dict[str, str],
) -> None:
    assert (await client.post("/api/v1/auth/register", json=user_payload)).status_code == 201

    duplicate_email = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "username": "outro_nome"},
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["code"] == "conflict"

    duplicate_username = await client.post(
        "/api/v1/auth/register",
        json={**user_payload, "email": "outro@agro.com.br"},
    )
    assert duplicate_username.status_code == 409


async def test_login_rejects_wrong_password(
    client: AsyncClient,
    user_payload: dict[str, str],
) -> None:
    await client.post("/api/v1/auth/register", json=user_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"login": user_payload["email"], "password": "senha-errada"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_error"


async def test_me_requires_valid_token(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_payload: dict[str, str],
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["email"] == user_payload["email"]

    missing = await client.get("/api/v1/auth/me")
    assert missing.status_code == 401

    invalid = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token-invalido"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "invalid_token"


async def test_register_validates_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "nao-e-email", "username": "ab", "password": "123"},
    )
    assert response.status_code == 422
