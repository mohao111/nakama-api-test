import uuid

from config.config import BASE_URL, SERVER_KEY, LEADERBOARD_ID
from utils.client import NakamaClient


def test_write_score_returns_record(authed_client):
    resp = authed_client.write_leaderboard_record(LEADERBOARD_ID, score=100)
    assert resp.status_code == 200
    assert resp.json()["score"] == "100"


def test_list_contains_submitted_score(authed_client):
    authed_client.write_leaderboard_record(LEADERBOARD_ID, score=250)
    owner_id = authed_client.get_account().json()["user"]["id"]
    resp = authed_client.list_leaderboard_records(LEADERBOARD_ID, owner_ids=[owner_id])
    assert resp.status_code == 200
    scores = [r["score"] for r in resp.json().get("owner_records", [])]
    assert "250" in scores


def test_leaderboard_sorted_descending():
    players = []
    for s in (10, 300, 150):
        c = NakamaClient(BASE_URL, SERVER_KEY)
        c.session(f"lb-{uuid.uuid4()}")
        c.write_leaderboard_record(LEADERBOARD_ID, score=s)
        players.append(c)
    resp = players[0].list_leaderboard_records(LEADERBOARD_ID, limit=100)
    scores = [int(r["score"]) for r in resp.json().get("records", [])]
    assert scores == sorted(scores, reverse=True)
