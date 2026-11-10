import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Post } from "./types";
import { errorMessage } from "./validation";

type FeedPage = { items: Post[]; next_cursor: string | null };
type FeedState = FeedPage & { scope: string; loading: boolean; error: string };
const empty: Post[] = [];

export function useCommunityFeed(
  userId: string | null,
  communityId: string,
  revision: number,
) {
  const scope = JSON.stringify([userId, communityId, revision]);
  const [state, setState] = useState<FeedState | null>(null);
  const request = useRef<{
    scope: string;
    controller: AbortController;
    pending: boolean;
  } | null>(null);
  const current = state?.scope === scope ? state : null;
  const enabled = !!userId && !!communityId;
  useEffect(() => {
    if (!userId || !communityId) return undefined;
    const context = { scope, controller: new AbortController(), pending: true };
    request.current = context;
    void api<FeedPage>(
      `/communities/${encodeURIComponent(communityId)}/feed?limit=24`,
      "GET",
      undefined,
      { signal: context.controller.signal },
    )
      .then((page) => {
        if (!context.controller.signal.aborted && request.current === context)
          setState({ ...page, scope, loading: false, error: "" });
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!context.controller.signal.aborted && request.current === context)
          setState({
            scope,
            items: [],
            next_cursor: null,
            loading: false,
            error: errorMessage(cause),
          });
      })
      .finally(() => {
        context.pending = false;
      });
    return () => {
      context.controller.abort();
      if (request.current === context) request.current = null;
    };
  }, [userId, communityId, scope]);

  async function loadMore() {
    const context = request.current;
    if (
      !enabled ||
      !current?.next_cursor ||
      !context ||
      context.scope !== scope ||
      context.pending
    )
      return;
    context.pending = true;
    const cursor = current.next_cursor;
    setState((previous) =>
      previous?.scope === scope
        ? { ...previous, loading: true, error: "" }
        : previous,
    );
    try {
      const page = await api<FeedPage>(
        `/communities/${encodeURIComponent(communityId)}/feed?limit=24&before=${encodeURIComponent(cursor)}`,
        "GET",
        undefined,
        { signal: context.controller.signal },
      );
      if (context.controller.signal.aborted || request.current !== context)
        return;
      setState((previous) => {
        if (previous?.scope !== scope) return previous;
        const existing = new Set(previous.items.map((item) => item.id));
        return {
          scope,
          items: [
            ...previous.items,
            ...page.items.filter((item) => !existing.has(item.id)),
          ],
          next_cursor: page.next_cursor,
          loading: false,
          error: "",
        };
      });
    } catch (cause) {
      if (!context.controller.signal.aborted && request.current === context)
        setState((previous) =>
          previous?.scope === scope
            ? { ...previous, loading: false, error: errorMessage(cause) }
            : previous,
        );
    } finally {
      context.pending = false;
    }
  }

  return {
    items: enabled ? current?.items || empty : empty,
    loading: enabled && (!current || current.loading),
    error: enabled ? current?.error || "" : "",
    nextCursor: enabled ? current?.next_cursor || null : null,
    loadMore,
  };
}
