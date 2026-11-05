# Proposal

## Why

El issue [#23](https://github.com/user-bcp-student49/ai-labs/issues/23), originado en `H-AUTH-01`, identifica que una entrada de login manipulada puede alterar la consulta de credenciales y permitir acceso sin conocer la contraseña. Corregirlo evita autenticaciones no autorizadas sin cambiar el comportamiento observable del inicio de sesión válido.

## What Changes

- **Alcance:** definir requisitos observables para `POST /auth/login`: conservar el login válido documentado por la prueba existente y rechazar intentos de inyección como usuario o contraseña con `401` y sin token.
- **Fuera de alcance:** cambiar la ruta, el formato de respuesta para el login válido, los usuarios/credenciales de prueba, otros endpoints o componentes; especificar la técnica de implementación.
- **Comportamiento a preservar:** credenciales `student` / `Workshop123!` siguen produciendo `200`, `user.username = student` y un `token` no vacío.
- `docs/ENDPOINTS.md` no documenta `/auth/login`; por tanto, no existe en ese baseline un contrato HTTP de auth que estos escenarios contradigan. El comportamiento exitoso se conserva según la prueba de caracterización existente y el rechazo de inyección se incorpora conforme al alcance explícito del issue.

## Capabilities

### New Capabilities
- `auth-login`: comportamiento observable del endpoint de autenticación `POST /auth/login`.

### Modified Capabilities
- Ninguna.

## Impact

- Issue de origen: `user-bcp-student49/ai-labs#23` (`H-AUTH-01`).
- Componente afectado: `auth/`, limitado al endpoint de login y su comportamiento verificable.
- API pública: conserva `POST /auth/login` y la respuesta exitosa existente; los intentos de inyección deben terminar en `401` sin token.
- No se proponen cambios a otros componentes, dependencias ni al contrato HTTP documentado de `api/`.