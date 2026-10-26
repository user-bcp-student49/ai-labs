# Contratos HTTP consumidos

Este documento describe el contrato **observado en el cliente web**. No hay
un contrato acordado de backend registrado en este repositorio; los estados y
formas de respuesta que el servidor garantiza deben confirmarse con sus
responsables. Los ejemplos usan credenciales ficticias locales documentadas
para el laboratorio.

## web — Login

### 1. Quién lo llama

`LoginComponent.login()` delega la petición en `AuthService.login(username,
password)`. La URL base se lee de `web/src/environments/environment.ts`.
Evidencia: `web/src/app/login/login.component.ts:40-67`,
`web/src/app/services/auth.service.ts:10-23`,
`web/src/environments/environment.ts:1-4`.

### 2. Qué envía

**Método y URL:** `POST http://localhost:8080/auth/login`.

**Headers:** el servicio no configura headers propios. Envía un objeto JSON a
Axios, que serializa el cuerpo como JSON. No se añade un token de autorización
al login.

| Ubicación | Campo | Tipo observado | Valor de ejemplo |
|---|---|---|---|
| Body JSON | `username` | string | `"student"` |
| Body JSON | `password` | string | `"Workshop123!"` |
| Body JSON | `client` | string constante | `"angular-workshop"` |

El timeout configurado para la petición es **5000 ms**.

```http
POST http://localhost:8080/auth/login
Content-Type: application/json

{
  "username": "student",
  "password": "Workshop123!",
  "client": "angular-workshop"
}
```

Evidencia de la forma del cuerpo y timeout:
`web/src/app/services/auth.service.ts:6-22`; la prueba de contrato está en
`web/src/app/services/auth.service.spec.ts:20-30`. El usuario de ejemplo es
ficticio y está descrito en `README.md`.

### 3. Qué espera recibir en éxito

El cliente trata cualquier respuesta HTTP que Axios considere exitosa (por
defecto, un estado 2xx) como respuesta utilizable. No comprueba un código
específico; **200 es el estado convencional del ejemplo**, no una garantía
verificada del backend.

| Campo de respuesta | Tipo declarado | Uso en la UI |
|---|---|---|
| `token` | string requerido por `LoginResponse` | Si falta o es falsy, muestra “El backend respondió sin token.” y no navega. Si existe, lo guarda en sesión. |
| `user` | objeto `AuthUser` | Se guarda en sesión junto al token y se usa después para el nombre y el parámetro `owner`. El tipo declara `username` obligatorio y `displayName` y `role` opcionales. |
| `expiresIn` | number opcional | El cliente no lo consulta ni aplica una expiración basada en este campo. |

```http
HTTP/1.1 200
Content-Type: application/json

{
  "token": "fake-token",
  "user": {
    "username": "student",
    "displayName": "Workshop Student",
    "role": "STUDENT"
  },
  "expiresIn": 3600
}
```

El nombre y rol son valores de ejemplo; la aplicación no exige esos valores
concretos. El modelo declara la forma en
`web/src/app/models/auth.models.ts:1-17`; el servicio retorna `response.data`
en `web/src/app/services/auth.service.ts:17-23`; la sesión y navegación se
realizan en `web/src/app/login/login.component.ts:54-61`.

### 4. Cómo reacciona ante errores o respuesta inesperada

| Caso | Reacción observada |
|---|---|
| Campos vacíos | Antes de HTTP, muestra “Ingrese un usuario.” o “Ingrese una contraseña.” y retorna. |
| Credenciales inválidas / HTTP no 2xx | Axios rechaza la petición. El componente muestra `No se pudo autenticar a <username>. <mensaje>`, donde el normalizador prefiere `response.data.message`, luego `response.data.detail`, luego el texto del error o “Error desconocido”. |
| Timeout | La llamada configura 5000 ms. Si Axios rechaza por timeout, se muestra el texto de error de Axios en el mensaje de login y se registra el error en consola; `busy` vuelve a `false`. |
| Respuesta exitosa sin `token` | Muestra “El backend respondió sin token.”; no guarda sesión ni navega al dashboard. |
| Respuesta exitosa con `token` pero usuario ausente o inválido | El tipo declara `user`, pero el componente no valida su forma antes de guardarlo. El dashboard puede fallar al leer/validar el usuario de sesión y mostrar el mensaje derivado de ese error. Esta forma de respuesta no se presenta como válida. |
| Error desconocido | Muestra el fallback “Error desconocido” si no hay mensaje utilizable y termina el estado ocupado. |

Evidencia: validación, respuesta, catch y `finally` en
`web/src/app/login/login.component.ts:40-68`; normalización en
`web/src/app/utils/error-message.ts:3-17`; validación de usuario de sesión en
`web/src/app/services/session.service.ts:33-48`.

### 5. Notas de seguridad

- El token y usuario se guardan en `sessionStorage`; las claves antiguas de
  token/usuario en `localStorage` se eliminan al construir `SessionService`.
  Las preferencias permanecen en `localStorage`.
- `sessionStorage` limita la persistencia de la sesión a la pestaña, pero es
  accesible para JavaScript del mismo origen; no equivale a una cookie
  `HttpOnly`.
- El mensaje de error se presenta con interpolación de texto, no con
  `[innerHTML]`: `web/src/app/login/login.component.html:39`.
- Los textos `message`/`detail` del backend se presentan sin filtrado
  semántico. Si contienen detalles internos, la UI podría mostrarlos. El
  cliente no valida el token criptográficamente; eso corresponde al servidor.

Evidencia de sesión: `web/src/app/services/session.service.ts:27-73`.

## web — Consulta de tareas

### 1. Quién lo llama

`DashboardComponent.ngOnInit()` obtiene token y usuario de `SessionService` y
llama a `TasksService.getTasks(owner, token)`. El servicio compone la URL y
realiza la petición.

Evidencia: `web/src/app/dashboard/dashboard.component.ts:45-68`,
`web/src/app/services/session.service.ts:33-48`,
`web/src/app/services/tasks.service.ts:7-16`,
`web/src/environments/environment.ts:1-4`.

### 2. Qué envía

**Método y URL:** `GET http://localhost:8000/api/tasks?owner=<username>`.
El `owner` se codifica como parámetro de URL.

| Ubicación | Campo | Tipo observado | Ejemplo |
|---|---|---|---|
| Query param | `owner` | string | `student` |
| Header | `Authorization` | string con esquema Bearer | `Bearer fake-token` |

No se envía body.

```http
GET http://localhost:8000/api/tasks?owner=student
Authorization: Bearer fake-token
```

Evidencia de URL, query y header:
`web/src/app/services/tasks.service.ts:8-14`; la prueba de contrato, incluido
el encoding de un owner con caracteres reservados, está en
`web/src/app/services/tasks.service.spec.ts:20-30`.

### 3. Qué espera recibir en éxito

El cliente acepta la resolución normal de Axios (estado HTTP 2xx; normalmente
200, sin comprobación propia de código) y espera que `response.data` sea un
array de tareas. Filtra los elementos con `status === "ARCHIVED"`, calcula
`label` y ordena por prioridad descendente antes de presentarlos.

| Campo de tarea | Tipo declarado | Uso en la UI |
|---|---|---|
| `id` | number o string, opcional | No se usa en el procesamiento observado. |
| `title` | string, opcional | Título de la tarjeta. |
| `description` | string, opcional | Descripción de la tarjeta. |
| `status` | string, opcional | Se filtra `ARCHIVED`; se convierte a etiqueta visible y clase CSS. |
| `priority` | number o string, opcional | Orden descendente cuando ambos elementos tienen prioridad. |
| `owner` | string, opcional | Se usa para generar la etiqueta de tarea. |
| `label` | string, opcional | El cliente lo calcula a partir de prioridad y owner antes de mostrarlo. |

```http
HTTP/1.1 200
Content-Type: application/json

[
  {
    "id": 1,
    "title": "Actualizar flujo de login",
    "description": "Revisar el estado de autenticación",
    "status": "TODO",
    "priority": 3,
    "owner": "student"
  }
]
```

El ejemplo usa valores ficticios y campos presentes en el tipo `Task`; el tipo
no establece que todos sean obligatorios. Evidencia:
`web/src/app/models/task.models.ts:1-11`,
`web/src/app/dashboard/dashboard.component.ts:70-76`,
`web/src/app/dashboard/dashboard.component.html:20-27`.

### 4. Cómo reacciona ante errores o respuesta inesperada

| Caso | Reacción observada |
|---|---|
| No hay token en sesión | No realiza la petición y navega a `/login`. |
| Token inválido / HTTP 401 u otro estado no 2xx | Axios rechaza la llamada; el dashboard muestra el `message` o `detail` de la respuesta si existe, en otro caso el texto del error. Deja de cargar. No borra la sesión ni redirige automáticamente a login. |
| Error de red o timeout | No se configura timeout específico para tareas. Cuando Axios rechaza por red u otro error, la UI muestra su texto; si no es un `Error` utilizable muestra “No se pudo cargar el dashboard”. El estado loading pasa a falso. |
| Respuesta exitosa con `data` que no es array | El procesamiento con `.filter()` falla; el `catch` captura el error y muestra su texto, después termina el estado loading. |
| Array vacío | No es error; aparece “No hay tareas para mostrar todavía.” |

Evidencia de sesión, request y catch:
`web/src/app/dashboard/dashboard.component.ts:45-68`;
`web/src/app/dashboard/dashboard.component.html:13-27`;
normalización de errores en `web/src/app/utils/error-message.ts:3-17`.
Axios usa su comportamiento de timeout predeterminado porque este servicio no
provee una opción `timeout`.

### 5. Notas de seguridad

- El token se recupera del `SessionService` y se envía como Bearer; el frontend
  no verifica firma, expiración o permisos del token.
- `owner` proviene del usuario almacenado en la sesión del navegador y se envía
  como query param. Este cliente no prueba que el backend ate ese valor a la
  identidad autenticada; la autorización efectiva queda por verificar con el
  contrato y pruebas del servidor.
- Los errores se insertan en la plantilla mediante interpolación de texto
  (`web/src/app/dashboard/dashboard.component.html:18`), no como HTML. El
  contenido `message`/`detail` no se filtra para ocultar posibles detalles
  internos.
- El token sigue siendo accesible a JavaScript del mismo origen mientras está
  en `sessionStorage`; no se almacena ningún secreto nuevo en el bundle.

## Contrato acordado y preguntas abiertas

- **Contrato acordado:** no hay confirmación de contrato de backend registrada
  en los documentos consultados. Este archivo documenta el comportamiento y
  tipos observados del cliente web; no atribuye garantías de estado o schema al
  servidor.
- ¿Qué código de éxito y schema garantiza cada backend, en particular si
  `user` siempre acompaña al token y si tareas siempre se devuelven como array?
- ¿Qué valores de `message`/`detail` puede devolver el backend para errores de
  autenticación, autorización y servidor, y cuáles son aptos para mostrar al
  usuario?
- ¿El backend valida que el `owner` de la query coincida con la identidad del
  token? ¿Cómo debe actuar el cliente ante un token inválido: conservar la
  sesión y mostrar error o limpiarla y redirigir?
