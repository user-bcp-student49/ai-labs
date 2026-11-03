# Pruebas de API

## Alcance y entorno

Esta sección cubre los cinco endpoints API descritos en
[ENDPOINTS.md](./ENDPOINTS.md). Los casos se ejecutan con FastAPI `TestClient`,
SQLite y directorios temporales; JWT usa una clave RSA generada solo para
pruebas y un servidor JWKS local (`api/tests/test_api.py`). No se usan
credenciales ni servicios de producción.

El gateway externo de autenticación no se integró: issuer, audience y JWKS
reales continúan pendientes de coordinación. Los casos con JWKS no disponible
usan `127.0.0.1:1` y no representan una integración real.

## Matriz de casos

| Endpoint | Caso | Tipo | Resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Lista las tareas sembradas del sujeto autenticado (`test_lists_seeded_tasks`, `test_task_list_and_summary_contract`) | Camino feliz | `200`; lista de tareas del propietario autenticado con las claves del contrato. |
| `GET /api/tasks` | `owner` vacío | Borde | `200`; se usa el `sub` autenticado y no se cambia el propietario. |
| `GET /api/tasks` | Header ausente o JWT inválido | Error | `401`, `{"detail":"Invalid token"}`. Header ausente se prueba en cada endpoint; token inválido también en `test_accepts_valid_jwt_and_rejects_invalid_token`. |
| `GET /api/tasks` | `owner` distinto | Error / autorización | `403`, `{"detail":"Owner does not match identity"}`; no se consulta otro owner. |
| `GET /api/tasks` | Configuración JWT ausente / JWKS inaccesible | Error | `503`, respectivamente `Authentication is not configured` y `Authentication service is unavailable`. |
| `GET /api/tasks` | Fallo no manejado del servicio | Error | `500`; el cuerpo no se fija porque el contrato no lo define. |
| `POST /api/tasks` | Crea una tarea válida (`test_creates_task_and_summary`) | Camino feliz | `201`; tarea persistida bajo el sujeto autenticado. |
| `POST /api/tasks` | Cuerpo `{}` y campos omitidos | Borde | `201`; valores predeterminados del modelo, incluido owner del token. |
| `POST /api/tasks` | Cuerpo ausente o tipo incorrecto en `title` | Error / validación | `422`; error FastAPI/Pydantic. |
| `POST /api/tasks` | `title`, `description`, `status` y `priority` en 255 y 256 caracteres | Borde / límite | `201` en el máximo; `422` sobre el máximo y sin persistir la tarea. |
| `POST /api/tasks` | Owner discordante | Error / autorización | `403`; la tarea para otro owner no se crea. |
| `POST /api/tasks` | Header ausente, configuración JWT ausente o JWKS inaccesible | Error | `401` o `503` con cuerpo genérico de autenticación. |
| `POST /api/tasks` | Fallo no manejado del servicio | Error | `500`; solo se verifica el status porque no hay cuerpo estable documentado. |
| `GET /api/summary` | Resumen del sujeto autenticado (`test_task_list_and_summary_contract`) | Camino feliz | `200`; totales, agrupación por estado y conteo de prioridad alta abierta. |
| `GET /api/summary` | Sujeto autenticado sin tareas (`test_owner_filters_treat_quotes_as_literal_values`) | Borde | `200`; `total: 0`, `byStatus: {}` y `highPriorityOpen: 0`. |
| `GET /api/summary` | Header ausente | Error | `401`, `{"detail":"Invalid token"}`. |
| `GET /api/summary` | `owner` distinto | Error / autorización | `403`, `{"detail":"Owner does not match identity"}`. |
| `GET /api/summary` | Configuración JWT ausente / JWKS inaccesible | Error | `503` con cuerpo genérico de autenticación. |
| `GET /api/summary` | Fallo no manejado del servicio | Error | `500`; no se afirma un cuerpo que no está definido por la API. |
| `POST /api/requirements` | Sube `.md` válido (`test_characterizes_requirement_upload_response`) | Camino feliz | `201`; owner, basename, ruta de almacenamiento y tamaño corresponden al archivo guardado. |
| `POST /api/requirements` | Archivo de 1 MiB (`test_accepts_requirement_at_maximum_size`) | Borde | `201`; tamaño guardado exactamente 1.048.576 bytes. |
| `POST /api/requirements` | Extensión no permitida, sin extensión o nombre inválido | Error / borde | `400`; mensaje de extensión o nombre correspondiente; no se escribe un archivo rechazado. |
| `POST /api/requirements` | Archivo de 1 MiB + 1 byte | Error / límite | `413`, `{"detail":"Uploaded file is too large"}`; no se crea archivo parcial. |
| `POST /api/requirements` | Archivo multipart ausente o nombre vacío | Error / validación | `422`; validación de FastAPI. |
| `POST /api/requirements` | Nombre de archivo ya existente | Error | `409`; el contenido existente permanece intacto. |
| `POST /api/requirements` | Nombre drive-relative de Windows (`C:outside.md`) | Error / seguridad | `400`; no se crea archivo fuera ni dentro del directorio de cargas. |
| `POST /api/requirements` | Header ausente, configuración JWT ausente o JWKS inaccesible | Error | `401` o `503` con cuerpo genérico de autenticación. |
| `POST /api/requirements` | Fallo no manejado del servicio | Error | `500`; solo se verifica el status, no un cuerpo estable. |
| `GET /api/backend-health` | Servicio de salud externo responde (`test_backend_health_response`) | Camino feliz | `200`; `requestedBy`, status y cuerpo externo. |
| `GET /api/backend-health` | Excepción de conexión externa | Borde/error integrado | HTTP `200`; `status: 0` y texto de excepción en `body`, según comportamiento actual documentado. |
| `GET /api/backend-health` | Header ausente, configuración JWT ausente o JWKS inaccesible | Error | `401` o `503` con cuerpo genérico de autenticación. |
| `GET /api/backend-health` | Fallo no manejado de la ruta | Error | `500`; solo se verifica el status. |

Las respuestas `500` se documentan como posibles fallos internos sin cuerpo
estable. Las pruebas inyectan una excepción controlada en cada servicio y
afirman únicamente el status HTTP. El fallo del upstream de
`GET /api/backend-health` es distinto: el servicio lo captura y devuelve HTTP
`200` con `status: 0`. H-API-06 continúa aprobado y pendiente; este test
caracteriza la conducta actual y no la declara segura.

## Código de las pruebas añadidas

El conjunto completo, incluidos los tests de caracterización y JWT que ya
existían, está en [api/tests/test_api.py](../api/tests/test_api.py). Los
siguientes tests completan los casos borde y errores que faltaban:

```python
ENDPOINTS = (
    ("GET", "/api/tasks"),
    ("POST", "/api/tasks"),
    ("GET", "/api/summary"),
    ("POST", "/api/requirements"),
    ("GET", "/api/backend-health"),
)


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
```

También se añadió `test_backend_health_reports_upstream_exception_in_success_response`,
que verifica que un fallo upstream se representa con HTTP `200`, `status: 0`
y el texto de la excepción. El test de ruta drive-relative para Windows y los
casos de JWT, SQL, owner, extensiones, colisiones y tamaños ya están en el
mismo archivo.

## Ejecuciones y cobertura

Todas las rutas de comando siguientes se ejecutan desde la raíz `ai-labs`,
salvo que se indique explícitamente `api/`.

| Componente / IDs | Comando | Directorio | Código de salida | Resultado |
|---|---|---|---:|---|
| api / H-API-01/02/03/04/05 | `python tools/lab.py test api` | raíz del repositorio | `0` | **54 passed**, 1 advertencia externa deprecada de Starlette/AnyIO. |
| api / H-API-01/02/03/04/05 | Gate de pytest invocado por el comando anterior: `api/.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=85` | `api/` | `0` | Cobertura reportada por pytest: 95.58%; gate de 85% aprobado. Reporte HTML en `api/htmlcov/index.html`. |
| api / H-API-01/02/03/04/05 | `.\.venv\Scripts\python.exe -` (script PowerShell reproducible debajo, con `coverage.Coverage().load()` y `analysis2()` sobre los seis módulos modificados) | `api/` | `0` | Código de aplicación modificado: **255/262 sentencias = 97.33%**. |
| api / H-API-01/02/03/04/05 | `.\.venv\Scripts\python.exe -` (mismo script sobre todos los módulos medidos de `api/app/`) | `api/` | `0` | Cobertura global de aplicación: **255/262 sentencias = 97.33%**. Todo el código Python de `api/app/` en este cambio corresponde a módulos modificados o añadidos. |

Comando de conteo ejecutado desde `api/` en PowerShell:

```powershell
@'
from coverage import Coverage

coverage = Coverage()
coverage.load()
measured_files = coverage.get_data().measured_files()
modified_names = {"main.py", "repository.py", "routes.py", "schemas.py", "security.py", "services.py"}
modified_files = [
    path for path in measured_files
    if path.replace("\\", "/").split("/")[-1] in modified_names
]
app_files = [path for path in measured_files if "/app/" in path.replace("\\", "/")]

def report(label: str, paths: list[str]) -> None:
    analyses = [coverage.analysis2(path) for path in paths]
    statements = sum(len(analysis[1]) for analysis in analyses)
    missing = sum(len(analysis[3]) for analysis in analyses)
    covered = statements - missing
    print(f"{label}: {covered}/{statements} ({covered / statements * 100:.2f}%)")

report("modified app", modified_files)
report("global app", app_files)
'@ | .\.venv\Scripts\python.exe -
```

Salida real: `modified app: 255/262 (97.33%)` y
`global app: 255/262 (97.33%)`; código de salida `0`.

El porcentaje de pytest (95.58%) usa la medición configurada con líneas y
ramas. Los porcentajes 97.33% se calcularon aparte como sentencias ejecutables
cubiertas/total, agregadas sobre archivos de aplicación. Se reportan ambas
métricas por separado; ninguna cambia el gate.

## Fallos, pendientes y pruebas propuestas

### Fallos de las ejecuciones finales

- Ninguno: el comando final terminó con código `0` y 54 pruebas pasaron.
- Se mantiene la advertencia externa de deprecación de
  `anyio.abc.BlockingPortal` emitida desde Starlette; no se ocultó ni se cambió
  el gate.

### Pendientes

- **H-API-01:** confirmar con el responsable del emisor los valores reales de
  issuer/audience y la publicación de JWKS RS256. Las pruebas solo usan el
  servidor local de test.
- **H-API-06:** el backend-health devuelve `str(exception)` en `body` cuando
  falla el upstream; su test caracteriza esta conducta, no la aprueba como
  segura.
- **H-API-07:** contrastar versiones fijadas con advisories vigentes; esta suite
  no verifica CVEs ni sustituye Dependency Review.
- Las pruebas de `500` verifican solo el código; el cuerpo no tiene un
  contrato estable documentado.

### Pruebas propuestas

- Ejecutar una prueba de integración coordinada con el emisor real, en un
  entorno autorizado, para validar JWKS, `iss`, `aud`, rotación de claves y
  expiración.
- Ejecutar Dependency Review/SCA con el repositorio y las versiones fijadas
  para resolver H-API-07.
- Si se define un cuerpo estable para `500`, añadir aserciones de esquema y
  contenido al test parametrizado de fallos internos.
