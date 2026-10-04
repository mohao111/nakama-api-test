from utils.client import NakamaClient
from config.config import BASE_URL, SERVER_KEY


def test_authenticate_device_returns_token(new_device_id):
    client = NakamaClient(BASE_URL, SERVER_KEY)
    resp = client.authenticate_device(new_device_id)
    assert resp.status_code == 200
    assert resp.json().get("token")
