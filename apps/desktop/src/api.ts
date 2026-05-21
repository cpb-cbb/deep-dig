const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

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
  if (!response.ok) throw await response.json();
  return response.json();
}
