import { errorMessage } from "./validation";
import { lazy, Suspense, useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { api, setAccessToken, stageFrame } from "./api";
import type { User } from "./types";
import { Icon } from "./ui";
import type { MotionTrigger } from "./useNavigationMotion";
import "./login.css";
import "./residence.css";
import { SealMark, WoodcutArt } from "./WaArt";
const Registration = lazy(() => import("./Registration"));

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
  const [registering, setRegistering] = useState(false);
  const [registrationBusy, setRegistrationBusy] = useState(false);
  const [registrationNotice, setRegistrationNotice] = useState("");
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
      setError(errorMessage(cause));
      setPassword("");
      setShowPassword(false);
      requestAnimationFrame(() => passwordInput.current?.focus());
    } finally {
      setBusy(false);
    }
  }
  return (
    <main
      className={`welcome-page ${isProvider ? "welcome-provider" : "welcome-traveler"} ${registering ? "welcome-registration" : ""}`}
    >
      <div className="welcome-content">
        <div className="welcome-brand">
          <SealMark className="welcome-brand-seal">講</SealMark>
          <p className="welcome-role">{isProvider ? "事業者" : "旅行者"}</p>
        </div>
        <header className="welcome-heading">
          <h1 id="welcome-signin-title">
            {registering ? "アカウントを作る" : "ログイン"}
          </h1>
        </header>
        {!registering && !isProvider && (
          <div className="welcome-photo">
            <WoodcutArt priority />
          </div>
        )}
        <section
          className="welcome-form-panel"
          aria-labelledby="welcome-signin-title"
        >
          {message && <output className="welcome-message">{message}</output>}
          {registrationNotice && (
            <output className="welcome-message">{registrationNotice}</output>
          )}
          {registering ? (
            <Suspense
              fallback={
                <output className="residence-loading">
                  登録画面をひらいています…
                </output>
              }
            >
              <Registration
                onLogin={onLogin}
                onBusyChange={setRegistrationBusy}
                onLoginNeeded={(createdUsername, notice) => {
                  setUsername(createdUsername);
                  setRegistrationNotice(notice);
                  setPassword("");
                  setRegistering(false);
                }}
              />
            </Suspense>
          ) : (
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
                <span className="welcome-written-line">
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
                </span>
              </label>
              <label className="welcome-field" htmlFor="signin-password">
                パスワード
                <span className="welcome-password welcome-written-line">
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
          )}
          {!isProvider && (
            <button
              className="text-button welcome-account-switch"
              type="button"
              disabled={busy || registrationBusy}
              onClick={() => {
                setRegistering((value) => !value);
                setPassword("");
                setShowPassword(false);
                setError("");
                setRegistrationNotice("");
              }}
            >
              {registering ? "ログインに戻る" : "アカウントを作る"}
            </button>
          )}
        </section>
      </div>
    </main>
  );
}
