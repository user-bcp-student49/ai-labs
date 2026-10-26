import '@angular/compiler';
import { beforeEach, describe, expect, it } from 'vitest';
import { SessionService } from './session.service';

describe('SessionService', () => {
  const storage = new Map<string, string>();
  const legacyStorage = new Map<string, string>();
  let service: SessionService;

  beforeEach(() => {
    storage.clear();
    legacyStorage.clear();
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
        removeItem: (key: string) => storage.delete(key)
      }
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => legacyStorage.get(key) ?? null,
        setItem: (key: string, value: string) => legacyStorage.set(key, value),
        removeItem: (key: string) => legacyStorage.delete(key)
      }
    });
    service = new SessionService();
  });

  it('stores and reads the login token and user', () => {
    service.saveSession({ token: 'fake-token', user: { username: 'student' } });

    expect(service.getToken()).toBe('fake-token');
    expect(service.getUser()).toEqual({ username: 'student' });
  });

  it('returns null when session values are absent', () => {
    expect(service.getToken()).toBeNull();
    expect(service.getUser()).toBeNull();
  });

  it('clears credentials without changing preferences', () => {
    service.saveSession({ token: 'fake-token', user: { username: 'student' } });
    service.savePreferences({ theme: 'light', showTips: true, compact: false });

    service.clearSession();

    expect(service.getToken()).toBeNull();
    expect(service.getUser()).toBeNull();
    expect(service.getPreferences()).toEqual({ theme: 'light', showTips: true, compact: false });
  });

  it('returns null when no preferences have been saved', () => {
    expect(service.getPreferences()).toBeNull();
  });

  it('removes persisted credentials from the previous local storage session', () => {
    legacyStorage.set('workshop_token', 'old-token');
    legacyStorage.set('workshop_user', '{"username":"student"}');

    service = new SessionService();

    expect(legacyStorage.has('workshop_token')).toBe(false);
    expect(legacyStorage.has('workshop_user')).toBe(false);
    expect(service.getToken()).toBeNull();
  });

  it('rejects malformed stored user data explicitly', () => {
    storage.set('workshop_user', 'not-json');
    expect(() => service.getUser()).toThrow();

    storage.set('workshop_user', '[]');
    expect(() => service.getUser()).toThrow('Stored session user is invalid');
  });

  it('rejects invalid stored preferences explicitly', () => {
    legacyStorage.set('workshop_preferences', '{"showTips":"yes"}');
    expect(() => service.getPreferences()).toThrow('Stored preferences are invalid');
  });
});
