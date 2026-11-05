# Tasks

Alcance: issue #23 (`H-AUTH-01`), solo componente `auth/`. Archivos permitidos: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java` y `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`. Las pruebas se ejecutan con `mvn test` desde `auth/`.

## 1. Pruebas de caracterización (sin cambio funcional)

- [x] 1.1 Ejecutar `mvn test` desde `auth/` sobre el código actual y verificar que la prueba existente `logsInWithWorkshopUser` pasa (línea base en verde).
- [x] 1.2 Ampliar la prueba de login válido de `student` para comprobar `token` no vacío, `expiresIn = 3600` y `user.role = STUDENT`; verificar que pasa en verde.
- [x] 1.3 Añadir prueba de login válido de `trainer` (`Trainer123!`) con `200` y `user.role = TRAINER`; verificar que pasa en verde.
- [x] 1.4 Añadir pruebas de contraseña incorrecta para `student` y de usuario inexistente, ambas con `401` y sin `token`; verificar que pasan en verde.
- [x] 1.5 Añadir prueba de `username` vacío y de `password` vacío con `400`; verificar que pasan en verde.
- [x] 1.6 Añadir prueba de `' OR '1'='1` como `username` con una contraseña arbitraria, esperando `401` sin `token`; verificar que pasa en verde con el código actual (protección contra regresión).
- [x] 1.7 Confirmar con `git diff --stat` que solo cambió `AuthResourceTest.java` y registrar el estado de la suite en verde.

## 2. Reproducción del defecto (pruebas en rojo)

- [x] 2.1 Añadir prueba con `username=student` y `password=' OR '1'='1`, esperando `401` sin `token` (escenario de la spec); verificar que falla en rojo con `200` sobre el código actual.
- [x] 2.2 Añadir prueba con `' OR '1'='1` en `username` y en `password`, esperando `401` sin `token`; verificar que falla en rojo con `200` sobre el código actual.
- [x] 2.3 Si alguna de 2.1 o 2.2 ya pasa en verde, mantenerla como prueba de regresión y anotar la diferencia respecto a la hipótesis del diseño en el mensaje de commit.

## 3. Corrección incremental

- [x] 3.1 Modificar únicamente `LegacyDatabase.findByCredentials` para enlazar `username` y `password` como parámetros de la consulta en lugar de concatenarlos, conservando firma, tipo de retorno, `try/catch` y retorno `null` ante error; verificar con `grep` que el método ya no concatena valores en el SQL.
- [x] 3.2 Ejecutar `mvn test` desde `auth/` y verificar que pasan todas las pruebas de los grupos 1 y 2, incluidas 2.1 y 2.2 ahora en verde.

## 4. Verificación final y cobertura

- [x] 4.1 Ejecutar `mvn verify` desde `auth/` y revisar el reporte JaCoCo; verificar que la cobertura del código modificado es 85 % o superior, o documentar y justificar la brecha (por ejemplo, la rama de excepción).
- [x] 4.2 Verificar con `git diff --stat` que el cambio funcional se limita a `LegacyDatabase.java` y `AuthResourceTest.java`, y que `api/`, `web/` y los demás archivos de `auth/` no cambiaron.
- [x] 4.3 Verificar contra `specs/auth-login/spec.md` y los criterios de aceptación del issue #23 que cada escenario tiene una prueba que pasa, y ejecutar `openspec status --change "parameterized-auth-login"` desde la raíz.

## Workflow follow-up

- Un commit por grupo de tareas (1, 2 y 3) para facilitar revisión y rollback, según el diseño.
- Archivar el cambio tras la revisión y aprobación humanas; en el Día 1 no se hace push ni se crean PR.
