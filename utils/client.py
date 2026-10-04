import base64

import requests


class NakamaClient:
    def __init__(self, base_url, server_key):
        self.base_url = base_url.rstrip("/")
        self.server_key = server_key
        self.token = None

    def _basic_auth(self):
        raw = f"{self.server_key}:".encode()
        return {"Authorization": "Basic " + base64.b64encode(raw).decode()}

    @property
    def bearer(self):
        return {"Authorization": f"Bearer {self.token}"}

    def authenticate_device(self, device_id, create=True, username=None):
        params = {"create": str(create).lower()}
        if username:
            params["username"] = username
        return requests.post(
            f"{self.base_url}/v2/account/authenticate/device",
            params=params,
            json={"id": device_id},
            headers=self._basic_auth(),
        )

    def session(self, device_id):
        resp = self.authenticate_device(device_id)
        resp.raise_for_status()
        self.token = resp.json()["token"]
        return self.token

    def get_account(self):
        return requests.get(f"{self.base_url}/v2/account", headers=self.bearer)

    def update_account(self, display_name):
        return requests.put(
            f"{self.base_url}/v2/account",
            json={"display_name": display_name},
            headers=self.bearer,
        )

    def write_leaderboard_record(self, leaderboard_id, score, subscore=None, metadata=None):
        body = {"score": score}
        if subscore is not None:
            body["subscore"] = subscore
        if metadata is not None:
            body["metadata"] = metadata
        return requests.post(
            f"{self.base_url}/v2/leaderboard/{leaderboard_id}",
            json=body,
            headers=self.bearer,
        )

    def list_leaderboard_records(self, leaderboard_id, limit=None, owner_ids=None):
        params = {}
        if limit is not None:
            params["limit"] = limit
        if owner_ids is not None:
            params["owner_ids"] = owner_ids
        return requests.get(
            f"{self.base_url}/v2/leaderboard/{leaderboard_id}",
            params=params,
            headers=self.bearer,
        )

    def write_storage(self, objects):
        return requests.put(
            f"{self.base_url}/v2/storage", json={"objects": objects}, headers=self.bearer
        )

    def read_storage(self, object_ids):
        return requests.post(
            f"{self.base_url}/v2/storage", json={"object_ids": object_ids}, headers=self.bearer
        )
