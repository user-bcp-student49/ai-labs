# Pruebas — componente web

## Matriz de casos

Las pruebas son unitarias de Vitest y usan dobles locales para servicios,
sesión y respuestas HTTP; no contactan los backends.

| flujo | caso | tipo | resultado esperado |
|---|---|---|---|
| Login → tareas | Credenciales válidas; el login guarda la sesión, navega al dashboard y la consulta obtiene tareas | Camino feliz | La petición de tareas recibe `owner` y token guardados; la tarea no archivada se muestra y termina la carga. **Pasó** en `DashboardComponent:113`. |
| Login | Usuario vacío y contraseña vacía | Borde | Muestra el mensaje de validación correspondiente y no llama al servicio de autenticación. **Pasó** en `LoginComponent:30`. |
| Login | Respuesta exitosa sin token | Borde / respuesta inesperada | Muestra “El backend respondió sin token.”; no guarda sesión ni navega. **Pasó** en `LoginComponent:66`. |
| Login | Credenciales inválidas / rechazo HTTP con mensaje | Error | Muestra el mensaje devuelto por el error, no navega y restablece `busy`. **Pasó** en `LoginComponent:78`. |
| Login | Servicio de autenticación no disponible (`Network Error`) | Error | Muestra el error de red, no navega y restablece `busy`. **Pasó** en `LoginComponent:91`. |
| Login | Timeout de autenticación | Error | Muestra el mensaje de timeout, no navega y restablece `busy`. **Pasó** en `LoginComponent:105`; el rechazo se simula, no se espera cinco segundos reales. |
| Tareas | Token inválido, respuesta 401 con `detail` | Error | Muestra `detail`, detiene la carga y, según el comportamiento actual documentado, no borra la sesión ni redirige automáticamente. **Pasó** en `DashboardComponent:63`. |
| Tareas | Rechazo de red del servicio | Error | Muestra el texto de error y detiene la carga. **Pasó** en `DashboardComponent:52`. |
| Tareas | Rechazo de la consulta por timeout | Error | Muestra el texto de timeout y detiene la carga. **Pasó** en `DashboardComponent:84`; Axios se simula rechazando, no se prueba temporización de red. |
| Tareas | Respuesta exitosa cuyo cuerpo no es un array | Error / respuesta inesperada | El procesamiento falla dentro del componente, el error se presenta y la carga termina. **Pasó** en `DashboardComponent:95`. |
| Tareas | Array con tareas archivadas, tareas válidas y prioridades | Camino feliz / regla de negocio | Excluye `ARCHIVED`, calcula etiquetas, ordena por prioridad descendente y termina la carga. **Pasó** en `DashboardComponent:34`. |
| Sesión | No hay token | Borde | No solicita tareas y navega a `/login`. **Pasó** en `DashboardComponent:27`. |
| Cierre de sesión | Logout | Camino feliz | Limpia credenciales y navega a `/login`. **Pasó** en `DashboardComponent:106`. |

Los números de línea son del código de pruebas actual. La lista completa de
casos y sus dobles está en
`web/src/app/login/login.component.spec.ts` y
`web/src/app/dashboard/dashboard.component.spec.ts`; los contratos de HTTP y
sesión también se prueban en los archivos `.spec.ts` junto a cada servicio.

## Código de los tests de flujo y error

Los siguientes fragmentos corresponden a casos ejecutados; los archivos
enlazados arriba contienen el código íntegro.

```ts
it('shows an authentication service unavailable error and resets the busy state', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
  authService.login.mockRejectedValue(new Error('Network Error'));
  component.username = 'student';
  component.password = 'Workshop123!';

  await component.login();

  expect(component.message).toBe('No se pudo autenticar a student. Network Error');
  expect(component.busy).toBe(false);
  expect(router.navigate).not.toHaveBeenCalled();
  consoleError.mockRestore();
});

it('shows the login timeout error and resets the busy state', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
  authService.login.mockRejectedValue(new Error('timeout of 5000ms exceeded'));
  component.username = 'student';
  component.password = 'Workshop123!';

  await component.login();

  expect(component.message).toBe(
    'No se pudo autenticar a student. timeout of 5000ms exceeded'
  );
  expect(component.busy).toBe(false);
  expect(router.navigate).not.toHaveBeenCalled();
  consoleError.mockRestore();
});
```

```ts
it('shows an invalid-token response without clearing the session or redirecting', async () => {
  const unauthorizedError = new axios.AxiosError('Request failed with status code 401');
  unauthorizedError.response = {
    data: { detail: 'Not authorized' },
    status: 401,
    statusText: 'Unauthorized',
    headers: {},
    config: { headers: new axios.AxiosHeaders() }
  };
  sessionService.getToken.mockReturnValue('invalid-token');
  sessionService.getUser.mockReturnValue({ username: 'student' });
  tasksService.getTasks.mockRejectedValue(unauthorizedError);

  await component.ngOnInit();

  expect(component.error).toBe('Not authorized');
  expect(component.loading).toBe(false);
  expect(sessionService.clearSession).not.toHaveBeenCalled();
  expect(router.navigate).not.toHaveBeenCalled();
});
```

## Ejecuciones y cobertura

Comandos ejecutados desde el directorio `web/`:

| comando | directorio | código de salida | resultado real |
|---|---|---:|---|
| `npx tsc --noEmit -p tsconfig.json` | `web/` | 0 | **Componente:** web. **ID:** H-WEB-06. Chequeo TypeScript del código fuente y pruebas completado sin errores. |
| `npm test` | `web/` | 0 | **Componente:** web. **ID:** H-WEB-06. 7 archivos de pruebas aprobados; 28/28 pruebas aprobadas. |
| `npm run test:coverage` | `web/` | 0 | **Componente:** web. **ID:** H-WEB-06. 7 archivos de pruebas aprobados; 28/28 pruebas aprobadas. Vitest informó cobertura de líneas del 87,27%. |

La medición usa el proveedor **V8** configurado en
`web/vitest.config.ts`, con cobertura por líneas (`lines.covered / lines.total`).
No se modificó código de producción en este paso; para cuantificar la
superficie de producción del flujo cubierta por estas pruebas, se agregan los
archivos instrumentados de componentes, servicios y utilidades relacionados:

| superficie del flujo | líneas cubiertas / líneas instrumentadas | cobertura |
|---|---:|---:|
| LoginComponent | 57 / 61 | 93,44% |
| DashboardComponent | 67 / 69 | 97,10% |
| AuthService | 21 / 21 | 100% |
| TasksService | 14 / 14 | 100% |
| SessionService | 61 / 63 | 96,82% |
| Utilidades `error-message` y `legacy-format` | 23 / 23 | 100% |
| **Agregado de la superficie del flujo** | **243 / 251** | **96,81%** |

La cobertura global se registra por separado: **247 / 283 líneas = 87,27%**.
Incluye archivos de arranque y componente raíz que estas pruebas unitarias no
ejecutan. La cobertura se refiere al código de producción instrumentado por
Vitest; el código de los propios tests no se instrumenta.

## Fallos

- No quedan fallos en las validaciones finales.
- La primera ejecución de `npx tsc --noEmit -p tsconfig.json` detectó que el
  mock Axios 401 omitía `headers` en su configuración (`TS2741`). Se completó
  el mock y la ejecución final de TypeScript indicada arriba terminó con
  código 0. No era un fallo del código de producción.

## Pendientes y límites

- No se ejecutó una integración con los backends reales ni se verificaron
  códigos HTTP o schemas en servidores; los requests y errores se simulan.
- El timeout del login se comprueba como rechazo entregado al componente. No
  se mide el tiempo real de Axios ni se espera el intervalo de 5000 ms.
- `TasksService` no configura timeout propio. El caso de timeout de tareas
  comprueba la reacción del dashboard a un rechazo simulado, no el tiempo tras
  el cual Axios rechaza una conexión real.
- El dashboard conserva la sesión y no redirige al recibir 401; se prueba y
  documenta como comportamiento observado, no como decisión confirmada del
  backend.
- La plantilla y accesibilidad visual no se prueban con navegador/DOM: Vitest
  está configurado con entorno `node`.

## Pruebas propuestas, no ejecutadas

- Ejecutar con los servicios locales disponibles una prueba de integración
  manual o automatizada del login válido seguido de carga de tareas, para
  confirmar que el contrato documentado coincide con respuestas reales.
- Coordinar con el responsable de API si un 401 debe limpiar la sesión y
  redirigir; si se acuerda otro comportamiento, añadir la prueba de regresión
  correspondiente antes de cambiar la UI.
