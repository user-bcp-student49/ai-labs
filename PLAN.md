# Plan de corrección

## API

Alcance aprobado: H-API-01 a H-API-05. H-API-03 se implementó previamente;
en esta iteración se implementaron H-API-01, H-API-02, H-API-04 y H-API-05.
Los cuatro figuran `Resuelto` en HALLAZGOS.md. La compatibilidad con el emisor
JWT real aún requiere coordinación externa. Los contratos de
`docs/ENDPOINTS.md` no están disponibles; se preservaron los endpoints, códigos
de éxito y formas de respuesta observados, con cambios de seguridad explícitos
para propietarios discordantes y cargas rechazadas.

### Decisiones de diseño

Estas decisiones se toman para concretar la propuesta aprobada; no afirman
que el emisor externo ya las soporte ni que la integración haya sido probada.

- **H-API-01 — JWT:** elegir RS256 y validación mediante JWKS. La API exigirá
  `sub`, `role`, `iss`, `aud` y `exp`; `iss` y `aud` esperados, junto con la URL
  JWKS, se configurarán externamente (`JWT_ISSUER`, `JWT_AUDIENCE`,
  `JWT_JWKS_URL`). JWKS remotos requieren HTTPS; solo localhost se permite por
  HTTP para pruebas locales y sin credenciales en la URL. Se fijará RS256 en el verificador, sin aceptar el
  algoritmo indicado libremente por el token ni mantener el formato Base64 legado. Se
  justifica una dependencia JWT mantenida con soporte criptográfico porque el
  proyecto no declara una biblioteca para validar tokens; se agregó
  `PyJWT[crypto]==2.15.1`. JWKS facilita rotación de claves sin
  desplegar una clave privada en la API. **Pendiente externo:** confirmar que
  el emisor publica claves RS256/JWKS y acordar los valores reales de emisor y
  audiencia. Se usarán datos y claves efímeras solo en pruebas.
- **H-API-02 — `owner` discordante:** rechazar con HTTP 403 cuando el
  `owner` explícito de query o body no coincide con `identity["username"]`.
  Si se omite, la identidad autenticada sigue siendo el propietario. Se elige
  rechazo explícito en vez de ignorar silenciosamente el campo para que el
  cliente detecte entradas incompatibles; nunca se consultarán ni crearán
  tareas para otro propietario.
- **H-API-04 — carga:** permitir solo `.txt` y `.md`, sin distinguir
  mayúsculas, con un tamaño máximo de 1 MiB (1,048,576 bytes). Normalizar el
  nombre a su basename eliminando separadores de ruta Windows y POSIX; rechazar
  nombres vacíos o sin esas extensiones. Rechazar colisiones de nombre para no
  sobrescribir un archivo existente. El límite es deliberadamente acotado y
  suficiente para documentos de requisitos de texto; extensiones binarias y
  archivos mayores quedan fuera del uso previsto.
- **H-API-05 — separación:** mantener `main.py` como fábrica de aplicación;
  ubicar routers en `api/app/routes.py`, modelos Pydantic en
  `api/app/schemas.py`, reglas en `api/app/services.py` y persistencia SQLite
  en `api/app/repository.py`. La seguridad JWT quedará en
  `api/app/security.py`. Esta separación mantiene cada función en una
  responsabilidad, evita SQL en rutas y permite preservar contratos con
  pruebas por endpoint.
- **Contratos:** dado que `docs/ENDPOINTS.md` no existe, se preservarán rutas,
  métodos, códigos y formas JSON observadas. Los nuevos 403 para propietario
  discordante y errores controlados para cargas rechazadas son cambios
  intencionales de seguridad, no cambios a los resultados exitosos.

### H-API-01 — Token Base64 con secreto estático embebido y sin firma

- **Problema:** `legacy_identity` decodifica contenido Base64 y compara un
  secreto estático, sin verificar firma, emisor ni audiencia
  (`api/app/main.py:14, api/app/main.py:17-24`).
- **Cambio propuesto:** sustituir la confianza en Base64 por verificación de
  JWT firmado, validando firma, emisor, audiencia y expiración. Mantener el
  mismo requisito de autenticación en todas las rutas protegidas y devolver
  un error genérico para tokens inválidos, sin exponer excepciones. Usar
  configuración externa para parámetros/secretos y valores aislados de prueba;
  no incluir secretos reales ni mantener un mecanismo alternativo que acepte
  tokens sin verificar.
- **Archivos a tocar:** `api/app/main.py`, `api/app/security.py`,
  `api/requirements.txt` para una biblioteca de validación JWT con soporte
  criptográfico, y `api/tests/test_api.py`.
- **Caracterización antes de tocar implementación:** ampliar pruebas con token
  válido que permita una petición protegida, token malformado y token expirado;
  registrar los códigos HTTP y la forma de respuesta observados. Ejecutarlas
  antes de cambiar autenticación y guardar el resultado real. Estas pruebas
  caracterizan el comportamiento actual, no certifican una firma JWT.
- **Validación tras el cambio:** probar JWT válido firmado con clave de prueba,
  firma alterada, emisor/audiencia incorrectos, expiración y ausencia de
  credenciales; comprobar que los inválidos reciben error genérico y que los
  endpoints y respuestas de éxito no cambian.
- **Dependencia externa / pendiente:** la selección RS256/JWKS está tomada,
  pero falta confirmar con el emisor que publica JWKS compatible y los valores
  exactos de issuer/audience. Sin esa coordinación no se puede validar la
  integración real. Las pruebas usan claves generadas para test y un JWKS
  local; no se inspeccionó ni cambió otro componente.
- **Resultado:** `api/app/security.py` verifica RS256, firma y los claims
  requeridos; errores de token devuelven 401 genérico y la configuración
  ausente, una URL remota sin HTTPS o el JWKS inaccesible se informa como 503.
  Se rechazan algoritmo distinto, firma inválida, issuer/audience incorrectos,
  expiración y el token Base64 legado.

### H-API-02 — El cliente puede elegir el owner de consultas y tareas

- **Problema:** `GET /api/tasks` y `GET /api/summary` aceptan `owner` del
  cliente; `POST /api/tasks` permite elegirlo en el cuerpo
  (`api/app/main.py:68-71, api/app/main.py:78-85, api/app/main.py:91-93`).
- **Cambio propuesto:** derivar siempre el propietario autorizado de la
  identidad autenticada. Las consultas y las nuevas tareas deben estar
  vinculadas a esa identidad; nunca usar un `owner` enviado por el cliente
  para acceder a datos de otra identidad. Rechazar con `403` cualquier
  `owner` explícito discordante; si está omitido, usar la identidad. Conservar
  las rutas y formas JSON para las peticiones aceptadas.
- **Archivos a tocar:** `api/app/main.py`; `api/tests/test_api.py`; el módulo
  de servicio/repositorio correspondiente si se realiza junto con H-API-05.
- **Caracterización antes de tocar implementación:** probar listados y resumen
  para la identidad autenticada sin parámetro `owner`, confirmar sus formas y
  valores; probar la creación ordinaria y confirmar que el propietario por
  defecto procede del token. Añadir un caso que documente el efecto actual de
  un `owner` distinto sin convertir el acceso cruzado en comportamiento
  aprobado.
- **Validación tras el cambio:** verificar que consultas y creación no revelan
  ni asignan datos de otro propietario, que la identidad autenticada queda
  asociada a la tarea y que se conserva la forma de las respuestas. Verificar
  que owner discordante en query o body devuelve `403`.
- **Contrato:** no existe contrato acordado en `docs/ENDPOINTS.md`. Mantener
  rutas, métodos y estructuras de éxito observadas. El 403 para propietario
  discordante es la política de seguridad elegida; el acceso cruzado actual
  no se preserva.
- **Resultado:** query discordante para lista/resumen y body discordante para
  creación devuelven 403; sin `owner`, la respuesta mantiene el sujeto del JWT.

### H-API-03 — Filtros e inserts SQL concatenan valores de entrada

- **Problema:** valores de filtros y campos de tarea se concatenan en
  sentencias SQL (`api/app/main.py:70-71, api/app/main.py:83-85,
  api/app/main.py:92-93`); el `SELECT` posterior a la inserción también
  concatena `lastrowid` (`api/app/main.py:87`).
- **Cambio propuesto:** cambiar todas las consultas afectadas a parámetros
  enlazados de SQLite, incluidos filtros, inserciones y selección de la fila
  recién creada. No construir SQL con datos recibidos. Coordinar el filtro de
  propietario con H-API-02 para que solo consulte la identidad autorizada.
- **Archivos a tocar:** `api/app/main.py`; `api/tests/test_api.py`; el
  repositorio SQLite nuevo si se implementa H-API-05 en la misma iteración.
- **Caracterización antes de tocar implementación:** añadir pruebas con una
  tarea de datos ordinarios y valores textuales que incluyan comillas en los
  campos aceptados; registrar los códigos y formas de respuesta actuales para
  list, create y summary. Ejecutar antes de editar consultas. No escribir una
  prueba que dependa de alterar SQL como contrato.
- **Validación tras el cambio:** confirmar que valores con comillas se tratan
  como datos literales, las tareas se crean y recuperan correctamente, los
  filtros mantienen sus respuestas esperadas y los errores no exponen SQL.
  Inspeccionar que cada valor variable se entrega como parámetro enlazado.
- **Resultado de implementación H-API-03:** parametrizados los filtros de
  `list_tasks` y `summary`, los valores del `INSERT` de `create_task` y el
  `SELECT` de la tarea insertada (`api/app/main.py:68-107`). Las pruebas con
  comillas fallaban antes del cambio con HTTP 500 y pasan después. La
  caracterización ordinaria también pasa después sin cambios en los endpoints
  ni en las formas JSON.

### H-API-04 — La carga conserva directamente el nombre proporcionado y lee el archivo completo

- **Problema:** `upload_requirement` combina el nombre de cliente con el
  directorio, lee el archivo completo en memoria y lo escribe sin comprobar
  extensión ni tamaño (`api/app/main.py:108-112`).
- **Cambio propuesto:** normalizar y validar el nombre antes de construir la
  ruta; aceptar `.txt` y `.md` (sin distinguir mayúsculas) y limitar el
  archivo a 1 MiB mientras se lee, antes de persistir. Rechazar nombres vacíos
  y colisiones, y no sobrescribir archivos existentes. Usar constantes con
  nombre, no valores mágicos. Conservar `POST /api/requirements`, el
  multipart requerido, el código `201` y la forma de respuesta para cargas
  aceptadas. Responder con error controlado para nombre, extensión o tamaño no
  permitidos.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py` y, si se
  implementa H-API-05 en la misma iteración, los módulos de rutas/servicio.
- **Caracterización antes de tocar implementación:** ampliar el test de carga
  existente con un archivo válido y comprobar código, claves de respuesta,
  nombre devuelto, tamaño y archivo almacenado. Registrar el comportamiento
  para cargas ordinarias antes de cambiar la ruta.
- **Validación tras el cambio:** comprobar `.txt` y `.md` válidos, extensión
  no permitida, basename normalizado, nombre vacío, colisión y cargas de
  tamaño exactamente en el límite y por encima de 1 MiB; verificar que
  rechazos no crean archivos fuera del directorio ni conservan contenido
  parcial.
- **Resultado:** `.txt` y `.md` aceptados, basename normalizado, colisión
  rechazada sin sobrescritura, extensión no permitida 400, tamaño excesivo
  413 y nombre multipart vacío 422 por validación de FastAPI. Se probaron
  1 MiB exactos y 1 byte por encima. La revisión local detectó que un nombre
  drive-relative de Windows podía resolver fuera del directorio configurado;
  se añadió rechazo explícito y verificación de contención del destino
  resuelto. La regresión cubre `C:outside.md`.

### H-API-05 — Rutas, persistencia, reglas y serialización están concentradas en un módulo

- **Problema:** inicialización de SQLite, serialización, consultas, reglas y
  rutas se concentran en `create_app` y funciones locales
  (`api/app/main.py:29-60, api/app/main.py:67-112`).
- **Cambio propuesto:** separar incrementalmente las responsabilidades en
  rutas FastAPI, servicios de reglas y repositorio SQLite parametrizado. Usar
  modelos Pydantic para request/response conforme a las buenas prácticas de
  API, conservando nombres de campos JSON (incluido `createdAt`), métodos,
  rutas y códigos observados. Cada función debe tener una responsabilidad;
  extraer lógica repetida, preferir retornos tempranos y nombrar límites y
  valores constantes. La refactorización no debe adelantarse a las pruebas de
  caracterización.
- **Archivos a tocar:** `api/app/main.py`, `api/app/routes.py`,
  `api/app/services.py`, `api/app/repository.py`, `api/app/schemas.py`,
  `api/app/security.py` para H-API-01 y `api/tests/test_api.py`. No cambiar
  código de otros componentes.
- **Caracterización antes de tocar implementación:** completar y ejecutar
  pruebas de respuestas existentes de `GET /api/tasks`, `POST /api/tasks`,
  `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`,
  usando dependencias aisladas de SQLite y carga. Registrar status codes,
  campos y valores por defecto observados; incluir autenticación válida e
  inválida. Ejecutar el conjunto antes de mover lógica.
- **Validación tras el cambio:** repetir la caracterización y comprobar que las
  rutas públicas y formatos de éxito se mantienen. Añadir validación de los
  modelos para entradas inválidas y revisar consultas parametrizadas,
  autorización y errores genéricos en las capas correspondientes.
- **Resultado:** `main.py` conserva la fábrica y vida de la conexión; routers,
  esquemas Pydantic, servicios y repositorio se separaron en módulos propios.
  Las pruebas mantienen las formas `createdAt`, `byStatus`,
  `highPriorityOpen`, `fileName` y `storedAt`.
- **Alcance relacionado:** H-API-01 a H-API-04 tienen cambios de seguridad
  propios; separarlos o integrarlos en cambios pequeños revisables. La
  separación no debe ocultar esos cambios ni servir para preservar los defectos.

## Ejecución y evidencia

- **Pruebas propuestas:** ejecutar `pytest` desde `api/` para las pruebas
  focalizadas; posteriormente, ejecutar `python tools/lab.py test api` desde
  la raíz conforme a README.md, si el entorno del componente está preparado.
- **Estado actual:** se ejecutaron pruebas de caracterización antes de los
  cambios y la suite con cobertura después. `docs/TESTING.md` aún no existe y
  no se creó en este paso.
- **Cobertura:** medir la cobertura del código modificado y perseguir la meta
  de 85% indicada para API; no reducir el gate configurado.
- **Revisión:** HALLAZGOS.md registra H-API-01/02/03/04/05 como `Resuelto`.
  La integración con el emisor JWT real sigue pendiente; no se registra como
  verificada.

### Ejecuciones registradas

| Componente | IDs | Comando / fase | Resultado |
|---|---|---|---|
| api | H-API-03 | `Set-Location api; pytest` (baseline inicial) | Falló durante colección: `ModuleNotFoundError: No module named 'app'`; el ejecutable global no configuró la ruta de importación del componente. |
| api | H-API-03 | `Set-Location api; python -m pytest` (baseline inicial) | Falló durante colección: falta `urllib3` en el intérprete global. |
| api | H-API-03 | `python tools/lab.py setup api` | Correcto; se preparó el entorno virtual documentado y sus dependencias ya estaban instaladas. |
| api | H-API-03 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest` (baseline antes de añadir pruebas) | 4 pruebas pasaron; 11 advertencias deprecadas. |
| api | H-API-03 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_create_task_preserves_quotes_in_text_fields tests\test_api.py::test_owner_filters_treat_quotes_as_literal_values` (antes del cambio SQL) | 2 pruebas fallaron como se esperaba: las rutas devolvieron HTTP 500 ante valores con comillas. |
| api | H-API-03 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_create_task_preserves_quotes_in_text_fields tests\test_api.py::test_owner_filters_treat_quotes_as_literal_values` (después del cambio SQL) | 2 pruebas pasaron. |
| api | H-API-03 | `python tools/lab.py test api` (después del cambio SQL) | 6 pruebas pasaron; cobertura total 90.91% (91% para `app\main.py`); gate configurado de 85% aprobado. |
| api | H-API-01/02/04/05 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest` (caracterización antes de cambiar implementación) | 11 pruebas pasaron; registraron formatos de endpoints, carga, health y acceso a owner distinto de la identidad. |
| api | H-API-01 | `python tools/lab.py setup api` | Correcto; instaló PyJWT 2.15.1, cryptography 50.0.2 y dependencias requeridas. |
| api | H-API-01/02/04/05 | `python tools/lab.py test api` (implementación, primera validación) | 23 pruebas pasaron; cobertura total 96.67%, módulos modificados entre 94% y 100%; gate de 85% aprobado. |
| api | H-API-01/02/04/05 | `Set-Location api; .\.venv\Scripts\python.exe -m compileall -q app tests` | Correcto; todos los módulos y pruebas compilaron. |
| api | H-API-01/02/04/05 | `python tools/lab.py test api` (validación final tras añadir casos de algoritmo, token legado y transporte JWKS) | 26 pruebas pasaron; cobertura total 95.39%, módulos modificados entre 92% y 100%; gate de 85% aprobado. Una advertencia de deprecación externa de Starlette/AnyIO permanece. |
| api | H-API-01/02/04/05 | `python tools/lab.py test api` (validación final tras rechazar credenciales en URL JWKS de loopback) | 26 pruebas pasaron; cobertura total 95.39%, con mínimo de 92% en módulos modificados; gate de 85% aprobado. Permanece una advertencia externa de deprecación de Starlette/AnyIO. |
| api | H-API-04 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_rejects_drive_relative_upload_filename -q` (antes del arreglo) | Falló como se esperaba: `C:outside.md` recibió HTTP 201 en lugar de 400. La prueba usó un directorio temporal como cwd. |
| api | H-API-04 | `Set-Location api; .\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_rejects_drive_relative_upload_filename -q` (después del arreglo) | 1 prueba pasó; el nombre drive-relative se rechazó y no se creó ningún archivo fuera ni dentro del directorio de cargas. |
| api | H-API-04 | `python tools/lab.py test api` (validación final tras rechazar rutas drive-relative y comprobar contención del destino) | 27 pruebas pasaron; cobertura total 94.90%, módulos de aplicación modificados entre 92% y 95%; gate de 85% aprobado. Permanece una advertencia externa de deprecación de Starlette/AnyIO. |

## Item: H-API-06 — Manejo amplio de excepciones en consulta de salud

- **Hallazgo de HALLAZGOS.md:** H-API-06, componente `api`, estado actual
  `Aprobado`, severidad media. `BackendHealthService.get_status` captura
  cualquier `Exception` y devuelve `str(error)` en el campo `body`
  (`api/app/services.py:103-123`). Esto expone detalles del error upstream y
  convierte fallos inesperados en una respuesta HTTP `200` con forma de éxito.
- **Alcance de este item:** cambiar únicamente el manejo de errores de
  `GET /api/backend-health`. No modificar JWT, autorización, otros endpoints,
  URLs ni la lógica de respuestas HTTP exitosas del servicio consultado.
- **Cambio propuesto:** manejar explícitamente los errores de transporte de
  urllib3 (`urllib3.exceptions.HTTPError`) y transformarlos en HTTP `502 Bad
  Gateway` con el cuerpo genérico
  `{"detail":"Authentication service is unavailable"}`. Registrar en el log
  del servidor una advertencia controlada con la clase de excepción, sin
  enviar el mensaje crudo al cliente. Eliminar el `except Exception` que
  actualmente devuelve un éxito aparente; errores inesperados, como fallos de
  decodificación, deben continuar hacia el manejo genérico HTTP `500` del
  servidor y no convertirse en `status: 0`.
- **Contrato protegido / cambio intencional:** conservar `GET
  /api/backend-health`, la autenticación, y para respuestas upstream normales
  el HTTP `200` de la API con `requestedBy`, `status` upstream y `body`
  upstream, incluso si el propio upstream responde con un status HTTP de
  error. Cambia de forma intencional el caso de fallo de transporte: deja de
  ser HTTP `200` con `status: 0` y texto arbitrario, y pasa a `502` genérico.
  Actualizar `docs/ENDPOINTS.md` y `docs/TESTING.md` durante la implementación
  para reflejar este cambio aprobado; no cambiar ahora esos contratos.
- **Archivos a tocar:** `api/app/services.py` para el manejo específico y
  logging; `api/tests/test_api.py` para caracterización y regresiones;
  `docs/ENDPOINTS.md` para documentar el error `502` y retirar el comportamiento
  de éxito aparente; `docs/TESTING.md` para registrar casos/comandos/resultados;
  `HALLAZGOS.md` para marcar el estado solo después de validación.
- **Prueba antes de modificar implementación:**
  1. Ejecutar el test existente
     `test_backend_health_reports_upstream_exception_in_success_response` y
     registrar el baseline real: actualmente espera HTTP `200`, `status: 0`
     y el texto de la excepción.
  2. Añadir antes del cambio una prueba de transporte que espere HTTP `502`,
     cuerpo exacto `{"detail":"Authentication service is unavailable"}` y que
     un texto simulado sensible de la excepción no aparezca en la respuesta.
     Verificar además que se registra la advertencia controlada. Ejecutarla
     para confirmar que falla frente a la implementación actual; no adaptar la
     expectativa para hacer pasar el comportamiento inseguro.
  3. Proteger el camino feliz existente (`test_backend_health_response`) y
     agregar/confirmar un caso de respuesta upstream `503`, que debe seguir
     siendo HTTP `200` de la API con `status: 503` y cuerpo upstream intacto.
     Añadir un caso de excepción no perteneciente a urllib3 para confirmar que
     no se convierte en `status: 0` ni expone su mensaje al cliente.
- **Validación posterior propuesta:** repetir los casos anteriores, ejecutar
  `python tools/lab.py test api` desde la raíz y calcular/reportar cobertura
  del código modificado con numerador/denominador, además del resultado global.
  Mantener el gate existente de 85%; registrar cada ejecución con componente
  `api` e ID H-API-06. No declarar el item resuelto si falla cualquiera de
  esas verificaciones.
- **Riesgos y decisión:** el `502` cambia el status HTTP de la falla de
  transporte que antes se presentaba como `200`; consumidores que dependan de
  `status: 0` requieren adaptación. La decisión prioriza distinguir fallo de
  upstream de respuesta exitosa y no devolver excepciones crudas. Las respuestas
  HTTP de error que sí devuelve el upstream no son fallos de transporte y
  conservan su status/body reenviados.
