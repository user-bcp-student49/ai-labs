# Hallazgos

## API

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto estático embebido y sin firma | Vulnerabilidad | Antes, identidad y rol se aceptaban mediante Base64 y un secreto fijo. Resolución: JWT RS256 verificado por JWKS con `sub`, `role`, `iss`, `aud` y `exp` obligatorios; parámetros externos, HTTPS para JWKS remoto y errores genéricos. La conexión con el emisor real y sus claims acordados aún no se ha probado. | api/app/security.py:13-72, api/requirements.txt:4 | alta | Resuelto |
| H-API-02 | api | El cliente puede elegir el owner de consultas y tareas | Vulnerabilidad | Antes, query y body podían seleccionar otro propietario. Resolución: las consultas usan el sujeto autenticado y los `owner` explícitos discordantes reciben HTTP 403; la creación siempre asigna el sujeto del JWT. | api/app/routes.py:28-54, api/app/routes.py:79-85 | alta | Resuelto |
| H-API-03 | api | Filtros e inserts SQL concatenan valores de entrada | Vulnerabilidad | Los valores de filtro e inserción se interpolaban en SQL. Resolución: se parametrizaron filtros, insert y selección de la tarea creada. | api/app/repository.py:56-83, api/app/repository.py:85-90 | alta | Resuelto |
| H-API-04 | api | La carga admite nombres drive-relative de Windows | Vulnerabilidad | Se rechazan nombres drive-relative sin raíz, y se verifica que el destino resuelto permanezca dentro del directorio de cargas. Se mantienen los límites de extensión y 1 MiB, el basename normalizado y el rechazo de colisiones. | api/app/services.py:81-84, api/app/services.py:126-130, api/tests/test_api.py:383-399 | alta | Resuelto |
| H-API-05 | api | Rutas, persistencia, reglas y serialización están concentradas en un módulo | Refactor | Resolución: se separaron fábrica, rutas, modelos Pydantic, servicios, repositorio y seguridad en módulos de `api/app/`; las rutas/métodos y formatos exitosos observados se mantienen. | api/app/main.py:17-60, api/app/routes.py:21-77, api/app/schemas.py:1-51, api/app/services.py:28-148, api/app/repository.py:35-98 | media | Resuelto |
| H-API-06 | api | Manejo amplio de excepciones en consulta de salud | Refactor | La consulta de salud todavía convierte cualquier excepción en status 0 y devuelve su texto en el cuerpo. Este comportamiento observado no se modificó porque H-API-06 no forma parte del alcance de esta implementación. | api/app/services.py:99-121 | media | Aprobado |
| H-API-07 | api | Dependencias fijadas requieren verificación de advisories | Sugerencia | `urllib3` y `python-multipart` están fijadas a las versiones indicadas en RETO.md. La versión fijada por sí sola no confirma que exista una vulnerabilidad aplicable; hay que contrastar advisories y compatibilidad antes de afirmar el riesgo o cambiar dependencias. | api/requirements.txt:5-6 | baja | Aprobado |

## Contrato observado durante discovery (antes de implementación)

`docs/ENDPOINTS.md` no existe. Lo siguiente registra el comportamiento previo a
la implementación; no es un contrato acordado:

- Todas las rutas siguientes dependen de `legacy_identity`, que espera un encabezado `Authorization` con un token Base64 cuyo contenido tiene cuatro partes separadas por `|`; valida secreto y expiración y devuelve `username` y `role` (api/app/main.py:17-24).
- `GET /api/tasks` devuelve tareas en JSON, acepta `owner` opcional y, si falta o es vacío, usa el usuario del token (api/app/main.py:67-75).
- `POST /api/tasks` acepta un cuerpo JSON, devuelve `201` y la tarea creada; los campos `status`, `priority` y `owner` tienen valores predeterminados (api/app/main.py:77-88).
- `GET /api/summary` devuelve `owner`, `total`, `byStatus` y `highPriorityOpen`; acepta `owner` opcional con el mismo valor predeterminado que la lista (api/app/main.py:90-105).
- `POST /api/requirements` recibe un archivo multipart, devuelve `201` con propietario, nombre, ruta guardada y tamaño (api/app/main.py:107-112).
- `GET /api/backend-health` consulta el URL configurado o `http://localhost:8080/q/health`; devuelve estado y cuerpo de la respuesta, o estado `0` y el texto de la excepción (api/app/main.py:114-122).

No se ejecutaron pruebas durante este discovery.

## Comportamiento actual tras H-API-01/02/04/05

- Las rutas protegidas requieren `Authorization: Bearer <JWT>` firmado con
  RS256. La clave pública se resuelve desde `JWT_JWKS_URL`; se validan firma,
  emisor, audiencia, expiración y claims `sub` y `role`. Issuer, audience y URL
  se configuran mediante `JWT_ISSUER`, `JWT_AUDIENCE` y `JWT_JWKS_URL`;
  JWKS remotos requieren HTTPS.
- `GET /api/tasks` y `GET /api/summary` usan la identidad autenticada. Un
  `owner` no vacío que difiere del sujeto devuelve `403`. `POST /api/tasks`
  devuelve `403` si el `owner` del cuerpo difiere; si se omite, usa el sujeto.
- Las cargas aceptan `.txt` y `.md` de hasta 1 MiB. Se guarda el basename
  normalizado. Extensiones no admitidas devuelven `400`, exceso de tamaño
  `413`, colisión `409`; nombre multipart vacío se rechaza por FastAPI con
  `422`. Los archivos existentes no se sobrescriben.
- Las formas JSON y los códigos exitosos observados para tareas, resumen,
  carga y backend-health siguen cubiertos por pruebas de caracterización.
- La integración con el emisor JWT real no se probó; confirmar soporte RS256,
  JWKS, `iss` y `aud` con su responsable.
