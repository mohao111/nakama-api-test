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
    written = []
    owner_ids = []
    for s in (10, 300, 150):
        c = NakamaClient(BASE_URL, SERVER_KEY)
        c.session(f"lb-{uuid.uuid4()}")
        c.write_leaderboard_record(LEADERBOARD_ID, score=s)
        owner_ids.append(c.get_account().json()["user"]["id"])
        written.append(s)
    reader = NakamaClient(BASE_URL, SERVER_KEY)
    reader.session(f"lb-reader-{uuid.uuid4()}")
    resp = reader.list_leaderboard_records(LEADERBOARD_ID, owner_ids=owner_ids)
    got = [int(r["score"]) for r in resp.json().get("owner_records", [])]
    assert sorted(got) == sorted(written)
    assert got == sorted(got, reverse=True)
