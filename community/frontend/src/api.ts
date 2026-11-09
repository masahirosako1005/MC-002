let csrf = "";
let bearer = "";
export const stageFrame = /^\/stage\/(visitor|provider)\/?$/.test(
  window.location.pathname,
);
export function setAccessToken(value: string) {
  bearer = value;
}
function stageEvent(path: string, method: string, ok: boolean) {
  if (!stageFrame) return;
  const type =
    path === "/stage/login"
      ? "session"
      : path === "/media" && method === "POST"
        ? "photo"
        : path.endsWith("/condition-drafts")
          ? "conditions"
          : path.endsWith("/requirements") && method === "PUT"
            ? "requirements"
            : path.endsWith("/recommendations")
              ? "recommendations"
              : path.endsWith("/selections")
                ? "selection"
                : path.includes("/consultations/") && path.endsWith("/messages")
                  ? method === "POST"
                    ? "reply"
                    : "consultation-read"
                  : (path.includes("/provider-plans/") && method === "PATCH") ||
                      (path.includes("/providers/") &&
                        path.endsWith("/plans") &&
                        method === "POST")
                    ? "provider-plan"
                    : path.includes("/travel-parties/") &&
                        path.endsWith("/messages") &&
                        method === "POST"
                      ? "conversation"
                      : null;
  if (type)
    window.parent.postMessage(
      { source: "ko-stage", type, status: ok ? "success" : "failure" },
      window.location.origin,
    );
}
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
  if (!value) bearer = "";
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (stageFrame && bearer) headers.Authorization = `Bearer ${bearer}`;
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
      credentials: stageFrame ? "omit" : "same-origin",
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
    stageEvent(path, method, false);
    throw new ApiError(
      "接続できませんでした。接続を確かめて、もう一度お試しください。",
      0,
    );
  }
  if (!response.ok) {
    stageEvent(path, method, false);
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
      path != "/login" &&
      path != "/stage/login"
    ) {
      csrf = "";
      window.dispatchEvent(new Event("session-invalid"));
    }
    throw new ApiError(detail, response.status);
  }
  const result = (await response.json()) as T;
  stageEvent(path, method, true);
  return result;
}
export async function privateImage(
  url: string,
  signal: AbortSignal,
): Promise<Blob> {
  if (!mediaUrl(url) || !stageFrame || !bearer)
    throw new Error("画像へのアクセスを確認できません");
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${bearer}` },
    credentials: "omit",
    cache: "no-store",
    signal,
  });
  if (
    !response.ok ||
    !response.headers.get("Content-Type")?.startsWith("image/jpeg")
  )
    throw new Error("写真を表示できません");
  return response.blob();
}
export function mediaUrl(url: string): string {
  return /^\/api\/media\/[a-zA-Z0-9_-]+$/.test(url) ? url : "";
}
