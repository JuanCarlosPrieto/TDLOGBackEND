def test_register(client):
    body = {
        "email": "test@example.com",
        "username": "tester",
        "name": "John",
        "surname": "Doe",
        "password": "123456",
        "birthdate": "2000-01-01",
        "country": "Colombia"
    }

    response = client.post("/auth/register", json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


def test_login(client):
    client.post("/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "name": "Test",
        "surname": "User",
        "password": "123456",
        "birthdate": "2000-01-01",
        "country": "Colombia"
    })

    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "123456"
    })

    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


def test_refresh(client):
    client.post("/auth/register", json={
        "email": "refresh@example.com",
        "username": "refreshuser",
        "name": "Refresh",
        "surname": "User",
        "password": "123456",
        "birthdate": "2000-01-01",
        "country": "Colombia"
    })
    login_resp = client.post("/auth/login", json={
        "email": "refresh@example.com",
        "password": "123456"
    })

    refresh_token = login_resp.cookies.get("refresh_token")

    response = client.post("/auth/refresh", cookies={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.cookies


def test_me(client):
    client.post("/auth/register", json={
        "email": "profile@example.com",
        "username": "profile",
        "name": "Profile",
        "surname": "User",
        "password": "123456",
        "birthdate": "2000-01-01",
        "country": "Colombia"
    })
    login_resp = client.post("/auth/login", json={
        "email": "profile@example.com",
        "password": "123456"
    })

    access_token = login_resp.cookies.get("access_token")

    resp = client.get("/auth/me", cookies={"access_token": access_token})
    assert resp.status_code == 200
    assert resp.json()["email"] == "profile@example.com"


def test_update_user(client):
    client.post("/auth/register", json={
        "email": "update@example.com",
        "username": "updateuser",
        "name": "Old",
        "surname": "Name",
        "password": "123456",
        "birthdate": "2000-01-01",
        "country": "Colombia"
    })
    login_resp = client.post("/auth/login", json={
        "email": "update@example.com",
        "password": "123456"
    })
    access_token = login_resp.cookies.get("access_token")

    response = client.put(
        "/auth/update",
        cookies={"access_token": access_token},
        json={"name": "New Name"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_logout(client):
    response = client.post("/auth/logout")
    assert response.status_code == 200
