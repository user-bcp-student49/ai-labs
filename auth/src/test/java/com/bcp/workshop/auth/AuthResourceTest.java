package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.emptyOrNullString;
import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@QuarkusTest
class AuthResourceTest {
    // Spec "Conservar el comportamiento del inicio de sesión exitoso" y contrato de éxito protegido en design.md.
    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("user.role", is("STUDENT"))
                .body("expiresIn", is(3600))
                .body("token", not(emptyOrNullString()));
    }

    // Contrato de éxito para otro usuario sembrado: el rol proviene de la base, no es fijo.
    @Test
    void logsInWithTrainerUser() {
        postLogin("trainer", "Trainer123!")
                .statusCode(200)
                .body("user.username", is("trainer"))
                .body("user.role", is("TRAINER"))
                .body("token", not(emptyOrNullString()));
    }

    // Credenciales inválidas: 401 con message y sin token; el login válido no debe volverse más permisivo.
    @Test
    void rejectsWrongPasswordForExistingUser() {
        postLogin("student", "wrong-password")
                .statusCode(401)
                .body("message", notNullValue())
                .body("token", nullValue());
    }

    // Credenciales inválidas: un usuario inexistente termina igual en 401 sin token.
    @Test
    void rejectsUnknownUser() {
        postLogin("nobody", "Workshop123!")
                .statusCode(401)
                .body("message", notNullValue())
                .body("token", nullValue());
    }

    // Validación de entrada: username vacío responde 400 con el mensaje actual.
    @Test
    void rejectsEmptyUsername() {
        postLogin("", "Workshop123!")
                .statusCode(400)
                .body("message", is("Username is required"))
                .body("token", nullValue());
    }

    // Validación de entrada: password vacío responde 400 con el mensaje actual.
    @Test
    void rejectsEmptyPassword() {
        postLogin("student", "")
                .statusCode(400)
                .body("message", is("Password is required"))
                .body("token", nullValue());
    }

    // Spec "valor de inyección como usuario": ya rechaza hoy por la precedencia AND/OR (design.md); evita regresiones.
    @Test
    void rejectsInjectionValueAsUsernameWithArbitraryPassword() {
        postLogin("' OR '1'='1", "arbitrary-password")
                .statusCode(401)
                .body("token", nullValue());
    }

    private static ValidatableResponse postLogin(String username, String password) {
        return given()
                .contentType("application/json")
                .body(Map.of("username", username, "password", password))
                .when().post("/auth/login")
                .then();
    }
}
