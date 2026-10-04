import uuid

import pytest

from config.config import BASE_URL, SERVER_KEY
from utils.client import NakamaClient


@pytest.fixture
def client():
    return NakamaClient(BASE_URL, SERVER_KEY)


@pytest.fixture
def new_device_id():
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def authed_client(client, new_device_id):
    client.session(new_device_id)
    return client
