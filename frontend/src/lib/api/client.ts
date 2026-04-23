const PUBLIC_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const INTERNAL_API_BASE_URL =
  process.env.INTERNAL_API_BASE_URL ?? PUBLIC_API_BASE_URL;

export const API_BASE_URL =
  typeof window === "undefined" ? INTERNAL_API_BASE_URL : PUBLIC_API_BASE_URL;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

export async function fetchFromApi<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = options.body === undefined ? undefined : { "Content-Type": "application/json" };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      if (payload.error?.message) {
        detail = payload.error.message;
      }
    } catch {
      // Ignore non-JSON error bodies
    }
    throw new Error(`API request failed: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
