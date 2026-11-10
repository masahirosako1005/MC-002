import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Tag, User } from "./types";
import { privateImage, stageFrame } from "./api";
export function Icon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  const paths: Record<string, ReactNode> = {
    filter: (
      <>
        <path d="M4 6h16M4 12h16M4 18h16" />
        <circle cx="9" cy="6" r="2" fill="currentColor" />
        <circle cx="16" cy="12" r="2" fill="currentColor" />
        <circle cx="7" cy="18" r="2" fill="currentColor" />
      </>
    ),
    cup: (
      <>
        <path d="M4 8h12v7a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5ZM16 9h2a3 3 0 0 1 0 6h-2M7 3v2m5-2v2M3 22h15" />
      </>
    ),
    wave: (
      <path d="M2 7c3-4 5 4 8 0s5 4 8 0 4 0 4 0M2 12c3-4 5 4 8 0s5 4 8 0 4 0 4 0M2 17c3-4 5 4 8 0s5 4 8 0 4 0 4 0" />
    ),
    home: (
      <>
        <path d="m3 10 9-7 9 7v10H3Z" />
        <path d="M9 20v-7h6v7" />
      </>
    ),
    people: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M17 14a5 5 0 0 1 4 5v2" />
      </>
    ),
    compass: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m16 8-2 6-6 2 2-6Z" />
      </>
    ),
    plus: <path d="M12 4v16M4 12h16" />,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    photo: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <circle cx="8" cy="9" r="1" />
        <path d="m4 18 6-6 4 3 3-5 4 6" />
      </>
    ),
    pin: (
      <>
        <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z" />
        <circle cx="12" cy="10" r="2" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    leaf: (
      <>
        <path d="M20 3C6 1 2 9 6 16s16 3 14-13ZM4 21 16 9" />
      </>
    ),
    logout: (
      <>
        <path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 3v4m10-4v4M3 11h18" />
      </>
    ),
    refresh: (
      <>
        <path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5" />
      </>
    ),
  };
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.compass}
    </svg>
  );
}
export function Avatar({
  user,
  small = false,
}: {
  user: Pick<User, "name" | "initials" | "color">;
  small?: boolean;
}) {
  return (
    <span className={`avatar ${small ? "small" : ""}`} aria-label={user.name}>
      {user.initials}
    </span>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return message ? (
    <p className="error-box" role="alert">
      {message}
    </p>
  ) : null;
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Icon name="leaf" />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function TagPicker({
  tags,
  value,
  onChange,
  disabled = false,
  label = "タグを選ぶ",
}: {
  tags: Tag[];
  value: string[];
  onChange: (v: string[]) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <fieldset className="tag-picker" disabled={disabled}>
      <legend>{label}</legend>
      <div className="tag-options">
        {tags.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`chip ${value.includes(t.id) ? "selected" : ""}`}
            aria-pressed={value.includes(t.id)}
            onClick={() =>
              onChange(
                value.includes(t.id)
                  ? value.filter((id) => id !== t.id)
                  : [...value, t.id],
              )
            }
          >
            {value.includes(t.id) && <Icon name="check" />}
            {t.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
export function Tags({ ids, tags }: { ids: string[]; tags: Tag[] }) {
  return (
    <div className="tags">
      {ids.map((id) => (
        <span key={id}>#{tags.find((t) => t.id === id)?.label || id}</span>
      ))}
    </div>
  );
}
let modalLocks = 0;
let modalRestore: (() => void) | null = null;
function lockPageScroll() {
  if (modalLocks++ === 0) {
    const root = document.documentElement;
    const body = document.body;
    const rootOverflow = root.style.overflow;
    const bodyOverflow = body.style.overflow;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    root.style.overflow = "hidden";
    body.style.overflow = "hidden";
    modalRestore = () => {
      root.style.overflow = rootOverflow;
      body.style.overflow = bodyOverflow;
      window.scrollTo({ left: scrollX, top: scrollY, behavior: "instant" });
    };
  }
  return () => {
    modalLocks = Math.max(0, modalLocks - 1);
    if (modalLocks === 0) {
      modalRestore?.();
      modalRestore = null;
    }
  };
}
export function Modal({
  title,
  onClose,
  children,
  busy = false,
  wide = false,
  variant = "default",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  busy?: boolean;
  wide?: boolean;
  variant?: "default" | "conversation";
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const dialog = ref.current;
    const trigger = document.activeElement;
    const unlock = lockPageScroll();
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (trigger instanceof HTMLElement) trigger.focus({ preventScroll: true });
      unlock();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal${wide ? " wide" : ""}${variant === "conversation" ? " modal-conversation" : ""}`}
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!busy) onClose();
      }}
    >
      <div className="modal-head">
        <h2 id={id}>{title}</h2>
        <button
          className="icon-button"
          aria-label="閉じる"
          disabled={busy}
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      <div className="modal-body">{children}</div>
    </dialog>
  );
}
type PhotoProps = {
  src: string;
  alt?: string;
  className?: string;
  priority?: boolean;
};
export function LocalPhoto(props: PhotoProps) {
  return <PhotoContent key={props.src} {...props} />;
}
function PhotoContent({
  src,
  alt = "",
  className = "",
  priority = false,
}: PhotoProps) {
  const [failed, setFailed] = useState(false);
  const [authenticatedSrc, setAuthenticatedSrc] = useState("");
  const needsAuth = stageFrame && src.startsWith("/api/media/");
  useEffect(() => {
    if (!needsAuth) return undefined;
    const controller = new AbortController();
    let objectUrl = "";
    privateImage(src, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return undefined;
        objectUrl = URL.createObjectURL(blob);
        setAuthenticatedSrc(objectUrl);
        return undefined;
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, needsAuth]);
  const resolved = needsAuth ? authenticatedSrc : src;
  return resolved && !failed ? (
    <img
      className={className}
      src={resolved}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      onError={() => setFailed(true)}
    />
  ) : (
    <div className={`photo-fallback ${className}`}>
      <Icon name="photo" />
      <span>
        {needsAuth && !failed
          ? "写真を読み込んでいます"
          : "写真を表示できません"}
      </span>
    </div>
  );
}
export function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("ja-JP", {
        month: "long",
        day: "numeric",
      }).format(date);
}
