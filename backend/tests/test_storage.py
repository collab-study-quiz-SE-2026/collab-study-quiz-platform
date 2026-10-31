import os
from contextlib import closing
from uuid import uuid4

import pytest
from botocore.exceptions import EndpointConnectionError
from botocore.stub import Stubber
from fastapi.testclient import TestClient

from app.main import app
from app.storage import get_storage_client


def test_storage_health(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "TESTACCESSKEY")
    monkeypatch.setenv("S3_SECRET_KEY", "test-only-secret")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    with closing(get_storage_client()) as storage:
        monkeypatch.setattr("app.main.get_storage_client", lambda: storage)
        with Stubber(storage) as stubber:
            stubber.add_response("head_bucket", {}, {"Bucket": "test-bucket"})
            with TestClient(app) as client:
                response = client.get("/health/storage")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "storage": "connected"}


def test_storage_unavailable(monkeypatch):
    def unavailable():
        raise EndpointConnectionError(endpoint_url="http://private-connection-details")

    monkeypatch.setattr("app.main.get_storage_client", unavailable)
    with TestClient(app) as client:
        response = client.get("/health/storage")
    assert response.status_code == 503
    assert response.json() == {"detail": "Storage unavailable"}


def test_storage_round_trip():
    if os.getenv("RUN_STORAGE_TESTS") != "1":
        pytest.skip("Set RUN_STORAGE_TESTS=1 with local S3 settings")

    bucket = os.environ["S3_BUCKET"]
    key = f"foundation-checks/{uuid4()}.txt"
    payload = b"CSMQP storage connection check"
    with closing(get_storage_client()) as client:
        try:
            client.put_object(Bucket=bucket, Key=key, Body=payload)
            result = client.get_object(Bucket=bucket, Key=key)
            with closing(result["Body"]) as body:
                assert body.read() == payload
        finally:
            client.delete_object(Bucket=bucket, Key=key)
