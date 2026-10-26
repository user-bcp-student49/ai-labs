import { Injectable } from '@angular/core';
import axios from 'axios';
import { LoginRequest, LoginResponse } from '../models/auth.models';
import { environment } from '../../environments/environment';

const LOGIN_TIMEOUT_MS = 5000;
const LOGIN_CLIENT = 'angular-workshop';

@Injectable({ providedIn: 'root' })
export class AuthService {
  async login(username: string, password: string): Promise<LoginResponse> {
    const request: LoginRequest = {
      username,
      password,
      client: LOGIN_CLIENT
    };
    const response = await axios.post<LoginResponse>(
      `${environment.authApiUrl}/auth/login`,
      request,
      { timeout: LOGIN_TIMEOUT_MS }
    );
    return response.data;
  }
}
