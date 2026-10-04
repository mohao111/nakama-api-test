import uuid
from concurrent.futures import ThreadPoolExecutor

from config.config import BASE_URL, SERVER_KEY, LEADERBOARD_ID
from utils.client import NakamaClient


def _submit_score(score):
    c = NakamaClient(BASE_URL, SERVER_KEY)
    c.session(f"concurrent-{uuid.uuid4()}")
    status = c.write_leaderboard_record(LEADERBOARD_ID, score=score).status_code
    user_id = c.get_account().json()["user"]["id"]
    return score, status, user_id


def test_concurrent_writes_all_persist_and_sorted():
    scores = list(range(1000, 1000 + 20))
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(_submit_score, scores))
    assert all(status == 200 for _, status, _ in results), "并发写入有失败"

    user_ids = [uid for _, _, uid in results]
    c = NakamaClient(BASE_URL, SERVER_KEY)
    c.session(f"reader-{uuid.uuid4()}")
    resp = c.list_leaderboard_records(LEADERBOARD_ID, owner_ids=user_ids)
    got = [int(r["score"]) for r in resp.json().get("owner_records", [])]
    assert sorted(got) == sorted(scores), "并发写入有丢失"
    assert got == sorted(got, reverse=True), "榜单未按降序排列"
