import { Injectable } from '@angular/core';
import { AuthUser, LoginResponse, UserPreferences } from '../models/auth.models';

const TOKEN_KEY = 'workshop_token';
const USER_KEY = 'workshop_user';
const PREFERENCES_KEY = 'workshop_preferences';

function isAuthUser(value: unknown): value is AuthUser {
  if (typeof value !== 'object' || value === null || !('username' in value)) {
    return false;
  }
  return typeof value.username === 'string'
    && (!('displayName' in value) || typeof value.displayName === 'string')
    && (!('role' in value) || typeof value.role === 'string');
}

function isUserPreferences(value: unknown): value is Partial<UserPreferences> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return false;
  }
  return (!('theme' in value) || typeof value.theme === 'string')
    && (!('showTips' in value) || typeof value.showTips === 'boolean')
    && (!('compact' in value) || typeof value.compact === 'boolean');
}

@Injectable({ providedIn: 'root' })
export class SessionService {
  constructor() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  getToken(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  getUser(): AuthUser | null {
    const storedUser = sessionStorage.getItem(USER_KEY);
    if (storedUser === null) {
      return null;
    }

    const user: unknown = JSON.parse(storedUser);
    if (!isAuthUser(user)) {
      throw new Error('Stored session user is invalid');
    }
    return user;
  }

  saveSession(response: LoginResponse): void {
    sessionStorage.setItem(TOKEN_KEY, response.token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(response.user));
  }

  clearSession(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }

  getPreferences(): Partial<UserPreferences> | null {
    const storedPreferences = localStorage.getItem(PREFERENCES_KEY);
    if (storedPreferences === null) {
      return null;
    }
    const preferences: unknown = JSON.parse(storedPreferences);
    if (!isUserPreferences(preferences)) {
      throw new Error('Stored preferences are invalid');
    }
    return preferences;
  }

  savePreferences(preferences: UserPreferences): void {
    localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
  }
}
