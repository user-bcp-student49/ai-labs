import axios from 'axios';

export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const responseData: unknown = error.response?.data;
    if (typeof responseData === 'object' && responseData !== null) {
      const data = responseData as Record<string, unknown>;
      const message = data.message ?? data.detail;
      if (typeof message === 'string') {
        return message;
      }
    }
    return error.message || fallback;
  }

  return error instanceof Error ? error.message : fallback;
}
