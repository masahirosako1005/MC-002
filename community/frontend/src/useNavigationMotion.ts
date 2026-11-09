import { useEffect, useLayoutEffect, useRef } from "react";

export type MotionTrigger = "pointer" | "keyboard" | "programmatic";
type MotionKind = "login" | "navigation";

/** Animate only the newly rendered main content; keep no outgoing account DOM. */
export function useNavigationMotion(
  route: string,
  authenticated: boolean,
  ready: boolean,
) {
  const target = useRef<HTMLElement | null>(null);
  const pending = useRef<{ kind: MotionKind; trigger: MotionTrigger } | null>(
    null,
  );
  const animation = useRef<Animation | null>(null);
  const sequence = useRef(0);

  function cancel() {
    animation.current?.cancel();
    animation.current = null;
    if (target.current) target.current.dataset.motionState = "idle";
  }
  function request(kind: MotionKind, trigger: MotionTrigger) {
    cancel();
    pending.current = { kind, trigger };
  }
  function reset() {
    pending.current = null;
    cancel();
  }

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onPreference = () => {
      if (reduced.matches) cancel();
    };
    const onKeyboard = () => cancel();
    reduced.addEventListener("change", onPreference);
    document.addEventListener("keydown", onKeyboard, true);
    return () => {
      reduced.removeEventListener("change", onPreference);
      document.removeEventListener("keydown", onKeyboard, true);
      cancel();
    };
  }, []);

  useLayoutEffect(() => {
    cancel();
    if (!authenticated) {
      pending.current = null;
      return;
    }
    if (!ready || !target.current || !pending.current) return;
    const node = target.current;
    const intent = pending.current;
    pending.current = null;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    node.dataset.motionKind = intent.kind;
    node.dataset.motionTrigger = intent.trigger;
    node.dataset.motionPolicy = reduced ? "reduced" : intent.trigger;
    node.dataset.motionSequence = String(++sequence.current);
    node.dataset.motionState = "idle";
    if (
      reduced ||
      intent.trigger !== "pointer" ||
      typeof node.animate !== "function"
    )
      return;
    const current = node.animate(
      [
        {
          opacity: 0,
          transform: `translateY(${intent.kind === "login" ? 8 : 5}px)`,
        },
        { opacity: 1, transform: "translateY(0)" },
      ],
      {
        duration: intent.kind === "login" ? 220 : 170,
        easing: "cubic-bezier(0.2, 0.8, 0.2, 1)",
        fill: "none",
      },
    );
    animation.current = current;
    node.dataset.motionState = "running";
    current.onfinish = () => {
      if (animation.current === current) {
        animation.current = null;
        node.dataset.motionState = "idle";
      }
    };
    return () => cancel();
  }, [route, authenticated, ready]);

  return { target, request, reset };
}
