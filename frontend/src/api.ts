import type {
  ActiveAttempt,
  Answer,
  Catalog,
  Journal,
  Leaderboard,
  Plan,
  Recommendations,
  Visit,
} from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// Session credentials remain in an HttpOnly cookie. Only the CSRF token is held in memory.
let csrfToken = '';
let sessionPromise: Promise<void> | null = null;
let sessionOpened = false;
export const sessionInvalidEvent = 'journey:session-invalid';
const reconnectMessage =
  '手帳の接続が変わりました。もう一度読み込んでください。以前の記録は「引き継ぎ」から開けます。';

async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      redirect: 'error',
      cache: 'no-store',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
        ...(method !== 'GET' && csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      ...(method !== 'GET' ? { body: JSON.stringify(body ?? {}) } : {}),
    });
    const data: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      if (
        (response.status === 401 && !path.startsWith('/session')) ||
        (response.status === 403 && response.headers.get('X-Session-Invalid') === 'true')
      ) {
        // Never replay a rejected write or silently attach it to a new anonymous journal.
        window.dispatchEvent(new Event(sessionInvalidEvent));
        throw new ApiError(reconnectMessage, response.status);
      }
      const detail =
        data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
          ? data.detail
          : '';
      throw new ApiError(
        detail ||
          (response.status === 401
            ? '旅の手帳を開き直してください。'
            : '読み込めませんでした。もう一度お試しください。'),
        response.status,
      );
    }
    if (data === null) throw new ApiError('受け取った内容を読み込めませんでした。', 502);
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('接続できませんでした。接続を確認して、もう一度お試しください。', 0);
  } finally {
    window.clearTimeout(timeout);
  }
}

async function openSession() {
  type Session = { nickname: string; csrf_token: string };
  let session: Session;
  try {
    session = await request<Session>('/session');
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    if (sessionOpened) throw new ApiError(reconnectMessage, 401);
    session = await request<Session>('/session', 'POST', {});
  }
  csrfToken = session.csrf_token;
  sessionOpened = true;
}

export const api = {
  session() {
    return (sessionPromise ??= openSession().finally(() => {
      sessionPromise = null;
    }));
  },
  catalog: () => request<Catalog>('/catalog'),
  journal: () => request<Journal>('/journal'),
  visit: (spotId: string, code: string) =>
    request<Visit>('/visits', 'POST', { spot_id: spotId, code }),
  start: (gameId: string) => request<ActiveAttempt>('/attempts', 'POST', { game_id: gameId }),
  hint: (id: string) =>
    request<{ hint: string; hints_used: number }>(
      `/attempts/${encodeURIComponent(id)}/hint`,
      'POST',
      {},
    ),
  answer: (id: string, values: number[]) =>
    request<Answer>(`/attempts/${encodeURIComponent(id)}/answer`, 'POST', { values }),
  recommendations: (minutes: number, season: string, interest: string) =>
    request<Recommendations>(
      `/recommendations?${new URLSearchParams({ minutes: String(minutes), season, interest })}`,
    ),
  save: (experienceId: string, reason: string) =>
    request<Plan>('/plans', 'POST', { experience_id: experienceId, reason }),
  remove: (id: string) => request<{ ok: boolean }>(`/plans/${encodeURIComponent(id)}`, 'DELETE'),
  leaderboard: (id: string) =>
    request<Leaderboard>(`/leaderboard?${new URLSearchParams({ game_id: id })}`),
  recovery: () => request<{ recovery_code: string }>('/recovery', 'POST', {}),
  async recover(code: string) {
    const session = await request<{ nickname: string; csrf_token: string }>(
      '/session/recover',
      'POST',
      { recovery_code: code },
    );
    csrfToken = session.csrf_token;
    sessionOpened = true;
    sessionPromise = null;
  },
};

export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'うまく処理できませんでした。もう一度お試しください。';
}
