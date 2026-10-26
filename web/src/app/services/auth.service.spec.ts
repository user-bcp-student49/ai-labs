import '@angular/compiler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { AuthService } from './auth.service';

vi.mock('axios', () => ({
  default: {
    post: vi.fn()
  }
}));

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new AuthService();
  });

  it('posts the observed login contract and returns response data', async () => {
    const loginResponse = { token: 'fake-token', user: { username: 'student' } };
    vi.mocked(axios.post).mockResolvedValue({ data: loginResponse } as never);

    await expect(service.login('student', 'Workshop123!')).resolves.toEqual(loginResponse);
    expect(axios.post).toHaveBeenCalledWith(
      'http://localhost:8080/auth/login',
      { username: 'student', password: 'Workshop123!', client: 'angular-workshop' },
      { timeout: 5000 }
    );
  });
});
