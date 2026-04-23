def test_create_and_list_assets(client) -> None:
    create_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.10.20",
            "type": "Linux",
            "name": "prod-web-01",
            "username": "root",
            "credential_password": "super-secret",
        },
    )

    assert create_response.status_code == 201
    created_asset = create_response.json()
    assert created_asset["ip"] == "192.168.10.20"
    assert created_asset["type"] == "linux"
    assert created_asset["name"] == "prod-web-01"
    assert created_asset["connection_type"] == "ssh"
    assert created_asset["port"] == 22
    assert created_asset["username"] == "root"
    assert created_asset["credential_configured"] is True
    assert isinstance(created_asset["credential_id"], int)
    assert isinstance(created_asset["id"], int)

    list_response = client.get("/api/v1/assets")

    assert list_response.status_code == 200
    assets = list_response.json()
    assert len(assets) == 1
    assert assets[0]["id"] == created_asset["id"]


def test_list_assets_supports_pagination(client) -> None:
    for index in range(3):
        response = client.post(
            "/api/v1/assets",
            json={
                "ip": f"192.168.10.3{index}",
                "type": "linux",
                "name": f"asset-{index}",
            },
        )
        assert response.status_code == 201

    response = client.get("/api/v1/assets?skip=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "asset-1"


def test_duplicate_ip_is_rejected(client) -> None:
    payload = {
        "ip": "10.0.0.8",
        "type": "switch",
        "name": "core-switch-01",
    }

    first_response = client.post("/api/v1/assets", json=payload)
    duplicate_response = client.post("/api/v1/assets", json=payload)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "conflict"


def test_create_asset_trims_ip_whitespace(client) -> None:
    response = client.post(
        "/api/v1/assets",
        json={
            "ip": " 192.168.10.25 ",
            "type": "linux",
            "name": "trimmed-asset",
        },
    )

    assert response.status_code == 201
    assert response.json()["ip"] == "192.168.10.25"


def test_delete_asset_removes_record(client) -> None:
    create_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "172.16.0.12",
            "type": "linux",
            "name": "jump-host-01",
        },
    )
    asset_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/assets/{asset_id}")
    list_response = client.get("/api/v1/assets")

    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_update_asset_rotates_connection_profile(client) -> None:
    create_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "172.16.0.13",
            "type": "switch",
            "name": "core-switch-02",
            "username": "admin",
            "vendor": "h3c",
            "credential_password": "initial-secret",
        },
    )
    asset_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/assets/{asset_id}",
        json={
            "name": "core-switch-02-a",
            "port": 2222,
            "username": "ops-admin",
            "vendor": "h3c",
            "is_enabled": False,
            "credential_password": "rotated-secret",
        },
    )

    assert update_response.status_code == 200
    updated_asset = update_response.json()
    assert updated_asset["name"] == "core-switch-02-a"
    assert updated_asset["port"] == 2222
    assert updated_asset["username"] == "ops-admin"
    assert updated_asset["is_enabled"] is False
    assert updated_asset["credential_configured"] is True


def test_openapi_exposes_asset_endpoints(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/assets" in openapi["paths"]
    assert "patch" in openapi["paths"]["/api/v1/assets/{asset_id}"]
    assert "/api/v1/assets/{asset_id}/ssh-test" in openapi["paths"]
    assert "/api/v1/assets/{asset_id}/port-scan" in openapi["paths"]
    assert "/api/v1/assets/{asset_id}/inspect" in openapi["paths"]
    assert "/api/v1/assets/{asset_id}/baseline" in openapi["paths"]
    assert "/api/v1/assets/{asset_id}" in openapi["paths"]
    parameter_names = {item["name"] for item in openapi["paths"]["/api/v1/assets"]["get"]["parameters"]}
    assert {"skip", "limit"} <= parameter_names
