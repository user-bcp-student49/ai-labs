import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from httpx import Response

import app.services as services
from app.main import create_app

ENDPOINTS = (
    ("GET", "/api/tasks"),
    ("POST", "/api/tasks"),
    ("GET", "/api/summary"),
    ("POST", "/api/requirements"),
    ("GET", "/api/backend-health"),
)
JWT_ISSUER = "https://issuer.test"
JWT_AUDIENCE = "workshop-api"
TEST_KEY_ID = "test-key"
TEST_SIGNING_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
TEST_PUBLIC_JWK = json.loads(
    jwt.algorithms.RSAAlgorithm.to_jwk(TEST_SIGNING_KEY.public_key())
)
TEST_PUBLIC_JWK.update({"kid": TEST_KEY_ID, "use": "sig", "alg": "RS256"})


class JwksHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps({"keys": [TEST_PUBLIC_JWK]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def jwks_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), JwksHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/.well-known/jwks.json"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.fixture(autouse=True)
def jwt_configuration(monkeypatch: pytest.MonkeyPatch, jwks_url: str) -> None:
    monkeypatch.setenv("JWT_ISSUER", JWT_ISSUER)
    monkeypatch.setenv("JWT_AUDIENCE", JWT_AUDIENCE)
    monkeypatch.setenv("JWT_JWKS_URL", jwks_url)


def token(
    username: str = "student",
    role: str = "STUDENT",
    *,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE,
    expires_at: int | None = None,
) -> str:
    claims = {
        "sub": username,
        "role": role,
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + 3600 if expires_at is None else expires_at,
    }
    return jwt.encode(
        claims,
        TEST_SIGNING_KEY,
        algorithm="RS256",
        headers={"kid": TEST_KEY_ID},
    )


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def request_endpoint(
    client: TestClient,
    method: str,
    path: str,
    request_headers: dict[str, str] | None = None,
) -> Response:
    selected_headers = request_headers or {}
    if method == "POST" and path == "/api/tasks":
        return client.post(path, headers=selected_headers, json={})
    if method == "POST" and path == "/api/requirements":
        return client.post(
            path,
            headers=selected_headers,
            files={"file": ("requirements.txt", b"requirements", "text/plain")},
        )
    return client.get(path, headers=selected_headers)


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["title"] == "Refactor login"


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "Add tests",
                "description": "Improve coverage",
                "status": "TODO",
                "priority": "HIGH",
            },
        )
        summary = client.get("/api/summary", headers=headers())

    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_create_task_preserves_quotes_in_text_fields(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "O'Reilly's task",
                "description": "A user's requirement",
                "status": "TODO",
                "priority": "HIGH",
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "O'Reilly's task"
    assert response.json()["description"] == "A user's requirement"


def test_owner_filters_treat_quotes_as_literal_values(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        tasks = client.get(
            "/api/tasks",
            headers=headers(username="student'"),
        )
        summary = client.get(
            "/api/summary",
            headers=headers(username="student'"),
        )

    assert tasks.status_code == 200
    assert tasks.json() == []
    assert summary.status_code == 200
    assert summary.json() == {
        "owner": "student'",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_task_list_and_summary_contract(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        tasks = client.get("/api/tasks", headers=headers())
        summary = client.get("/api/summary", headers=headers())

    assert tasks.status_code == 200
    assert tasks.json()[0]["title"] == "Refactor login"
    assert set(tasks.json()[0]) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }
    assert summary.status_code == 200
    assert summary.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_task_creation_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Characterization task"},
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Characterization task"
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["owner"] == "student"
    assert response.json()["priority"] == "MEDIUM"
    assert set(response.json()) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }


def test_task_creation_accepts_empty_object(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["owner"] == "student"
    assert response.json()["priority"] == "MEDIUM"


@pytest.mark.parametrize(
    "payload",
    [None, {"title": 42}],
    ids=("missing-json-body", "wrong-field-type"),
)
def test_task_creation_rejects_invalid_request_body(
    tmp_path: Path,
    payload: dict[str, object] | None,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        if payload is None:
            response = client.post("/api/tasks", headers=headers())
        else:
            response = client.post("/api/tasks", headers=headers(), json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_task_list_with_empty_owner_uses_authenticated_identity(
    tmp_path: Path,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers=headers(),
            params={"owner": ""},
        )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(task["owner"] == "student" for task in response.json())


def test_rejects_cross_owner_access_and_creation(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        tasks = client.get(
            "/api/tasks",
            headers=headers(),
            params={"owner": "trainer"},
        )
        summary = client.get(
            "/api/summary",
            headers=headers(),
            params={"owner": "trainer"},
        )
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Trainer task", "owner": "trainer"},
        )

    assert tasks.status_code == 403
    assert summary.status_code == 403
    assert created.status_code == 403


def test_characterizes_requirement_upload_response(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.md", b"Requirements", "text/markdown")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.md",
        "storedAt": str(upload_dir / "requirements.md"),
        "size": len(b"Requirements"),
    }
    assert (upload_dir / "requirements.md").read_bytes() == b"Requirements"


def test_normalizes_upload_filename(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("folder\\requirements.md", b"Requirements", "text/markdown")},
        )

    assert response.status_code == 201
    assert response.json()["fileName"] == "requirements.md"
    assert (upload_dir / "requirements.md").read_bytes() == b"Requirements"
    assert not (tmp_path / "requirements.md").exists()


@pytest.mark.parametrize(
    ("filename", "content_size", "expected_status"),
    [
        ("requirements.pdf", 6, 400),
        ("requirements.txt", 1_048_577, 413),
        ("", 10, 422),
    ],
    ids=("unsupported-extension", "over-size-limit", "empty-filename"),
)
def test_rejects_invalid_requirement_uploads(
    tmp_path: Path,
    filename: str,
    content_size: int,
    expected_status: int,
) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={
                "file": (
                    filename,
                    b"x" * content_size,
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == expected_status
    assert list(upload_dir.iterdir()) == []


def test_accepts_requirement_at_maximum_size(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    content = b"x" * 1_048_576
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )

    assert response.status_code == 201
    assert response.json()["size"] == len(content)
    assert (upload_dir / "requirements.txt").stat().st_size == len(content)


def test_rejects_upload_filename_without_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"Requirements", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file type"}
    assert list(upload_dir.iterdir()) == []


def test_rejects_requirement_upload_without_file_field(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_rejects_requirement_filename_collision(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    existing_file = upload_dir / "requirements.md"
    existing_file.write_bytes(b"existing")
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.md", b"replacement", "text/markdown")},
        )

    assert response.status_code == 409
    assert existing_file.read_bytes() == b"existing"


def test_backend_health_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class HealthResponse:
        status = 200
        data = json.dumps([{"status": "UP"}]).encode()

    class HealthPool:
        def request(
            self,
            method: str,
            url: str,
            timeout: float,
        ) -> HealthResponse:
            assert method == "GET"
            assert url == "http://localhost:8080/q/health"
            assert timeout == 3.0
            return HealthResponse()

    monkeypatch.setattr(services.urllib3, "PoolManager", HealthPool)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '[{"status": "UP"}]',
    }


def test_backend_health_reports_upstream_exception_in_success_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedHealthPool:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise RuntimeError("test-only connection failure")

    monkeypatch.setattr(services.urllib3, "PoolManager", FailedHealthPool)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "test-only connection failure",
    }


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )

    assert response.status_code == 201
    assert (upload_dir / "requirements.txt").exists()


def test_rejects_drive_relative_upload_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    upload_dir = Path("uploads")
    app = create_app("workshop.db", str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("C:outside.md", b"Requirements", "text/markdown")},
        )

    assert response.status_code == 400
    assert not (tmp_path / "outside.md").exists()
    assert list(upload_dir.iterdir()) == []


def test_accepts_valid_jwt_and_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        valid = client.get("/api/tasks", headers=headers())
        invalid = client.get(
            "/api/tasks",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        missing = client.get("/api/tasks")

    assert valid.status_code == 200
    assert invalid.status_code == 401
    assert invalid.json() == {"detail": "Invalid token"}
    assert missing.status_code == 401


@pytest.mark.parametrize(
    "claims",
    [
        {"issuer": "https://wrong-issuer.test"},
        {"audience": "another-api"},
        {"expires_at": int(time.time()) - 1},
    ],
)
def test_rejects_jwt_with_invalid_claims(
    tmp_path: Path,
    claims: dict[str, str | int],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token(**claims)}"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_jwt_with_invalid_signature(tmp_path: Path) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged_token = jwt.encode(
        {
            "sub": "student",
            "role": "STUDENT",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        other_key,
        algorithm="RS256",
        headers={"kid": TEST_KEY_ID},
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {forged_token}"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_legacy_base64_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={
                "Authorization": "Bearer student|STUDENT|9999999999|fake",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_unapproved_jwt_algorithm(tmp_path: Path) -> None:
    unapproved_token = jwt.encode(
        {
            "sub": "student",
            "role": "STUDENT",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        "test-only-hmac-key-for-rejected-algorithm",
        algorithm="HS256",
        headers={"kid": TEST_KEY_ID},
    )
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {unapproved_token}"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_reports_authentication_configuration_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JWT_JWKS_URL")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured"}


def test_rejects_non_tls_remote_jwks_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_JWKS_URL", "http://auth.example.test/jwks")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured"}


def test_reports_jwks_connection_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_JWKS_URL", "http://127.0.0.1:1/jwks")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service is unavailable"}


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_all_endpoints_reject_missing_authentication(
    tmp_path: Path,
    method: str,
    path: str,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, method, path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_all_endpoints_report_missing_jwt_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    monkeypatch.delenv("JWT_JWKS_URL")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, method, path, headers())

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured"}


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_all_endpoints_report_unavailable_jwks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    monkeypatch.setenv("JWT_JWKS_URL", "http://127.0.0.1:1/jwks")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, method, path, headers())

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service is unavailable"}


@pytest.mark.parametrize(
    ("method", "path", "service_name", "service_method"),
    [
        ("GET", "/api/tasks", "TaskService", "list_tasks"),
        ("POST", "/api/tasks", "TaskService", "create_task"),
        ("GET", "/api/summary", "TaskService", "summary"),
        ("POST", "/api/requirements", "RequirementService", "save"),
        ("GET", "/api/backend-health", "BackendHealthService", "get_status"),
    ],
)
def test_unhandled_endpoint_failures_return_internal_server_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    service_name: str,
    service_method: str,
) -> None:
    def fail_service(*args: object, **kwargs: object) -> None:
        raise RuntimeError("test-only service failure")

    service_class = getattr(services, service_name)
    monkeypatch.setattr(service_class, service_method, fail_service)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = request_endpoint(client, method, path, headers())

    assert response.status_code == 500
