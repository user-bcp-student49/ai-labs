# Contrato HTTP

## API FastAPI

Base local documentada: `http://localhost:8000`. Los cinco endpoints requieren
autenticación mediante el header exacto `Authorization: Bearer <JWT>`. El token
debe estar firmado con RS256 y validarse con el JWKS configurado. Son
obligatorios los claims `sub`, `role`, `iss`, `aud` y `exp`; el emisor y la
audiencia esperados se configuran con `JWT_ISSUER` y `JWT_AUDIENCE`, y la URL
JWKS con `JWT_JWKS_URL` (`api/app/security.py:13-49`).

En los ejemplos, `<JWT_RS256_VALIDO>` representa un token emitido por el
proveedor configurado para esta API; no es un token literal ni una credencial
incluida en este documento. La integración con el emisor real y sus valores
`iss`/`aud` aún debe confirmarse. Un `role` válido es obligatorio en el token,
pero estas rutas no aplican reglas de autorización por rol.

Los ejemplos con fecha, identificador y contenido son representativos: esos
valores dependen de la base de datos, la hora y la respuesta del servicio
consultado. Las respuestas de validación `422` corresponden al formato
observado con FastAPI/Pydantic en el entorno del proyecto. No se define un
formato propio para errores internos no capturados (`500`); su cuerpo depende
del servidor ASGI y queda como pregunta abierta.

## `GET /api/tasks`

### 1. Qué hace

Devuelve la lista de tareas del usuario autenticado (`api/app/routes.py:28-35`).

### 2. Autenticación

Requerida: `Authorization: Bearer <JWT>`. El token debe cumplir las condiciones
descritas arriba. La identidad usada para filtrar tareas proviene del claim
`sub`, no de un `owner` elegido por el cliente
(`api/app/security.py:26-49`, `api/app/routes.py:29-35,79-85`).

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` | Header `string` | Sí | Esquema `Bearer` seguido por un JWT válido. |
| `owner` | Query `string` | No | Si se omite o es vacío, se usa el `sub` autenticado. Si no coincide con el `sub`, se rechaza con `403`; no permite consultar otro propietario. |

Ejemplo completo:

```http
GET /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <JWT_RS256_VALIDO>
```

El parámetro opcional puede especificarse como
`GET /api/tasks?owner=student`; solo se acepta si coincide exactamente con el
sujeto autenticado.

### 4. Response exitosa

Código: `200 OK`. La respuesta es una lista, posiblemente vacía.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `integer` | Identificador de la tarea. |
| `title` | `string` | Título. |
| `description` | `string` | Descripción. |
| `status` | `string` | Estado almacenado. |
| `owner` | `string` | Propietario asociado a la identidad autenticada. |
| `priority` | `string` | Prioridad almacenada. |
| `createdAt` | `string` | Fecha/hora almacenada por SQLite en formato `YYYY-MM-DD HH:MM:SS`. |

Ejemplo:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-11-02 22:00:00"
  }
]
```

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente, esquema no `Bearer`, token mal formado, firma/claims inválidos o token expirado. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | Se envía `owner` distinto del `sub` del token. | `{"detail":"Owner does not match identity"}` |
| `503 Service Unavailable` | Falta configuración JWT, la URL JWKS no es segura o el servicio JWKS no está disponible. | `{"detail":"Authentication is not configured"}` o `{"detail":"Authentication service is unavailable"}` |
| `500 Internal Server Error` | Error interno no manejado por la ruta; la aplicación no define un cuerpo estable para este caso. | Pregunta abierta: el cuerpo depende de la configuración del servidor ASGI. |

### 6. Notas de seguridad

- El filtro de base de datos siempre usa la identidad autenticada. Un `owner`
  distinto no puede acceder a tareas de otra identidad; se rechaza en lugar de
  ignorarse (`api/app/routes.py:79-85`, `api/app/repository.py:56-61`).
- El `owner` se trata como parámetro enlazado SQL (`api/app/repository.py:56-61`).

## `POST /api/tasks`

### 1. Qué hace

Crea una tarea para el usuario autenticado (`api/app/routes.py:38-46`).

### 2. Autenticación

Requerida: `Authorization: Bearer <JWT>`, con los claims y la verificación
indicados al inicio de esta sección (`api/app/security.py:13-49`).

### 3. Request

Content-Type: `application/json`. El objeto cuerpo es obligatorio; todas sus
propiedades tienen valores predeterminados en el modelo, por lo que `{}` es
válido (`api/app/schemas.py:15-20`).

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` | Header `string` | Sí | `Bearer` seguido por un JWT válido. |
| `title` | JSON `string` | No | Título; predeterminado `""`. |
| `description` | JSON `string` | No | Descripción; predeterminado `""`. |
| `status` | JSON `string` | No | Estado; predeterminado `"TODO"`. Máximo 255 caracteres; no se valida contra una enumeración en este modelo. |
| `priority` | JSON `string` | No | Prioridad; predeterminado `"MEDIUM"`. Máximo 255 caracteres; no se valida contra una enumeración en este modelo. |
| `owner` | JSON `string` o `null` | No | Si se omite, es `null` o es vacío, se asigna el sujeto autenticado. Un valor no vacío distinto del sujeto se rechaza con `403`. |

`title` y `description` también admiten hasta 255 caracteres cada uno. Los
cuatro campos pueden omitirse, conservando sus valores predeterminados; un
valor que exceda el máximo se rechaza con `422`.

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <JWT_RS256_VALIDO>
Content-Type: application/json

{
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "priority": "HIGH"
}
```

### 4. Response exitosa

Código: `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `integer` | Identificador generado para la tarea. |
| `title` | `string` | Título almacenado. |
| `description` | `string` | Descripción almacenada. |
| `status` | `string` | Estado almacenado. |
| `owner` | `string` | Sujeto autenticado; no el valor proporcionado por un cliente discordante. |
| `priority` | `string` | Prioridad almacenada. |
| `createdAt` | `string` | Fecha/hora almacenada por SQLite, `YYYY-MM-DD HH:MM:SS`. |

Ejemplo:

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-11-02 22:00:00"
}
```

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido/expirado. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | El campo `owner` no vacío no coincide con el `sub` del token. | `{"detail":"Owner does not match identity"}` |
| `422 Unprocessable Entity` | Falta el objeto JSON, un campo presente no tiene el tipo esperado o cualquiera de los cuatro campos de texto excede 255 caracteres. | Respuesta de validación de FastAPI/Pydantic. |
| `503 Service Unavailable` | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Authentication is not configured"}` o `{"detail":"Authentication service is unavailable"}` |
| `500 Internal Server Error` | Error interno no manejado; no hay cuerpo estable definido por esta API. | Pregunta abierta: lo determina la configuración del servidor ASGI. |

### 6. Notas de seguridad

- La tarea se crea con `identity.username`, y no con un `owner` elegido por el
  cliente (`api/app/routes.py:41-46`).
- El repositorio enlaza los valores SQL como parámetros
  (`api/app/repository.py:63-82`).
- El modelo acepta cualquier texto para `status` y `priority`; el código no
  declara enumeraciones para esos campos (`api/app/schemas.py:15-20`).

## `GET /api/summary`

### 1. Qué hace

Resume el total de tareas, su distribución por estado y las tareas abiertas de
prioridad alta del usuario autenticado (`api/app/routes.py:48-55`,
`api/app/services.py:49-68`).

### 2. Autenticación

Requerida: `Authorization: Bearer <JWT>`, con los claims y la verificación
indicados al inicio (`api/app/security.py:13-49`).

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` | Header `string` | Sí | `Bearer` seguido por un JWT válido. |
| `owner` | Query `string` | No | Si se omite o es vacío, se usa el `sub` autenticado. Un valor distinto se rechaza con `403`. |

Ejemplo completo:

```http
GET /api/summary HTTP/1.1
Host: localhost:8000
Authorization: Bearer <JWT_RS256_VALIDO>
```

### 4. Response exitosa

Código: `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | `string` | Sujeto autenticado usado para el resumen. |
| `total` | `integer` | Número total de tareas de ese usuario. |
| `byStatus` | `object<string, integer>` | Conteo de tareas agrupado por el texto de estado almacenado. |
| `highPriorityOpen` | `integer` | Conteo de tareas con prioridad `HIGH` y estado distinto de `DONE` y `ARCHIVED`. |

Ejemplo:

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido/expirado. | `{"detail":"Invalid token"}` |
| `403 Forbidden` | Se envía `owner` distinto del `sub` autenticado. | `{"detail":"Owner does not match identity"}` |
| `503 Service Unavailable` | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Authentication is not configured"}` o `{"detail":"Authentication service is unavailable"}` |
| `500 Internal Server Error` | Error interno no manejado; no hay cuerpo estable definido por esta API. | Pregunta abierta: lo determina el servidor ASGI. |

### 6. Notas de seguridad

- Tanto las filas consultadas como el propietario de la respuesta derivan del
  sujeto autenticado; la consulta SQL usa un parámetro enlazado
  (`api/app/routes.py:49-55`, `api/app/repository.py:87-91`).
- Un parámetro `owner` no permite consultar datos de otra identidad
  (`api/app/routes.py:79-85`).

## `POST /api/requirements`

### 1. Qué hace

Guarda un documento de requisitos de texto asociado al usuario autenticado
(`api/app/routes.py:57-68`).

### 2. Autenticación

Requerida: `Authorization: Bearer <JWT>`, con los claims y la verificación
indicados al inicio (`api/app/security.py:13-49`).

### 3. Request

Content-Type: `multipart/form-data`.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` | Header `string` | Sí | `Bearer` seguido por un JWT válido. |
| `file` | Multipart `UploadFile` | Sí | Archivo con extensión `.txt` o `.md` (sin distinción de mayúsculas) y hasta 1 MiB (1.048.576 bytes). Se guarda el basename normalizado. El MIME no se valida explícitamente. |

Ejemplo completo:

```bash
curl -X POST "http://localhost:8000/api/requirements" \
  -H "Authorization: Bearer ${JWT}" \
  -F "file=@requirements.md;type=text/markdown"
```

`JWT` debe contener un token RS256 válido del emisor configurado. Ejemplo del
archivo enviado:

```text
Login must be accessible
```

### 4. Response exitosa

Código: `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | `string` | Sujeto autenticado que subió el archivo. |
| `fileName` | `string` | Basename normalizado guardado. |
| `storedAt` | `string` | Ruta del archivo según el directorio configurado. |
| `size` | `integer` | Tamaño del contenido guardado en bytes. |

Ejemplo si `WORKSHOP_UPLOAD_DIR=./uploads`:

```json
{
  "owner": "student",
  "fileName": "requirements.md",
  "storedAt": "uploads/requirements.md",
  "size": 24
}
```

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `400 Bad Request` | Nombre inválido, nombre drive-relative de Windows, destino resuelto fuera del directorio o extensión no permitida. | `{"detail":"Invalid file name"}` o `{"detail":"Unsupported file type"}` |
| `401 Unauthorized` | Header ausente o token inválido/expirado. | `{"detail":"Invalid token"}` |
| `409 Conflict` | Ya existe un archivo con ese nombre; no se sobrescribe. | `{"detail":"A file with this name already exists"}` |
| `413 Content Too Large` | El contenido supera 1 MiB. | `{"detail":"Uploaded file is too large"}` |
| `422 Unprocessable Entity` | Falta el campo multipart `file`, no es multipart válido o el nombre de archivo vacío es rechazado por FastAPI. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| `503 Service Unavailable` | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Authentication is not configured"}` o `{"detail":"Authentication service is unavailable"}` |
| `500 Internal Server Error` | Error interno no manejado al leer o guardar; no hay cuerpo estable definido por esta API. | Pregunta abierta: lo determina el servidor ASGI. |

### 6. Notas de seguridad

- Solo se admiten extensiones `.txt` y `.md`, se lee hasta superar el límite y
  se rechazan archivos demasiado grandes antes de guardarlos
  (`api/app/services.py:16-18,144-157`).
- Se normalizan separadores POSIX/Windows, se rechazan nombres
  drive-relative y se comprueba que la ruta resuelta quede dentro del
  directorio configurado (`api/app/services.py:81-84,126-136`).
- La apertura exclusiva (`xb`) evita sobrescribir un nombre existente
  (`api/app/services.py:86-93`).
- La respuesta asocia la carga al sujeto del token, no a un campo enviado por
  el cliente (`api/app/routes.py:61-68`).

## `GET /api/backend-health`

### 1. Qué hace

Consulta el endpoint de salud del servicio de autenticación y devuelve el
estado HTTP y cuerpo recibidos (`api/app/routes.py:70-74`,
`api/app/services.py:104-125`).

### 2. Autenticación

Requerida: `Authorization: Bearer <JWT>`, con los claims y la verificación
indicados al inicio (`api/app/security.py:13-49`).

### 3. Request

No tiene cuerpo ni parámetros de ruta o query.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---:|---|
| `Authorization` | Header `string` | Sí | `Bearer` seguido por un JWT válido. |

La URL consultada se configura con `AUTH_HEALTH_URL`; si falta, se usa
`http://localhost:8080/q/health` (`api/app/services.py:19,105`).

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <JWT_RS256_VALIDO>
```

### 4. Response exitosa

Código HTTP: `200 OK`, incluso cuando la consulta al servicio externo falla.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | `string` | Sujeto autenticado que solicitó el chequeo. |
| `status` | `integer` | Código HTTP del servicio externo; es `0` cuando la solicitud genera una excepción. |
| `body` | `string` | Cuerpo recibido del servicio externo o texto de la excepción en caso de fallo. |

Ejemplo cuando el servicio externo responde HTTP 200:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "[{\"status\": \"UP\"}]"
}
```

Si la llamada externa falla, la forma sigue siendo HTTP 200 y contiene, por
ejemplo, `{"requestedBy":"student","status":0,"body":"<texto de excepción>"}`.
El texto depende de la excepción concreta.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| `401 Unauthorized` | Header ausente o token inválido/expirado. | `{"detail":"Invalid token"}` |
| `503 Service Unavailable` | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Authentication is not configured"}` o `{"detail":"Authentication service is unavailable"}` |
| `500 Internal Server Error` | Error interno no manejado fuera de la captura del servicio; no hay cuerpo estable definido por esta API. | Pregunta abierta: lo determina el servidor ASGI. |

Un error de conexión al servicio de autenticación **no** se devuelve como
respuesta HTTP de error de esta API: se representa en la respuesta `200` con
`status: 0` y el texto de excepción en `body`
(`api/app/services.py:104-125`).

### 6. Notas de seguridad

- Este endpoint también requiere JWT; la respuesta identifica al solicitante
  con el `sub` verificado (`api/app/routes.py:70-74`).
- El cuerpo de error externo se devuelve como texto sin traducir. No se
  garantiza que sea estable ni genérico; esta conducta permanece como riesgo
  pendiente registrado en H-API-06 (`api/app/services.py:114-125`,
  `HALLAZGOS.md`, H-API-06).

## Preguntas abiertas

- Confirmar con el emisor JWT real que publica JWKS compatible con RS256 y
  acordar los valores de issuer y audience. La configuración y la verificación
  están implementadas, pero esa integración no se ha probado
  (`HALLAZGOS.md`, H-API-01).
- Acordar un contrato estable para errores internos `500`; la aplicación no
  define un handler global para ellos.
- Definir si los estados y prioridades de tareas deben limitarse a valores
  enumerados; el modelo actual los acepta como texto (`api/app/schemas.py:15-20`).
