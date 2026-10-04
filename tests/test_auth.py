from config.config import BASE_URL
from utils.client import NakamaClient


def test_authenticate_device_creates_account(client, new_device_id):
    resp = client.authenticate_device(new_device_id, create=True)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert "refresh_token" in body
    assert body.get("created") is True


def test_same_device_id_reuses_account(client, new_device_id):
    first = client.authenticate_device(new_device_id, create=True)
    second = client.authenticate_device(new_device_id, create=True)
    assert first.json().get("created") is True
    assert second.status_code == 200
    assert "created" not in second.json()


def test_authenticate_with_wrong_server_key_fails(new_device_id):
    bad = NakamaClient(BASE_URL, "definitely-wrong-key")
    resp = bad.authenticate_device(new_device_id)
    assert resp.status_code in (401, 403)
