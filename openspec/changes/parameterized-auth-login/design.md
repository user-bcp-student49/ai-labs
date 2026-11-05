# Design

## Context

Motivación y alcance: ver `proposal.md` (issue #23, `H-AUTH-01`). Requisitos: ver `specs/auth-login/spec.md`. Este documento solo cubre el cómo.

Estado actual observado en `auth/` (Quarkus 3.27, Java 21, SQLite vía `sqlite-jdbc`):

- `AuthResource.login` valida el cuerpo y llama a `LegacyDatabase.findByCredentials(username, password)`. Un resultado `null` produce `401`; en caso contrario crea el token con `LegacyTokenUtil` y responde `200`.
- `LegacyDatabase.findByCredentials` construye el SQL concatenando `username` y `password` dentro de un `Statement` (`LegacyDatabase.java:32`). Cualquier excepción se imprime y el método devuelve `null`, es decir, termina en `401`.
- Las contraseñas están en texto plano en `legacy_users`; los usuarios de prueba `student` y `trainer` se siembran en `initialize()`.
- `AuthResourceTest` solo cubre el login exitoso de `student`.
- `docs/ENDPOINTS.md` no documenta `/auth/login`, por lo que el baseline del contrato proviene del código y de la prueba existente.

Precedencia SQL relevante para las pruebas (con el código actual):

| Entrada | Condición resultante | Efecto actual |
|---|---|---|
| `username=student`, `password=' OR '1'='1` | `username='student' AND password='' OR '1'='1'` → verdadero | Login indebido (200) |
| `username=' OR '1'='1`, `password=<cualquiera>` | `username='' OR '1'='1' AND password='x'` → falso | Ya responde 401 |
| `username=' OR '1'='1`, `password=' OR '1'='1` | `... OR '1'='1' AND password='' OR '1'='1'` → verdadero | Login indebido (200) |

## Goals / Non-Goals

**Goals:**

- Que el valor de `username` y `password` nunca forme parte de la estructura de la consulta SQL de credenciales.
- Que los escenarios de `specs/auth-login/spec.md` se cumplan y estén cubiertos por pruebas automáticas.
- Un cambio mínimo, revisable y reversible en una sola capa (acceso a datos).

**Non-Goals:**

- Rediseñar `AuthResource` en capas, extraer servicios o cambiar la estructura de paquetes (refactor de clean code queda para cambios separados).
- Hashear contraseñas, cambiar el esquema de `legacy_users` o los usuarios sembrados.
- Cambiar `LegacyTokenUtil` (secreto embebido, formato del token, expiración).
- Eliminar el campo `debug`, el eco del usuario en el mensaje `401` o la exposición de `exception` en el `500`. Son hallazgos distintos; se conservan para no alterar el contrato.
- Añadir dependencias, rate limiting o bloqueo de cuentas.

## Contratos protegidos

Deben permanecer idénticos tras el cambio (los verifican las pruebas de caracterización):

| Contrato | Comportamiento protegido |
|---|---|
| Ruta y método | `POST /auth/login`, JSON de entrada y salida |
| Éxito | `200` con `token` (no vacío), `expiresIn = 3600`, `user.username`, `user.displayName` (escapado HTML), `user.role` y el campo `debug` existente |
| Validación | Cuerpo nulo, `username` ausente/vacío o `password` ausente/vacío → `400` con `message` actual |
| Credenciales inválidas | Usuario o contraseña incorrectos → `401` con `message` y sin `token` |
| Fallo de base de datos | Error al consultar → resultado nulo → `401` (comportamiento actual de `findByCredentials`) |
| Datos | Mismo esquema, mismos usuarios sembrados, misma `AUTH_DB_URL` |
| Otros componentes | `api/` y `web/` no se modifican |

## Componentes afectados

| Componente | Cambio |
|---|---|
| `auth/.../LegacyDatabase.java` (`findByCredentials`) | Única modificación de código funcional: consulta con parámetros enlazados |
| `auth/.../AuthResourceTest.java` | Nuevas pruebas de caracterización y de inyección |
| `AuthResource`, `LegacyTokenUtil`, `UserRecord`, `LoginRequest`, `pom.xml` | Sin cambios |

## Decisions

### D1. Consulta parametrizada con `PreparedStatement` en `findByCredentials`

Se sustituye la concatenación por una sentencia con marcadores para `username` y `password`, manteniendo firma, tipo de retorno y manejo de errores actuales. El issue exige explícitamente este mecanismo en sus criterios de aceptación.

Alternativas consideradas:

- **Escapar o sanear las comillas manualmente**: rechazada; es frágil, dependiente del dialecto y deja la estructura del SQL influida por la entrada.
- **Lista negra de patrones (`OR`, `'`, `--`) en el recurso**: rechazada; bloquea contraseñas legítimas con esos caracteres y se elude con variantes.
- **Panache/JPA u otro ORM**: rechazada; añade dependencias y rediseña la persistencia, fuera de alcance.
- **Buscar por `username` y comparar la contraseña en Java**: rechazada; cambia el modelo de acceso y se acerca al rediseño de credenciales (hashing), que es otro hallazgo.

### D2. Mantener sin cambios el manejo de errores y la firma de `findByCredentials`

El contrato protegido incluye que un fallo de base de datos termina en `401`. Cambiarlo a `500` sería un cambio de comportamiento no solicitado.

Alternativa considerada: propagar la excepción. Rechazada por alterar el contrato; puede evaluarse en un cambio aparte.

### D3. Pruebas a nivel HTTP con el stack existente

Se amplía `AuthResourceTest` (`@QuarkusTest` + RestAssured), ya presente en el proyecto, sin dependencias nuevas. Se prueba el comportamiento observable y no la implementación; así las pruebas sobreviven a refactors posteriores.

## Pruebas de caracterización (antes de tocar `LegacyDatabase`)

Deben escribirse y pasar en verde contra el código actual para fijar el contrato protegido:

1. Login válido de `student`: `200`, `user.username`, `token` no vacío, `expiresIn = 3600`, `user.role = STUDENT` (ya existe la parte base).
2. Login válido de `trainer`: `200` y `user.role = TRAINER`.
3. Contraseña incorrecta de un usuario existente: `401`, sin `token`.
4. Usuario inexistente: `401`, sin `token`.
5. `username` vacío y `password` vacío: `400`.
6. Inyección en `username` con contraseña arbitraria: `401` sin `token` (ya cumple hoy; protege contra regresión).

Pruebas de inyección que fallan en rojo con el código actual (confirman el defecto):

7. `username=student`, `password=' OR '1'='1` → esperado `401` sin `token` (escenario del spec; hoy devuelve `200`).
8. `username=' OR '1'='1`, `password=' OR '1'='1` → esperado `401` sin `token` (hoy devuelve `200`).

Nota: el escenario de la spec "inyección en username" por sí solo no reproduce la vulnerabilidad por la precedencia de operadores (ver tabla de Context); la prueba 8 es la que cubre el vector real en el campo `username`.

## Estrategia incremental

1. **Caracterización** (solo pruebas): añadir las pruebas 2–6 y verificar que pasan en verde sin modificar código funcional.
2. **Reproducción**: añadir las pruebas 7 y 8 y comprobar que fallan en rojo con el código actual.
3. **Corrección**: modificar únicamente `findByCredentials` para usar parámetros enlazados.
4. **Verificación**: ejecutar `mvn test` desde `auth/` y revisar JaCoCo; la meta es 85 % o más sobre el código modificado.
5. **Revisión**: el diff debe limitarse a `LegacyDatabase.java` y `AuthResourceTest.java` (más artefactos OpenSpec).

Cada paso es un commit independiente para facilitar la revisión y el rollback.

## Risks / Trade-offs

- [El rojo de la prueba 7/8 no se reproduce por diferencias del motor SQLite] → Confirmar ambos casos en el paso 2 antes de corregir; si alguno ya pasa, mantenerlo como regresión y documentarlo.
- [Las pruebas comparten `./data/workshop.db` y pueden depender del estado de la base de datos] → No escribir en la tabla desde las pruebas; solo usar los usuarios sembrados.
- [El cambio podría alterar el manejo de errores sin querer] → Mantener el `try/catch` y el retorno `null`; cubierto por el contrato protegido.
- [Persisten otros hallazgos de seguridad en login (contraseñas en texto plano, secreto embebido, eco del usuario en `401`, campo `debug`)] → Se declaran como fuera de alcance; deben registrarse en `HALLAZGOS.md` o en issues propios, sin ocultarlos.
- [Cobertura del código modificado] → El método tiene pocas ramas; las pruebas 1–8 cubren éxito, no encontrado e inyección. La rama de excepción puede requerir una prueba adicional o justificar la brecha.

## Migration Plan

- No hay migración de datos ni cambios de esquema; no se necesita despliegue especial.
- **Rollback**: revertir el commit de la corrección (paso 3). Las pruebas de caracterización pueden quedarse porque describen el contrato protegido; las pruebas 7 y 8 volverían a fallar, lo que confirma que el defecto reaparece.
- No hay feature flag: un rollback devolvería la vulnerabilidad, por lo que debe tratarse como último recurso y comunicarse.
