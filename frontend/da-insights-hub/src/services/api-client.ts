import { config } from '@/lib/config';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

const headers = (): Record<string, string> => {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (config.apiKey) {
    h['x-api-key'] = config.apiKey;
  }
  return h;
};

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${config.apiBaseUrl}${path}`, { headers: headers() });
    return handleResponse<T>(res);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${config.apiBaseUrl}${path}`, {
      method: 'POST',
      headers: headers(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },

  async postFormData<T>(path: string, formData: FormData): Promise<T> {
    const h: Record<string, string> = {};
    if (config.apiKey) {
      h['x-api-key'] = config.apiKey;
    }
    const res = await fetch(`${config.apiBaseUrl}${path}`, {
      method: 'POST',
      headers: h,
      body: formData,
    });
    return handleResponse<T>(res);
  },

  async delete<T>(path: string): Promise<T> {
    const res = await fetch(`${config.apiBaseUrl}${path}`, {
      method: 'DELETE',
      headers: headers(),
    });
    return handleResponse<T>(res);
  },

  async getRaw(path: string): Promise<Response> {
    return fetch(`${config.apiBaseUrl}${path}`, { headers: headers() });
  },
};
