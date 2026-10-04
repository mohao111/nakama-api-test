import requests

from config.config import BASE_URL, LEADERBOARD_ID


def test_missing_token_rejected():
    resp = requests.get(f"{BASE_URL}/v2/account")
    assert resp.status_code == 401


def test_malformed_token_rejected():
    resp = requests.get(
        f"{BASE_URL}/v2/account",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_write_score_without_score_field(authed_client):
    resp = requests.post(
        f"{BASE_URL}/v2/leaderboard/{LEADERBOARD_ID}",
        json={},
        headers=authed_client.bearer,
    )
    # 实测：缺 score 未被拒绝，服务器按 0 分建了记录（proto3 省略零值，故返回里无 score 字段）
    assert resp.status_code == 200
    assert resp.json()["leaderboard_id"] == LEADERBOARD_ID


def test_write_storage_without_objects_field(authed_client):
    resp = requests.put(
        f"{BASE_URL}/v2/storage", json={}, headers=authed_client.bearer
    )
    # 实测：缺 objects 未被拒绝，空操作返回 200
    assert resp.status_code == 200
    assert resp.json() == {}
