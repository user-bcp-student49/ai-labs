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

## web — Candidatos de discovery

Los siguientes puntos son candidatos basados en el código del componente web.
No se ejecutaron pruebas para reproducirlos y requieren revisión humana antes
de convertirse en hallazgos confirmados.

| id | componente | candidato | evidencia (archivo:linea o comando) | impacto | prioridad propuesta | contrato potencialmente afectado | cómo validarlo | estado |
|---|---|---|---|---|---|---|---|---|
| H-WEB-09 | web | El comparador de prioridades devuelve `1` también cuando las prioridades son iguales o falta alguna prioridad. | `web/src/app/dashboard/dashboard.component.ts:70-76` | El orden de tareas con prioridades iguales o ausentes puede depender del orden inicial y del comportamiento de ordenación, no de una regla estable documentada. | baja | Presentación y orden de la lista de tareas; no cambia el request HTTP. | Añadir prueba unitaria con prioridades repetidas y ausentes; definir y verificar la salida esperada, incluyendo que el comparador preserve el orden de elementos iguales si esa es la regla acordada. | CANDIDATO |
| H-WEB-10 | web | Login comprueba que exista `token`, pero no valida la forma de `user` antes de guardar la sesión. | `web/src/app/login/login.component.ts:54-60`; `web/src/app/services/session.service.ts:50-52`; `web/src/app/services/session.service.ts:37-46`; `web/src/app/dashboard/dashboard.component.ts:52-64` | Ante una respuesta exitosa con token y usuario ausente o inválido, podría persistirse una sesión inutilizable; el dashboard detectaría el dato inválido al leerlo y mostraría error en vez de cargar tareas. | media | Forma de respuesta de `POST /auth/login` y continuidad de sesión al consultar tareas. | Probar respuestas mock con `user` ausente, `null` y con `username` de tipo incorrecto; verificar que no quede sesión parcial ni se navegue como si el login hubiera completado correctamente. | CANDIDATO |
| H-WEB-11 | web | La lectura de token del dashboard ocurre antes del bloque `try/catch` que maneja errores de carga. | `web/src/app/dashboard/dashboard.component.ts:45-53`; `web/src/app/services/session.service.ts:33-35` | Si el navegador deniega el acceso a `sessionStorage` y la lectura lanza una excepción, `ngOnInit` puede rechazar fuera del manejo local y dejar la vista en estado de carga. Es un caso condicionado al comportamiento del navegador y no se ha reproducido. | baja | Recuperación de sesión y estado visual de carga del dashboard; no cambia el contrato HTTP. | Simular `getToken()` lanzando una excepción en una prueba del componente; observar la promesa de inicialización y verificar que la UI no quede indefinidamente en carga y muestre el tratamiento acordado. | CANDIDATO |
| H-WEB-12 | web | La consulta de tareas no configura un timeout explícito. | `web/src/app/services/tasks.service.ts:8-14` | Si la conexión no resuelve ni rechaza, el dashboard puede permanecer cargando sin límite explícito de tiempo. El timeout efectivo de Axios depende de su configuración predeterminada. | media | Disponibilidad percibida de `GET /api/tasks` y estado de carga del dashboard. | Añadir prueba del servicio que compruebe el timeout acordado en la configuración Axios y prueba del dashboard ante la cancelación/rechazo por timeout; confirmar antes el valor con responsables del servicio. | CANDIDATO |
