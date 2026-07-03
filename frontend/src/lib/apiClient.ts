export interface ApiClientOptions {
  baseUrl?: string;
  token?: string;
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

/** Resolve the API base URL from Vite env or the local dev default. */
export function resolveApiBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (typeof fromEnv === "string" && fromEnv.trim().length > 0) {
    return fromEnv.trim().replace(/\/$/, "");
  }
  return DEFAULT_API_BASE_URL;
}

/** Build an ApiClient, optionally attaching a bearer token. */
export function createApiClient(accessToken?: string | null): ApiClient {
  return new ApiClient({ token: accessToken ?? undefined });
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

/** Extract a readable message from a FastAPI-style error JSON body. */
export function parseApiErrorMessage(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null) {
    return fallback;
  }

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }

  if (!Array.isArray(detail)) {
    return fallback;
  }

  const messages = detail
    .map((item) => {
      if (typeof item !== "object" || item === null) {
        return null;
      }
      const msg = (item as { msg?: unknown }).msg;
      if (typeof msg !== "string" || msg.length === 0) {
        return null;
      }
      const loc = (item as { loc?: unknown }).loc;
      if (Array.isArray(loc)) {
        const field = loc
          .filter((part): part is string => typeof part === "string")
          .join(".");
        return field.length > 0 ? `${field}: ${msg}` : msg;
      }
      return msg;
    })
    .filter((message): message is string => message !== null);

  return messages.length > 0 ? messages.join(" ") : fallback;
}

export class ApiClient {
  private readonly baseUrl: string;

  private readonly token?: string;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? resolveApiBaseUrl();
    this.token = options.token;
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  }

  async delete(path: string): Promise<void> {
    await this.requestVoid(path, { method: "DELETE" });
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async requestVoid(path: string, init: RequestInit): Promise<void> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) {
      let message = response.statusText;
      try {
        const errorBody: unknown = await response.json();
        message = parseApiErrorMessage(errorBody, message);
      } catch {
        // Keep the status text when the error body is not JSON.
      }
      throw new ApiError(message, response.status);
    }
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined) {
      headers.set("Content-Type", "application/json");
    }
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) {
      let message = response.statusText;
      try {
        const errorBody: unknown = await response.json();
        message = parseApiErrorMessage(errorBody, message);
      } catch {
        // Keep the status text when the error body is not JSON.
      }
      throw new ApiError(message, response.status);
    }
    return (await response.json()) as T;
  }
}
