from contextlib import closing
from io import BytesIO

from botocore.exceptions import ClientError
from app.storage import get_storage_client
import os
from collections.abc import Generator
from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import StudyMaterial, User


@pytest.fixture
def material_client(monkeypatch) -> Generator[TestClient, None, None]:
    test_database = os.getenv("TEST_PGDATABASE")

    if not test_database:
        pytest.skip("Set TEST_PGDATABASE to a dedicated test database")

    if test_database == os.getenv("PGDATABASE", "postgres"):
        pytest.fail("TEST_PGDATABASE must differ from the development database")

    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-secret")
    

    test_url = URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.getenv("PGHOST", "127.0.0.1"),
        port=int(os.getenv("PGPORT", "5432")),
        database=test_database,
    )

    test_engine = create_engine(test_url)
    TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        with TestSession.begin() as session:
            session.execute(
                delete(User).where(User.email.like("material-test-%"))
            )

        app.dependency_overrides.clear()
        test_engine.dispose()


@pytest.fixture
def mock_storage(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    storage = Mock()
    monkeypatch.setattr("app.main.get_storage_client", lambda: storage)
    return storage

def register_and_login(client: TestClient) -> str:
    email = f"material-test-{uuid4()}@example.com"

    registration = client.post(
        "/auth/register",
        json={"email": email, "password": "Correct-Horse-123"},
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": email, "password": "Correct-Horse-123"},
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_authentication(material_client):
    response = material_client.post(
        "/materials/upload",
        data={"title": "DBMS Notes", "course_code": "DBMS101"},
        files={"file": ("notes.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 401


def test_upload_pdf_success(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={
            "title": "DBMS Notes",
            "course_code": "DBMS101",
            "tags": "sql, database, college",
        },
        files={
            "file": (
                "dbms.pdf",
                b"%PDF-1.4 test document",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    result = response.json()
    assert result["title"] == "DBMS Notes"
    assert result["course_code"] == "DBMS101"
    assert result["tags"] == ["sql", "database", "college"]
    assert result["original_filename"] == "dbms.pdf"
    assert result["file_type"] == "pdf"
    assert result["file_size"] == len(b"%PDF-1.4 test document")
    assert "storage_key" not in result

    mock_storage.put_object.assert_called_once()
    assert mock_storage.put_object.call_args.kwargs["Bucket"] == "test-bucket"


def test_upload_markdown_success(material_client, mock_storage):
    token = register_and_login(material_client)

    content = b"# Database Notes\n\nSQL basics."

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={
            "title": "SQL Notes",
            "course_code": "DBMS101",
            "tags": "sql, notes",
        },
        files={
            "file": ("sql.md", content, "text/markdown")
        },
    )

    assert response.status_code == 201
    assert response.json()["file_type"] == "markdown"
    assert response.json()["mime_type"] == "text/markdown"
    mock_storage.put_object.assert_called_once()


def test_upload_rejects_unsupported_file(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={"title": "Notes", "course_code": "DBMS101"},
        files={"file": ("notes.exe", b"some content", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Only PDF and Markdown" in response.json()["detail"]
    mock_storage.put_object.assert_not_called()


def test_upload_rejects_empty_file(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={"title": "Empty Notes", "course_code": "DBMS101"},
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file cannot be empty"
    mock_storage.put_object.assert_not_called()


def test_upload_rejects_file_over_25_mb(material_client, mock_storage):
    token = register_and_login(material_client)

    oversized_content = b"%PDF-" + (
        b"x" * (25 * 1024 * 1024)
    )

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={"title": "Large PDF", "course_code": "DBMS101"},
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File size exceeds the 25 MB limit"
    mock_storage.put_object.assert_not_called()


def test_upload_rejects_invalid_pdf_content(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={"title": "Invalid PDF", "course_code": "DBMS101"},
        files={
            "file": (
                "invalid.pdf",
                b"This is not a PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid PDF file content"
    mock_storage.put_object.assert_not_called()


def test_upload_saves_metadata(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={
            "title": "Operating Systems",
            "course_code": "OS101",
            "tags": "processes, scheduling",
        },
        files={
            "file": (
                "os.md",
                b"# Operating Systems",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201

    session_factory = app.dependency_overrides[get_db]
    session = next(session_factory())

    try:
        material = session.scalar(
            select(StudyMaterial).where(
                StudyMaterial.id == response.json()["id"]
            )
        )

        assert material is not None
        assert material.title == "Operating Systems"
        assert material.course_code == "OS101"
        assert material.tags == ["processes", "scheduling"]
        assert material.original_filename == "os.md"
        assert material.file_size == len(b"# Operating Systems")
    finally:
        session.close()


def test_upload_storage_failure(material_client, mock_storage):
    token = register_and_login(material_client)
    mock_storage.put_object.side_effect = RuntimeError("Storage unavailable")

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={"title": "DBMS Notes", "course_code": "DBMS101"},
        files={
            "file": ("notes.md", b"# Notes", "text/markdown")
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to upload study material"


def test_upload_real_storage_round_trip(material_client, monkeypatch):
    if os.getenv("RUN_UPLOAD_INTEGRATION") != "1":
        pytest.skip("Set RUN_UPLOAD_INTEGRATION=1 to test real storage")

    monkeypatch.setenv("S3_BUCKET", os.environ["S3_BUCKET"])

    token = register_and_login(material_client)
    content = b"%PDF-1.4\nReal RustFS integration test\n"

    response = material_client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={
            "title": "Real Storage Integration Test",
            "course_code": "TEST101",
            "tags": "integration, rustfs",
        },
        files={
            "file": (
                "integration.pdf",
                content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    session_factory = app.dependency_overrides[get_db]
    session = next(session_factory())

    try:
        material = session.get(StudyMaterial, response.json()["id"])
        assert material is not None

        storage_key = material.storage_key

        with closing(get_storage_client()) as storage:
            result = storage.get_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=storage_key,
            )

            with closing(result["Body"]) as body:
                assert body.read() == content

            storage.delete_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=storage_key,
            )
    finally:
        session.close()



def upload_test_material(
    client,
    token,
    title="Test Notes",
    filename="notes.md",
    content=b"# Test Notes",
    content_type="text/markdown",
):
    return client.post(
        "/materials/upload",
        headers=auth_headers(token),
        data={
            "title": title,
            "course_code": "TEST101",
            "tags": "testing, notes",
        },
        files={"file": (filename, content, content_type)},
    )


def test_list_materials_requires_authentication(material_client):
    response = material_client.get("/materials")

    assert response.status_code == 401


def test_download_material_requires_authentication(material_client):
    response = material_client.get("/materials/1/download")

    assert response.status_code == 401


def test_list_materials_success(material_client, mock_storage):
    token = register_and_login(material_client)

    first = upload_test_material(
        material_client, token, title="DBMS Notes"
    )
    second = upload_test_material(
        material_client, token, title="Python Notes"
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = material_client.get(
        "/materials",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    materials = response.json()
    assert len(materials) >= 2

    titles = [material["title"] for material in materials]
    assert "DBMS Notes" in titles
    assert "Python Notes" in titles

    for material in materials:
        assert "storage_key" not in material
        assert "title" in material
        assert "course_code" in material
        assert "tags" in material


def test_download_material_success(material_client, mock_storage):
    token = register_and_login(material_client)
    content = b"# Downloadable Study Notes"

    upload = upload_test_material(
        material_client,
        token,
        filename="download-notes.md",
        content=content,
    )

    assert upload.status_code == 201
    material_id = upload.json()["id"]

    mock_storage.get_object.return_value = {
        "Body": BytesIO(content)
    }

    response = material_client.get(
        f"/materials/{material_id}/download",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    mock_storage.get_object.assert_called_once()


def test_download_material_not_found(material_client, mock_storage):
    token = register_and_login(material_client)

    response = material_client.get(
        "/materials/999999/download",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Study material not found"
    mock_storage.get_object.assert_not_called()


def test_download_missing_storage_file(material_client, mock_storage):
    token = register_and_login(material_client)

    upload = upload_test_material(material_client, token)
    assert upload.status_code == 201

    mock_storage.get_object.side_effect = ClientError(
        {
            "Error": {
                "Code": "NoSuchKey",
                "Message": "The requested object does not exist",
            }
        },
        "GetObject",
    )

    material_id = upload.json()["id"]

    response = material_client.get(
        f"/materials/{material_id}/download",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Study material file not found in storage"
    )


def test_download_storage_unavailable(material_client, mock_storage):
    token = register_and_login(material_client)

    upload = upload_test_material(material_client, token)
    assert upload.status_code == 201

    mock_storage.get_object.side_effect = ClientError(
        {
            "Error": {
                "Code": "InternalError",
                "Message": "Storage unavailable",
            }
        },
        "GetObject",
    )

    material_id = upload.json()["id"]

    response = material_client.get(
        f"/materials/{material_id}/download",
        headers=auth_headers(token),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Storage service is unavailable"