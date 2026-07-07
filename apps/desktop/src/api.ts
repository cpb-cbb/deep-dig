export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type ApiProblem = {
  code?: string;
  message?: string;
  detail?: unknown;
};

export async function apiFetch<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-Client-Version': 'deep-dig-desktop/0.1.0',
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) throw await readProblem(response);
  return response.json();
}

export async function apiDownload(path: string, token: string): Promise<ArrayBuffer> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Client-Version': 'deep-dig-desktop/0.1.0',
    },
  });
  if (!response.ok) throw await readProblem(response);
  return response.arrayBuffer();
}

async function readProblem(response: Response): Promise<ApiProblem> {
  try {
    return await response.json();
  } catch {
    return { code: 'HTTP_ERROR', message: response.statusText || 'Request failed' };
  }
}
