def test_get_account_returns_user(authed_client):
    resp = authed_client.get_account()
    assert resp.status_code == 200
    assert "user" in resp.json()


def test_update_display_name(authed_client):
    resp = authed_client.update_account("testplayer")
    assert resp.status_code == 200
    account = authed_client.get_account().json()
    assert account["user"]["display_name"] == "testplayer"


def test_update_display_name_too_long_rejected(authed_client):
    resp = authed_client.update_account("x" * 256)
    assert resp.status_code >= 400
