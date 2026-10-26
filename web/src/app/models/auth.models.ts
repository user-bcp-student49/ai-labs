export interface LoginRequest {
  username: string;
  password: string;
  client: string;
}

export interface AuthUser {
  username: string;
  displayName?: string;
  role?: string;
}

export interface LoginResponse {
  token: string;
  user: AuthUser;
  expiresIn?: number;
}

export interface UserPreferences {
  theme: string;
  showTips: boolean;
  compact: boolean;
}
