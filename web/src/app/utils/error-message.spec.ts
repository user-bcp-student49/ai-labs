import { describe, expect, it } from 'vitest';
import axios from 'axios';
import { getErrorMessage } from './error-message';

describe('getErrorMessage', () => {
  it('uses a backend message or detail from an Axios error', () => {
    const messageError = new axios.AxiosError('request failed');
    messageError.response = { data: { message: 'Invalid credentials' } } as never;
    expect(getErrorMessage(messageError, 'fallback')).toBe('Invalid credentials');

    const detailError = new axios.AxiosError('request failed');
    detailError.response = { data: { detail: 'Not authorized' } } as never;
    expect(getErrorMessage(detailError, 'fallback')).toBe('Not authorized');
  });

  it('falls back for unknown errors and empty Axios messages', () => {
    expect(getErrorMessage('unexpected', 'fallback')).toBe('fallback');
    expect(getErrorMessage(new axios.AxiosError(''), 'fallback')).toBe('fallback');
  });

  it('uses a regular Error message', () => {
    expect(getErrorMessage(new Error('network error'), 'fallback')).toBe('network error');
  });
});
