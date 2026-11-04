import os
import re
import hashlib
import hmac
import json
from pathlib import Path
from time import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


TEST_DB_PATH = Path(f"./test_optimos_{uuid4().hex}.db").resolve()
# Set TEST_DATABASE_URL to run the suite against PostgreSQL instead of SQLite.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["ALLOW_SELF_SERVICE_TIER_CHANGE"] = "true"  # legacy tests upgrade via API
os.environ["RATE_LIMIT_DEFAULT_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_AUTH_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_AI_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_ADMIN_REQUESTS"] = "10000"

from app.db.base import Base
import app.models  # noqa: F401
from app.core import security as security_module
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.services.email_service import EmailService

TEST_EMAIL_OUTBOX = []


@pytest.fixture(scope="session")
def engine():
    # Keep hashing lightweight during tests to avoid long-running auth tests.
    security_module.pwd_context = CryptContext(
        schemes=["bcrypt"],
        bcrypt__rounds=4,
        deprecated="auto",
    )

    connect_args = {"check_same_thread": False} if TEST_DATABASE_URL.startswith("sqlite") else {}
    db_engine = create_engine(TEST_DATABASE_URL, connect_args=connect_args)
    Base.metadata.create_all(bind=db_engine)
    yield db_engine
    Base.metadata.drop_all(bind=db_engine)
    db_engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def clear_data(engine):
    # Start each test with a clean schema state.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def capture_test_emails(monkeypatch):
    TEST_EMAIL_OUTBOX.clear()
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Optimos Test <test@example.com>")

    async def capture_email(self, recipient, subject, html, text):
        TEST_EMAIL_OUTBOX.append(
            {"recipient": recipient, "subject": subject, "html": html, "text": text}
        )

    monkeypatch.setattr(EmailService, "send_email", capture_email)


@pytest.fixture()
def client(db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def latest_test_email(email: str, subject_fragment: str):
    return next(
        message
        for message in reversed(TEST_EMAIL_OUTBOX)
        if message["recipient"].lower() == email.lower()
        and subject_fragment.lower() in message["subject"].lower()
    )


def confirm_registered_email(client, email: str) -> None:
    sent = latest_test_email(email, "verify")
    token = re.search(r"[?&]token=([A-Za-z0-9_-]+)", sent["text"]).group(1)
    response = client.post(
        "/api/auth/email-verification/confirm",
        json={"token": token},
    )
    assert response.status_code == 200


def post_signed_stripe_event(client, event: dict, secret: str):
    timestamp = int(time())
    payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
    signed_payload = str(timestamp).encode("ascii") + b"." + payload
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return client.post(
        "/api/billing/webhooks",
        content=payload,
        headers={"Stripe-Signature": f"t={timestamp},v1={digest}"},
    )


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
