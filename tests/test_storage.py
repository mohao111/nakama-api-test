import json


def test_write_and_read_storage_object(authed_client):
    value = json.dumps({"progress": 50})
    w = authed_client.write_storage(
        [{"collection": "saves", "key": "save1", "value": value}]
    )
    assert w.status_code == 200
    assert w.json()["acks"][0]["version"]

    user_id = authed_client.get_account().json()["user"]["id"]
    r = authed_client.read_storage(
        [{"collection": "saves", "key": "save1", "user_id": user_id}]
    )
    assert r.status_code == 200
    objects = r.json().get("objects", [])
    assert len(objects) == 1
    assert json.loads(objects[0]["value"])["progress"] == 50


def test_read_missing_object_returns_empty(authed_client):
    user_id = authed_client.get_account().json()["user"]["id"]
    r = authed_client.read_storage(
        [{"collection": "saves", "key": "nope", "user_id": user_id}]
    )
    assert r.status_code == 200
    assert r.json().get("objects", []) == []
