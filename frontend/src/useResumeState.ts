import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import { errorMessage } from "./validation";

export type DiscoveryFilters = {
  query: string;
  category: string;
  duration: "all" | "day" | "overnight";
  schedule: "all" | "dated" | "on_request";
  area: string;
};
export const emptyDiscoveryFilters: DiscoveryFilters = {
  query: "", category: "", duration: "all", schedule: "all", area: "",
};
export type ResumeContent = {
  page: "feed" | "market" | "circles" | "journal" | "provider" | "daytrip";
  community_id: string | null;
  circle_id: string | null;
  filters: DiscoveryFilters;
};
export type ResumeState = ResumeContent & { version: number };
function signature(value: ResumeContent): string {
  return JSON.stringify([value.page, value.community_id, value.circle_id,
    value.filters.query.trim(), value.filters.category, value.filters.duration,
    value.filters.schedule, value.filters.area]);
}

/** One initial restore per account, serialized CAS writes, no private storage. */
export function useResumeState(userId: string | null) {
  const [restore, setRestore] = useState<{ userId: string; state: ResumeState } | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const epoch = useRef(0);
  const owner = useRef<string | null>(null);
  const acknowledged = useRef<ResumeState | null>(null);
  const queued = useRef<ResumeContent | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const writing = useRef(false);
  const blocked = useRef(false);
  const pendingRestore = useRef<ResumeState | null>(null);

  const reset = useCallback(() => {
    epoch.current++;
    owner.current = null;
    acknowledged.current = null;
    queued.current = null;
    writing.current = false;
    blocked.current = false;
    pendingRestore.current = null;
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => {
    reset();
    setRestore(null);
    setError("");
    setNotice("");
    if (!userId) return reset;
    owner.current = userId;
    const generation = epoch.current;
    void api<ResumeState>("/me/resume-state").then((state) => {
      if (generation !== epoch.current) return undefined;
      acknowledged.current = state;
      setRestore({ userId, state });
      return undefined;
    }).catch((cause: unknown) => {
      if (generation === epoch.current) setError(errorMessage(cause));
    });
    return reset;
  }, [userId, retryKey, reset]);

  const queue = useCallback((content: ResumeContent) => {
    if (!owner.current || !acknowledged.current || blocked.current) return;
    const normalized = { ...content, filters: { ...content.filters, query: content.filters.query.trim() } };
    queued.current = normalized;
    if (timer.current) clearTimeout(timer.current);
    const generation = epoch.current;
    const account = owner.current;
    async function flush() {
      timer.current = null;
      if (generation !== epoch.current || writing.current || blocked.current) return;
      const next = queued.current;
      const previous = acknowledged.current;
      queued.current = null;
      if (!next || !previous || signature(next) === signature(previous)) return;
      writing.current = true;
      try {
        const saved = await api<ResumeState>("/me/resume-state", "PUT", { ...next, version: previous.version });
        if (generation !== epoch.current) return;
        acknowledged.current = saved;
        setError("");
      } catch (cause: unknown) {
        if (generation !== epoch.current) return;
        queued.current = null;
        if (cause instanceof ApiError && [409, 404, 422].includes(cause.status)) {
          // Discard the conflicting operation; do not retry it with a fresh version.
          blocked.current = true;
          pendingRestore.current = null;
          try {
            const latest = await api<ResumeState>("/me/resume-state");
            if (generation !== epoch.current) return;
            acknowledged.current = latest;
            pendingRestore.current = latest;
            setRestore({ userId: account, state: latest });
            setNotice(cause.status === 409
              ? "別の画面で変更された保存状態を読み込みました。"
              : "現在利用できるコミュニティ・講・条件に更新しました。");
            setError("");
          } catch (refreshCause: unknown) {
            if (generation === epoch.current) setError(errorMessage(refreshCause));
          }
        } else setError(`再開する画面を保存できませんでした。${errorMessage(cause)}`);
      } finally {
        if (generation === epoch.current) {
          writing.current = false;
          if (queued.current && !blocked.current) timer.current = setTimeout(() => void flush(), 400);
        }
      }
    }
    timer.current = setTimeout(() => void flush(), 400);
  }, []);

  const applied = useCallback((state: ResumeState) => {
    if (pendingRestore.current === state) {
      blocked.current = false;
      pendingRestore.current = null;
    }
  }, []);
  const retry = useCallback(() => setRetryKey((value) => value + 1), []);
  return { restore: restore?.userId === userId ? restore : null, error, notice, queue, reset, applied, retry };
}
