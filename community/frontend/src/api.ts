let csrf = "";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const multipart = data instanceof FormData;
  if (method !== "GET") {
    if (!multipart) headers["Content-Type"] = "application/json";
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      credentials: "same-origin",
      cache: "no-store",
      body:
        data === undefined
          ? undefined
          : multipart
            ? data
            : JSON.stringify(data),
      signal: AbortSignal.timeout(45000),
    });
  } catch {
    throw new ApiError(
      "接続できませんでした。接続を確かめて、もう一度お試しください。",
      0,
    );
  }
  if (!response.ok) {
    let detail = "操作を完了できませんでした。もう一度お試しください。";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* Keep a safe local message for non-JSON failures. */
    }
    if (
      (response.status === 401 ||
        response.headers.get("X-Session-Invalid") === "true") &&
      path != "/me" &&
      path != "/login"
    ) {
      csrf = "";
      window.dispatchEvent(new Event("session-invalid"));
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}
export function mediaUrl(url: string): string {
  return /^\/api\/media\/[a-zA-Z0-9_-]+$/.test(url) ? url : "";
}
