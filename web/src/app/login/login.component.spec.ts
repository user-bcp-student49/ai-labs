import '@angular/compiler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginComponent } from './login.component';

describe('LoginComponent characterization', () => {
  const storage = new Map<string, string>();
  const router = { navigate: vi.fn().mockResolvedValue(true) };
  const authService = { login: vi.fn() };
  const sessionService = {
    getPreferences: vi.fn().mockReturnValue(null),
    saveSession: vi.fn(),
    savePreferences: vi.fn()
  };
  let component: LoginComponent;

  beforeEach(() => {
    storage.clear();
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
        removeItem: (key: string) => storage.delete(key)
      }
    });
    vi.clearAllMocks();
    component = new LoginComponent(router as never, authService as never, sessionService as never);
  });

  it('rejects blank credentials without making a request', async () => {
    await component.login();
    expect(component.message).toBe('Ingrese un usuario.');
    expect(authService.login).not.toHaveBeenCalled();

    component.username = 'student';
    component.password = ' ';
    await component.login();
    expect(component.message).toBe('Ingrese una contraseña.');
    expect(authService.login).not.toHaveBeenCalled();
  });

  it('saves a successful session and navigates to dashboard', async () => {
    authService.login.mockResolvedValue({
      token: 'fake-token',
      user: { username: 'student' }
    });
    component.username = 'student';
    component.password = 'Workshop123!';

    await component.login();

    expect(authService.login).toHaveBeenCalledWith('student', 'Workshop123!');
    expect(sessionService.saveSession).toHaveBeenCalledWith({
      token: 'fake-token',
      user: { username: 'student' }
    });
    expect(sessionService.savePreferences).toHaveBeenCalledWith({
      theme: 'light',
      showTips: true,
      compact: false
    });
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    expect(component.busy).toBe(false);
  });

  it('shows the missing-token response without navigating', async () => {
    authService.login.mockResolvedValue({ user: {} });
    component.username = 'student';
    component.password = 'wrong';

    await component.login();

    expect(component.message).toBe('El backend respondió sin token.');
    expect(sessionService.saveSession).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('shows a backend error and resets the busy state', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    authService.login.mockRejectedValue(new Error('Invalid credentials'));
    component.username = 'student';
    component.password = 'wrong';

    await component.login();

    expect(component.message).toContain('Invalid credentials');
    expect(component.busy).toBe(false);
    consoleError.mockRestore();
  });

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
});
