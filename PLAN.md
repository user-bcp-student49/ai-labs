# Plan

## web — Correcciones propuestas

### Seleccion

Se seleccionaron los seis hallazgos web cuando estaban en estado `Pendiente`.
El usuario aprobo los cambios antes de implementar. H-WEB-01 se priorizo por
el tratamiento del token; H-WEB-02, H-WEB-04, H-WEB-05 y H-WEB-06 se incluyeron
por los riesgos del codigo y el alcance de caracterizacion. H-WEB-03 se
selecciono como revision SCA, sin presumir un CVE antes de ejecutar la auditoria.

No existe `docs/ENDPOINTS.md`. El contrato HTTP a conservar es, por tanto, el
observado en `HALLAZGOS.md`: `POST /auth/login` con `username`, `password` y
`client`; persistir usuario y token al recibir token; luego `GET /api/tasks?owner=...`
con `Authorization: Bearer ...`; y al cerrar sesion retirar las claves de
usuario y token y volver a `/login`. Las URLs observadas son localhost:8080 y
localhost:8000. No se da por acordada ninguna semantica adicional del backend.

Las pruebas de caracterizacion se escribieron antes del refactor y se
ejecutaron. Los resultados verificables se registran al final de este plan;
`docs/TESTING.md` no se crea en este paso.

### H-WEB-01 — Token de sesion en `localStorage`

- **Hallazgo:** H-WEB-01, de `HALLAZGOS.md`, estado inicial `Pendiente`.
- **Problema:** el token es legible por cualquier JavaScript que se ejecute en
  el mismo origen. No se ha demostrado una explotacion.
- **Cambio propuesto:** centralizar la lectura, escritura y eliminacion del
  token/usuario en un servicio de sesion y usar `sessionStorage` para limitar
  su persistencia a la pestana. Esto mantiene la sesion disponible durante la
  navegacion y recargas en esa pestana, pero cambia su duracion respecto de
  `localStorage` y no protege el token frente a JavaScript del mismo origen.
  Registrar esta limitacion; una cookie HttpOnly requeriria coordinacion con
  el backend y queda fuera del alcance web.
- **Archivos a tocar:** `web/src/app/login/login.component.ts`,
  `web/src/app/dashboard/dashboard.component.ts`; nuevo servicio
  `web/src/app/services/session.service.ts`; pruebas nuevas
  `web/src/app/services/session.service.spec.ts` y pruebas de componentes
  indicadas en H-WEB-06.
- **Caracterizacion previa:** probar login valido persiste token/usuario y
  navega al dashboard; dashboard sin token redirige a login; dashboard con
  token usa ese valor en la cabecera de tareas; logout borra token/usuario y
  navega a login. Antes de cambiar almacenamiento, comprobar y dejar anotado
  que la persistencia tras cerrar/reabrir el navegador cambia; no presentar
  esa diferencia como comportamiento preservado.

### H-WEB-02 — Mensaje dinamico enlazado con `[innerHTML]`

- **Hallazgo:** H-WEB-02, de `HALLAZGOS.md`, estado inicial `Pendiente`; no equivale a
  una XSS confirmada.
- **Problema:** los mensajes construyen cadenas con texto de usuario y del
  backend y se presentan como HTML, aunque Angular sanitiza el enlace por
  defecto.
- **Cambio propuesto:** presentar el mensaje con interpolacion de texto y
  reemplazar las etiquetas HTML incrustadas en las cadenas por mensajes de
  texto plano. Mantener los mismos escenarios de validacion y error sin
  interpretar contenido del mensaje como marcado.
- **Archivos a tocar:** `web/src/app/login/login.component.ts`,
  `web/src/app/login/login.component.html`; prueba nueva
  `web/src/app/login/login.component.spec.ts`.
- **Caracterizacion previa:** comprobar mensajes actuales para usuario vacio,
  contrasena vacia, respuesta sin token y error de backend. Anotar los textos
  y el caso del nombre de usuario antes del cambio; despues verificar que
  contenido como `<strong>` se muestra como texto, no se interpreta como HTML.
  Vitest esta configurado con entorno `node`; no hay un entorno DOM de pruebas
  declarado, asi que no afirmar una prueba de render hasta resolver esa
  limitacion sin introducir dependencias no aprobadas.

### H-WEB-03 — Revision SCA de axios y lodash

- **Hallazgo:** H-WEB-03, de `HALLAZGOS.md`, estado inicial `Pendiente`; es una
  sugerencia de revision, no una vulnerabilidad confirmada.
- **Problema:** `web/package.json` fija las versiones indicadas en la matriz,
  pero aun no hay evidencia de auditoria o advisory que confirme un riesgo.
- **Cambio propuesto:** ejecutar `npm run audit:workshop` en `web/` y evaluar
  cada resultado contra avisos aplicables. No actualizar ni eliminar paquetes
  basandose solo en la lista de `RETO.md`. Si la auditoria confirma un problema,
  proponer el cambio minimo a `web/package.json` y `web/package-lock.json`,
  comprobando que no cambien los endpoints ni el flujo.
- **Archivos a tocar:** inicialmente ninguno; solo si la evidencia SCA justifica
  una correccion, `web/package.json` y `web/package-lock.json`.
- **Caracterizacion previa:** no aplica una prueba funcional para la inspeccion
  de advisories. Antes de cualquier cambio de dependencia, ejecutar y registrar
  `npm test` y `npm run build`; despues repetirlos y ejecutar de nuevo la
  auditoria. No se afirma ningun resultado en este plan.

### H-WEB-04 — HTTP, URL y sesion en componentes

- **Hallazgo:** H-WEB-04, de `HALLAZGOS.md`, estado inicial `Pendiente`.
- **Problema:** los componentes llaman axios directamente, conocen URLs y
  realizan navegacion y operaciones de sesion, haciendo mas dificil aislar
  responsabilidades y probar el flujo.
- **Cambio propuesto:** extraer las solicitudes a servicios `AuthService` y
  `TasksService`; dejar a los componentes la interaccion de pantalla y
  navegacion. Centralizar URLs en configuracion de ambiente, como recomienda
  `docs/GOOD_PRACTICES.md`. El servicio HTTP de autenticacion conserva cuerpo,
  endpoint y timeout observados; tareas conserva query, cabecera y filtros
  actuales.
- **Archivos a tocar:** `web/src/app/login/login.component.ts`,
  `web/src/app/dashboard/dashboard.component.ts`; nuevos
  `web/src/app/services/auth.service.ts` y
  `web/src/app/services/tasks.service.ts`; configuracion nueva bajo
  `web/src/environments/`; pruebas de servicios nuevas junto a los servicios.
- **Caracterizacion previa:** con axios simulado, verificar URL, metodo,
  cuerpo de login, timeout, query `owner`, cabecera de autorizacion, respuesta
  vacia/error y tareas recibidas. Verificar tambien redireccion cuando no hay
  token y navegacion a dashboard al login valido. Usar Vitest existente sin
  instalar dependencias.

### H-WEB-05 — Tipado, validacion anidada y estado compartido

- **Hallazgo:** H-WEB-05, de `HALLAZGOS.md`, estado inicial `Pendiente`.
- **Problema:** `any` en propiedades, respuestas y tareas permite errores de
  forma sin deteccion estatica; la validacion anidada dificulta comprender
  salidas y los componentes repiten acceso a claves de sesion.
- **Cambio propuesto:** definir tipos/interfaces para request/response de login,
  usuario, tarea y preferencias; reemplazar `any` por esos tipos y reducir la
  validacion de login a guard clauses. Reutilizar el servicio de sesion de
  H-WEB-01 en vez de duplicar claves. Conservar el formato de respuestas y la
  transformacion de tareas observada.
- **Archivos a tocar:** `web/src/app/login/login.component.ts`,
  `web/src/app/dashboard/dashboard.component.ts`,
  `web/src/app/utils/legacy-format.ts`; nuevo archivo de tipos bajo
  `web/src/app/models/`; pruebas nuevas de componentes/utilidad segun los casos.
- **Caracterizacion previa:** cubrir entradas nulas/vacias, respuesta de login
  sin token, tarea con campos opcionales, tarea archivada, etiquetas de estado,
  orden por prioridad y errores de red. Confirmar que mensajes, destinos y
  salida visible equivalen al comportamiento actual.

### H-WEB-06 — Cobertura limitada a una utilidad

- **Hallazgo:** H-WEB-06, de `HALLAZGOS.md`, estado inicial `Pendiente`.
- **Problema:** la prueba encontrada cubre `formatTaskLabel`, no los caminos de
  login, guardado de sesion, carga de tareas, error, filtro/orden o logout.
- **Cambio propuesto:** ampliar las pruebas unitarias de Vitest para login,
  servicios HTTP/sesion y dashboard con dependencias simuladas; no cambiar
  codigo de produccion solo para satisfacer una prueba. Mantener la prueba
  existente de `formatTaskLabel`.
- **Archivos a tocar:** nuevas pruebas
  `web/src/app/login/login.component.spec.ts`,
  `web/src/app/dashboard/dashboard.component.spec.ts` y pruebas de los
  servicios nuevos de H-WEB-01/H-WEB-04; conservar
  `web/src/app/utils/legacy-format.spec.ts`.
- **Caracterizacion previa:** escribir primero los casos de login valido e
  invalido, persistencia de sesion, ausencia de token, respuesta de tareas,
  tarea archivada, error de carga y logout. Ejecutarlos antes de refactorizar y
  registrar resultados; despues repetir y comprobar el build. El entorno Vitest
  actual es `node`, sin DOM, por lo que pruebas de plantilla/browser quedan
  pendientes hasta que exista una via de validacion aprobada.

### Resultados de implementacion

| ID | Cambio realizado (diff conceptual) | Caracterizacion antes | Prueba de correccion/despues |
|---|---|---|---|
| H-WEB-01 | Nuevo `SessionService` centraliza token, usuario y preferencias. Token y usuario viven en `sessionStorage`; elimina las antiguas claves persistentes del token/usuario al inicializar. No agrega secretos ni los mueve desde backend al frontend. | `npm test` desde `web/`: 9 pruebas pasaron antes de refactorizar, cubriendo login, almacenamiento local observado, dashboard, tareas y logout. | `web/src/app/services/session.service.spec.ts` prueba persistencia por pestana, borrado de credenciales antiguas, preferencias y datos invalidos. Prueba final: `npm test`, 22/22. Riesgo residual: cualquier JavaScript del mismo origen puede leer `sessionStorage`; no equivale a una cookie HttpOnly. |
| H-WEB-02 | Se sustituyo `[innerHTML]` por interpolacion; los mensajes dejaron de contener etiquetas HTML. | Pruebas previas cubrieron validacion vacia, respuesta sin token y error de login, incluyendo la cadena del mensaje. | `LoginComponent` conserva esos mensajes como texto; `npm run build` valida la compilacion de la plantilla. El entorno de Vitest es Node, por lo que no se afirma una prueba DOM que compruebe el render escapado en navegador. |
| H-WEB-03 | Tras el audit inicial se actualizaron axios 0.31.0 a 1.20.0 y lodash 4.17.21 a 4.18.1. Se actualizaron manifiesto y lock con npm. | `npm run audit:workshop` informo 25 vulnerabilidades en el arbol inicial; axios y lodash aparecian con severidad alta. `npm view axios version` y `npm view lodash version` devolvieron las versiones instaladas como releases actuales. | Tras actualizar, `npm ls axios lodash --depth=0` confirma axios 1.20.0 y lodash 4.18.1; el audit posterior ya no reporta esos paquetes, pero falla con 23 vulnerabilidades restantes (10 moderadas, 7 altas, 6 criticas) en otras dependencias. Hallazgo limitado a axios/lodash resuelto; el gate SCA global permanece fallido y visible. |
| H-WEB-04 | Se extrajeron login y consulta de tareas a `AuthService` y `TasksService`; URLs centralizadas en `environment.ts`; almacenamiento encapsulado en `SessionService`. | Antes del cambio, pruebas verificaron URL, metodo, cuerpo, timeout, query, cabecera, redirecciones y resultado de tareas desde los componentes. | Pruebas de servicios comprueban `POST /auth/login`, sus campos/timeout, y `GET /api/tasks` con owner codificado y cabecera Bearer; pruebas de componente comprueban destino, filtros, orden y logout. `npm test`: 22/22. No se ejecutaron servicios backend reales. |
| H-WEB-05 | Se definieron modelos `LoginRequest`, `LoginResponse`, `AuthUser`, `UserPreferences` y `Task`; se eliminaron `any` de los componentes/utilidad modificados y se usaron retornos anticipados y un normalizador tipado de errores. | Caracterizacion previa cubrio entradas vacias, respuesta sin token, error, tareas archivadas y orden por prioridad. | `npm test`: 22/22; `npm run build`: correcto. Cobertura final de lineas de archivos instrumentados: LoginComponent 93.44%, DashboardComponent 97.1%, servicios 96.82%-100%, utilidades 100%. |
| H-WEB-06 | Se incorporaron pruebas unitarias de login, dashboard, servicios de autenticacion/tareas/sesion y errores; se ampliaron casos de formato. | Suite previa: 9/9 pruebas. | `npm test`: 22/22. `npm run test:coverage`: 22/22; cobertura de lineas total informada por Vitest 87.27% (umbral objetivo 85%). Build posterior: correcto. No se simularon los backends reales ni se ejecutaron pruebas con DOM. |

### Ejecuciones y pendientes registrados

- `web/ — H-WEB-01, H-WEB-02, H-WEB-04, H-WEB-05, H-WEB-06 — npm test`
  antes de modificar: correcto, 3 archivos y 9 pruebas pasaron.
- `web/ — H-WEB-01, H-WEB-02, H-WEB-04, H-WEB-05, H-WEB-06 — npm test`
  despues: correcto, 7 archivos y 22 pruebas pasaron.
- `web/ — H-WEB-01, H-WEB-02, H-WEB-04, H-WEB-05, H-WEB-06 —
  npm run test:coverage`: correcto, 22 pruebas; cobertura de lineas 87.27%.
- `web/ — H-WEB-02, H-WEB-04, H-WEB-05, H-WEB-06 — npm run build`:
  correcto; Angular emitio una advertencia de optimizacion CommonJS para
  `lodash/merge`.
- `web/ — H-WEB-03 — npm run audit:workshop` antes de actualizar: fallo con
  25 vulnerabilidades (10 moderadas, 9 altas, 6 criticas). Despues: fallo con
  23 (10 moderadas, 7 altas, 6 criticas); axios/lodash ya no aparecen en el
  informe, pero los hallazgos restantes siguen pendientes.
- `web/ — H-WEB-03 — npm install`: primer intento fallo con error interno de
  npm al leer `children`; `npm install --package-lock-only --ignore-scripts
  --legacy-peer-deps` y despues `npm install --ignore-scripts --legacy-peer-deps`
  finalizaron correctamente. npm install reporto 19 vulnerabilidades; la
  ejecucion dedicada posterior de `npm run audit:workshop` informo 23. El
  `web/package-lock.json` ya estaba modificado antes del trabajo; npm regenero
  el lock para las nuevas versiones y elimino entradas extraneas. Revisar el
  diff del lock antes de integrar. No se uso `npm audit fix --force`.
- No se ejecutaron pruebas de navegador/DOM ni login integrado con servicios
  reales; no se cambia `docs/ENDPOINTS.md` ni se crea `docs/TESTING.md` en este
  paso.
