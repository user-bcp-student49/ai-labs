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

## Candidatos API (discovery)

### H-API-08 — CORS permite cualquier origen con credenciales habilitadas
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:53-58` configura `allow_origins=["*"]`,
  `allow_credentials=True`, `allow_methods=["*"]` y `allow_headers=["*"]`.
  La autenticación de rutas observada usa un encabezado de autorización
  (`api/app/security.py:26-49`); no se confirmó aquí un flujo de cookies.
- Impacto: una política sin allowlist permite que cualquier origen web intente
  solicitudes cross-origin y lea las respuestas que el navegador permita. El
  impacto efectivo depende de credenciales usadas por la integración; el
  código API revisado no demuestra por sí solo un bypass del JWT.
- Prioridad propuesta: media, sujeta a confirmar el modelo de despliegue y
  credenciales del navegador.
- Contrato potencialmente afectado: política CORS esperada para los orígenes
  consumidores y su acceso a endpoints autenticados.
- Cómo validarlo: definir los orígenes autorizados y probar preflight y
  respuesta desde un origen permitido y otro no permitido; ejecutar
  `python tools/lab.py test api` para la regresión.

### H-API-09 — Campos de tarea sin límite de longitud
- Estado: Resuelto
- Evidencia: inicialmente `api/app/schemas.py:15-19` declaraba los cuatro
  campos sin `max_length`. Ahora comparten el máximo de 255 caracteres en
  `api/app/schemas.py:5,18-21`; `api/tests/test_api.py:251-294` comprueba
  aceptación en el máximo y rechazo por encima de él sin persistencia.
  `python tools/lab.py test api`: 59 pruebas pasaron; cobertura total 95.59%.
- Impacto: la API limita los cuatro campos de creación de tareas antes de
  persistirlos. Los límites de tamaño total en proxy o despliegue no se
  verificaron y siguen fuera de este cambio.
- Prioridad propuesta: media, condicionada a límites externos y al volumen de
  usuarios permitidos.
- Contrato potencialmente afectado: límites aceptados por `POST /api/tasks`
  y disponibilidad/almacenamiento de la API.
- Cómo validarlo: `python tools/lab.py test api`; las pruebas de frontera
  cubren los cuatro campos en 255 y 256 caracteres y verifican que las
  solicitudes rechazadas no agreguen tareas.

### H-API-10 — Estados y prioridades aceptan valores arbitrarios
- Estado: CANDIDATO
- Evidencia: `api/app/schemas.py:18-19` deja `status` y `priority` como
  cadenas libres; el contrato documenta que no se validan contra enumeraciones
  (`docs/ENDPOINTS.md:127-128`). El resumen agrupa cualquier estado pero solo
  cuenta como prioridad alta el texto exacto `HIGH`
  (`api/app/services.py:49-64`).
- Impacto: si el dominio espera un conjunto cerrado, datos con valores
  tipográficos o desconocidos se almacenan y aparecen como categorías nuevas
  en el resumen; prioridades fuera de `HIGH` no se cuentan como altas. La lista
  válida de valores no está especificada en la evidencia revisada.
- Prioridad propuesta: baja hasta acordar el vocabulario de negocio.
- Contrato potencialmente afectado: validación de `POST /api/tasks` y la
  semántica de `GET /api/summary`.
- Cómo validarlo: acordar primero los valores permitidos; enviar estados y
  prioridades desconocidos y comprobar si deben rechazarse o si el resumen
  debe conservar el comportamiento actual. Ejecutar
  `python tools/lab.py test api`.

### H-API-11 — Los nombres de carga comparten un espacio global entre usuarios
- Estado: CANDIDATO
- Evidencia: `api/app/services.py:77-89` crea el destino usando solo el nombre
  normalizado, y `api/app/services.py:87-93` responde `409` si ya existe. La
  ruta pasa el usuario como metadato de respuesta, no como parte del destino
  (`api/app/routes.py:57-68`); `api/tests/test_api.py:421-434` caracteriza el
  conflicto ante una colisión.
- Impacto: una carga con un nombre común puede impedir que otra identidad
  guarde un archivo con ese mismo nombre en el directorio compartido; el modo
  exclusivo evita sobrescrituras, pero convierte la colisión en interferencia
  de disponibilidad entre usuarios.
- Prioridad propuesta: baja; el efecto está limitado a nombres coincidentes y
  no se confirmó que los archivos deban ser aislados por propietario.
- Contrato potencialmente afectado: propiedad/aislamiento de archivos en
  `POST /api/requirements` y respuesta `409` por nombre existente.
- Cómo validarlo: con un directorio vacío, cargar el mismo nombre primero con
  un token de una identidad y luego con otra; confirmar el comportamiento
  esperado para ambas identidades y ejecutar `python tools/lab.py test api`.

No se ejecutaron pruebas durante este discovery. Los cuatro hallazgos quedan
pendientes de revisión humana; no se crearon issues ni se modificó código.
