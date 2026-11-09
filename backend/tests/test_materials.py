from io import BytesIO
from collections.abc import Generator

from botocore.stub import Stubber
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Material, MaterialStatus
from app.models import User, UserRole


@pytest.fixture
def test_setup(monkeypatch) -> Generator[tuple, None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", "materials-test-secret")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with session_factory() as session:
        student = User(
            email="materials@example.com",
            password_hash=hash_password("materialpass"),
            role=UserRole.STUDENT,
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        token = create_access_token(student)

    with TestClient(app) as client:
        yield client, session_factory, student, token
    app.dependency_overrides.clear()


def test_authenticated_users_can_browse_published_materials(test_setup):
    client, session_factory, student, token, *_ = test_setup
    with session_factory() as session:
        session.add_all(
            [
                Material(
                    title="Distributed Systems Notes",
                    course_code="CS401",
                    tags=["systems", "notes"],
                    storage_key="materials/systems.md",
                    content_type="text/markdown",
                    file_name="systems.md",
                    uploader_id=student.id,
                    status=MaterialStatus.PUBLISHED,
                ),
                Material(
                    title="Hidden Notes",
                    course_code="CS401",
                    tags=["hidden"],
                    storage_key="materials/hidden.pdf",
                    content_type="application/pdf",
                    file_name="hidden.pdf",
                    uploader_id=student.id,
                    status=MaterialStatus.HIDDEN,
                ),
            ]
        )
        session.commit()

    response = client.get(
        "/materials?course_code=CS401&tag=systems",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Distributed Systems Notes"]


def test_material_download_requires_authentication_and_streams_allowed_file(
    test_setup, monkeypatch
):
    client, session_factory, student, token, *_ = test_setup
    with session_factory() as session:
        material = Material(
            title="Guide",
            course_code="CS101",
            tags=["guide"],
            storage_key="materials/guide.pdf",
            content_type="application/pdf",
            file_name="guide.pdf",
            uploader_id=student.id,
        )
        session.add(material)
        session.commit()
        session.refresh(material)

    monkeypatch.setenv("S3_BUCKET", "materials")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "TESTACCESSKEY")
    monkeypatch.setenv("S3_SECRET_KEY", "test-only-secret")
    import app.main

    client_s3 = app.main.get_storage_client()
    monkeypatch.setattr(app.main, "get_storage_client", lambda: client_s3)
    with Stubber(client_s3) as stubber:
        stubber.add_response(
            "get_object",
            {"Body": BytesIO(b"hello"), "ContentLength": 5},
            {"Bucket": "materials", "Key": "materials/guide.pdf"},
        )
        unauthorized = client.get(f"/materials/{material.id}/download")
        assert unauthorized.status_code == 401
        downloaded = client.get(
            f"/materials/{material.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert downloaded.status_code == 200
    assert downloaded.content == b"hello"
    assert downloaded.headers["content-disposition"] == 'attachment; filename="guide.pdf"'
