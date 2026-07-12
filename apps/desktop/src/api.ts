export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001';

type ApiProblem = {
  code?: string;
  message?: string;
  detail?: unknown;
};

export async function apiFetch<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const response = await request(`${API_BASE}${path}`, {
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
  const response = await request(`${API_BASE}${path}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Client-Version': 'deep-dig-desktop/0.1.0',
    },
  });
  if (!response.ok) throw await readProblem(response);
  return response.arrayBuffer();
}

export async function apiPublicFetch<T>(path: string): Promise<T> {
  const response = await request(`${API_BASE}${path}`, {});
  if (!response.ok) throw await readProblem(response);
  return response.json();
}

async function request(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (error) {
    const reason = error instanceof Error && error.message ? ` (${error.message})` : '';
    throw new Error(`Cannot reach the Deep Dig API at ${API_BASE}${reason}. Check that the backend is running.`);
  }
}

async function readProblem(response: Response): Promise<ApiProblem> {
  try {
    return await response.json();
  } catch {
    return { code: 'HTTP_ERROR', message: response.statusText || 'Request failed' };
  }
}
