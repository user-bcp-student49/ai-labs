# Spec Delta

## Purpose

Define el contrato observable del endpoint de inicio de sesión de autenticación: conserva los inicios de sesión válidos e impide que valores de credenciales manipulados autentiquen a un usuario sin credenciales válidas.

## ADDED Requirements

### Requirement: Conservar el comportamiento del inicio de sesión exitoso
El endpoint de login MUST seguir aceptando las credenciales válidas establecidas del workshop y devolver el contrato de respuesta exitosa existente.

#### Scenario: Un usuario del workshop inicia sesión correctamente
- **WHEN** un cliente envía `POST /auth/login` con usuario `student` y contraseña `Workshop123!`
- **THEN** el código de respuesta es `200`, `user.username` es `student` y `token` está presente y no vacío

### Requirement: Rechazar intentos de inyección como credenciales inválidas
El endpoint de login MUST NOT autenticar una solicitud cuyo usuario o contraseña contenga el valor de inyección identificado en el issue #23.

#### Scenario: El valor de inyección se envía como usuario
- **WHEN** un cliente envía `POST /auth/login` con usuario `' OR '1'='1`
- **THEN** el código de respuesta es `401` y la respuesta no contiene `token`

#### Scenario: El valor de inyección se envía como contraseña
- **WHEN** un cliente envía `POST /auth/login` con usuario `student` y contraseña `' OR '1'='1`
- **THEN** el código de respuesta es `401` y la respuesta no contiene `token`