import { useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { api, setAccessToken, stageFrame } from "./api";
import type { User } from "./types";
import { Icon } from "./ui";
import type { MotionTrigger } from "./useNavigationMotion";
import "./login.css";

export default function Login({
  onLogin,
  message,
}: {
  onLogin: (user: User, token: string, trigger: MotionTrigger) => void;
  message: string;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const passwordInput = useRef<HTMLInputElement>(null);
  const submitTrigger = useRef<MotionTrigger>("keyboard");
  const isProvider = window.location.pathname === "/stage/provider";
  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const trigger = submitTrigger.current;
    submitTrigger.current = "keyboard";
    setBusy(true);
    setError("");
    try {
      const result = await api<{
        user: User;
        csrf_token: string;
        access_token?: string;
      }>(stageFrame ? "/stage/login" : "/login", "POST", {
        username: username.trim(),
        password,
      });
      setPassword("");
      setShowPassword(false);
      if (result.access_token) setAccessToken(result.access_token);
      onLogin(result.user, result.csrf_token, trigger);
    } catch (cause) {
      setError((cause as Error).message);
      setPassword("");
      setShowPassword(false);
      requestAnimationFrame(() => passwordInput.current?.focus());
    } finally {
      setBusy(false);
    }
  }
  return (
    <main
      className={`welcome-page ${isProvider ? "welcome-provider" : "welcome-traveler"}`}
    >
      <div className="welcome-content">
        <div className="welcome-brand">
          <span className="brand-mark" aria-label="講">
            講
          </span>
        </div>
        <header className="welcome-heading">
          <p className="welcome-role">{isProvider ? "事業者" : "旅行者"}</p>
          <h1 id="welcome-signin-title">ログイン</h1>
        </header>
        <div className="welcome-photo">
          <img
            src="/welcome-woodland-97a0e1c711d0.webp"
            alt="秋の木立の道を歩く旅行者"
            width={640}
            height={320}
            decoding="async"
          />
        </div>
        <section
          className="welcome-form-panel"
          aria-labelledby="welcome-signin-title"
        >
          {message && (
            <p className="welcome-message" role="status">
              {message}
            </p>
          )}
          <form
            className="welcome-form"
            onSubmit={submit}
            aria-busy={busy}
            onKeyDownCapture={() => {
              submitTrigger.current = "keyboard";
            }}
          >
            <label className="welcome-field" htmlFor="signin-username">
              アカウント名
              <input
                id="signin-username"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                required
                maxLength={40}
                value={username}
                onChange={(event) => {
                  setUsername(event.target.value);
                  setError("");
                }}
                disabled={busy}
                aria-invalid={!!error}
                aria-describedby={error ? "signin-error" : undefined}
              />
            </label>
            <label className="welcome-field" htmlFor="signin-password">
              パスワード
              <span className="welcome-password">
                <input
                  ref={passwordInput}
                  id="signin-password"
                  aria-label="パスワード"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  maxLength={128}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    setError("");
                  }}
                  disabled={busy}
                  aria-invalid={!!error}
                  aria-describedby={error ? "signin-error" : undefined}
                />
                <button
                  type="button"
                  className="welcome-password-toggle"
                  aria-label={
                    showPassword ? "パスワードを隠す" : "パスワードを表示"
                  }
                  aria-pressed={showPassword}
                  disabled={busy}
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? "隠す" : "表示"}
                </button>
              </span>
            </label>
            {error && (
              <p className="welcome-error" id="signin-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button primary welcome-submit"
              onPointerDown={() => {
                submitTrigger.current = "pointer";
              }}
              type="submit"
              disabled={busy || !username.trim() || !password}
            >
              <span>{busy ? "ログインしています…" : "ログイン"}</span>
              <Icon name="arrow" />
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
