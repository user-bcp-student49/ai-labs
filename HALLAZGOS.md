# Hallazgos

## web — Discovery

### Flujo observado (contrato no acordado)

- `POST http://localhost:8080/auth/login`: `LoginComponent` envía `username`,
  `password` y `client`; si la respuesta contiene `token`, guarda el token y el
  usuario en `localStorage`, conserva también preferencias y navega a
  `/dashboard` (`web/src/app/login/login.component.ts:41-50`).
- En el dashboard, si no hay token navega a `/login`. Si existe, lee el usuario
  de `localStorage` y solicita
  `GET http://localhost:8000/api/tasks?owner=<username>` e incluye un
  encabezado `Authorization` con el token
  (`web/src/app/dashboard/dashboard.component.ts:36-44`).
  Filtra las tareas `ARCHIVED`, calcula etiquetas y las ordena
  (`web/src/app/dashboard/dashboard.component.ts:47-54`).
- Cerrar sesión elimina `workshop_token` y `workshop_user`, pero no
  `workshop_preferences`, y navega a `/login`
  (`web/src/app/dashboard/dashboard.component.ts:74-78`).
- No existe `docs/ENDPOINTS.md`; por tanto, lo anterior describe solo lo
  observado en el cliente. El alcance web no permite verificar la aceptación
  del contrato ni si el backend autoriza `owner` contra la identidad del token.

### Matriz de seguimiento

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-WEB-07 | web | El audit de dependencias sigue reportando vulnerabilidades no corregidas | Vulnerabilidad | `npm run audit:workshop` sigue fallando con 23 avisos: 10 moderados, 7 altos y 6 críticos. Incluye dependencias directas como Angular/Vitest y transitivas como piscina y tinypool. No se silenció el scanner ni se debe considerar cerrado el gate de dependencias. | `web/package.json:13-18,27-32`; `web/package-lock.json:4235,6524,11896,11940,13849,14024,14174,14272,15327` | alta | Pendiente |
| H-WEB-03 | web | Dependencias axios y lodash requieren revisión SCA | Vulnerabilidad | Resuelto para las dos dependencias de este hallazgo: se actualizaron a `axios` 1.20.0 y `lodash` 4.18.1; el `npm audit` posterior ya no las reporta. El audit sigue fallando por 23 hallazgos en otras dependencias (10 moderados, 7 altos, 6 críticos), que quedan como riesgo residual sin silenciar. | `web/package.json:19-20`; `web/package-lock.json:7237-7261,10525-10531` | alta | Resuelto |
| H-WEB-01 | web | Token de sesión en `localStorage` | Vulnerabilidad | Pendiente: token/usuario pasan a `sessionStorage` y se eliminan las antiguas claves persistentes, lo que reduce la persistencia tras cerrar la pestaña. Sin embargo, el token sigue disponible para JavaScript del mismo origen, que es el riesgo de exposición descrito originalmente; esta mitigación no lo resuelve por completo. | `web/src/app/services/session.service.ts:27-57`; `web/src/app/login/login.component.ts:59`; `web/src/app/dashboard/dashboard.component.ts:79` | media | Pendiente |
| H-WEB-08 | web | El cliente expone sin filtrar mensajes de error del backend | Sugerencia | El frontend copia los campos `message`/`detail` de respuestas Axios y el texto de `Error` directamente a mensajes de pantalla. Si el backend incluye detalles internos, se mostrarían al usuario; no se verificó en este alcance qué contenido real responde el servidor. | `web/src/app/utils/error-message.ts:3-16`; `web/src/app/login/login.component.ts:62-64`; `web/src/app/dashboard/dashboard.component.ts:61-65` | baja | Pendiente |
| H-WEB-02 | web | Contenido dinámico enlazado con `[innerHTML]` | Vulnerabilidad | Resuelto: los mensajes se muestran mediante interpolación de texto (`{{ message }}`), que no interpreta como marcado el usuario ni el texto del backend. No se afirma que antes hubiese una XSS explotable. | `web/src/app/login/login.component.html:39`; `web/src/app/login/login.component.ts:40-64` | baja | Resuelto |
| H-WEB-04 | web | Componentes concentran HTTP, sesión, URL y navegación | Refactor | Resuelto: HTTP se delega a `AuthService` y `TasksService`, las URLs se centralizan en configuración y el servicio de sesión centraliza token, usuario y preferencias; los componentes conservan navegación y presentación. | `web/src/app/services/auth.service.ts:10-21`; `web/src/app/services/tasks.service.ts:7-16`; `web/src/app/services/session.service.ts:27-73`; `web/src/environments/environment.ts:1-4` | baja | Resuelto |
| H-WEB-05 | web | Tipado `any`, validación anidada y duplicación de claves de sesión | Refactor | Resuelto: se añadieron tipos para login, usuario, preferencias y tareas; los componentes ya no usan `any`; login usa retornos anticipados y las claves de sesión/almacenamiento se centralizaron. | `web/src/app/models/auth.models.ts:1-20`; `web/src/app/models/task.models.ts:1-11`; `web/src/app/login/login.component.ts:18-64`; `web/src/app/dashboard/dashboard.component.ts:26-81`; `web/src/app/utils/legacy-format.ts:1-9` | baja | Resuelto |
| H-WEB-06 | web | Pruebas observadas limitadas a una utilidad | Refactor | Resuelto para las pruebas unitarias del flujo web: se añadieron casos de login, servicios, sesión y dashboard; la cobertura final medida del código instrumentado supera 85%. La plantilla se valida en build, no con DOM bajo el entorno Node actual de Vitest. | `web/src/app/login/login.component.spec.ts:30`; `web/src/app/dashboard/dashboard.component.spec.ts:26`; `web/src/app/services/session.service.spec.ts:32`; `web/src/app/services/auth.service.spec.ts:20`; `web/src/app/services/tasks.service.spec.ts:20` | baja | Resuelto |
