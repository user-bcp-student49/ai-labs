import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import merge from 'lodash/merge';
import { AuthService } from '../services/auth.service';
import { SessionService } from '../services/session.service';
import { AuthUser, UserPreferences } from '../models/auth.models';
import { getErrorMessage } from '../utils/error-message';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username = '';
  password = '';
  busy = false;
  message = '';
  preferences: UserPreferences = { theme: 'light', showTips: true, compact: false };

  constructor(
    private router: Router,
    private authService: AuthService,
    private sessionService: SessionService
  ) {
    try {
      const storedPreferences = this.sessionService.getPreferences();
      if (storedPreferences) {
        this.preferences = merge(this.preferences, storedPreferences);
      }
    } catch (error) {
      console.log('Preferences could not be loaded', error);
    }
  }

  async login(): Promise<void> {
    this.message = '';
    if (!this.username.trim()) {
      this.message = 'Ingrese un usuario.';
      return;
    }

    if (!this.password.trim()) {
      this.message = 'Ingrese una contraseña.';
      return;
    }

    this.busy = true;
    try {
      const response = await this.authService.login(this.username, this.password);
      if (!response?.token) {
        this.message = 'El backend respondió sin token.';
        return;
      }
      this.sessionService.saveSession(response);
      this.sessionService.savePreferences(this.preferences);
      await this.router.navigate(['/dashboard']);
    } catch (error: unknown) {
      const backendMessage = getErrorMessage(error, 'Error desconocido');
      this.message = `No se pudo autenticar a ${this.username}. ${backendMessage}`;
      console.error(error);
    } finally {
      this.busy = false;
    }
  }
}
