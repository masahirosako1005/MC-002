import { useCallback, useEffect, useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { api, setAccessToken, stageFrame } from "./api";
import type { User } from "./types";
import type { MotionTrigger } from "./useNavigationMotion";
import ResidenceFields from "./ResidenceFields";
import type { ResidenceCatalog } from "./ResidenceFields";
import { ErrorBox, Icon } from "./ui";
import { errorMessage, passwordLength } from "./validation";

export default function Registration({
  onLogin,
  onLoginNeeded,
  onBusyChange,
}: {
  onLogin: (user: User, token: string, trigger: MotionTrigger) => void;
  onLoginNeeded: (username: string, message: string) => void;
  onBusyChange: (value: boolean) => void;
}) {
  const [catalog, setCatalog] = useState<ResidenceCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [areaId, setAreaId] = useState("");
  const [shared, setShared] = useState(false);
  const [skipArea, setSkipArea] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeRequest = useRef<AbortController | null>(null);
  const catalogRequest = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const trigger = useRef<MotionTrigger>("keyboard");
  const loadCatalog = useCallback(() => {
    catalogRequest.current?.abort();
    const controller = new AbortController();
    catalogRequest.current = controller;
    api<ResidenceCatalog>("/residence/areas", "GET", undefined, {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted) {
          setCatalog(value);
          setCatalogError("");
        }
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setCatalogError(errorMessage(cause));
      });
    return controller;
  }, []);
  useEffect(() => {
    loadCatalog();
    return () => catalogRequest.current?.abort();
  }, [loadCatalog]);
  useEffect(() => () => activeRequest.current?.abort(), []);
  const valid =
    !!name.trim() &&
    /^[a-z0-9_-]{3,40}$/.test(username) &&
    passwordLength(password) >= 12 && passwordLength(password) <= 128 &&
    password === confirmation &&
    (skipArea || !!catalog?.items.some((area) => area.id === areaId));
  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current || !valid) return;
    lock.current = true;
    setBusy(true);
    onBusyChange(true);
    setError("");
    const controller = new AbortController();
    activeRequest.current = controller;
    let created = false;
    try {
      await api(
        "/register",
        "POST",
        {
          username,
          password,
          name: name.trim(),
          residence_area_id: skipArea ? null : areaId,
          share_area_analytics: skipArea ? false : shared,
        },
        { signal: controller.signal },
      );
      created = true;
      if (controller.signal.aborted) return;
      const result = await api<{
        user: User;
        csrf_token: string;
        access_token?: string;
      }>(
        stageFrame ? "/stage/login" : "/login",
        "POST",
        { username, password },
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      setPassword("");
      setConfirmation("");
      if (result.access_token) setAccessToken(result.access_token);
      onLogin(result.user, result.csrf_token, trigger.current);
    } catch (cause) {
      if (controller.signal.aborted) return;
      if (created)
        onLoginNeeded(
          username,
          "アカウントを作成しました。パスワードを入力してログインしてください。",
        );
      else
        setError(
          `${errorMessage(cause)} 登録済みの場合は、ログインしてください。`,
        );
    } finally {
      lock.current = false;
      onBusyChange(false);
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <form
      className="welcome-form registration-form"
      onSubmit={submit}
      aria-busy={busy}
      onKeyDownCapture={() => {
        trigger.current = "keyboard";
      }}
    >
      <label className="welcome-field" htmlFor="register-name">
        表示名
        <span className="welcome-written-line">
          <input
            id="register-name"
            name="name"
            autoComplete="name"
            maxLength={80}
            required
            value={name}
            disabled={busy}
            onChange={(event) => setName(event.target.value)}
          />
        </span>
      </label>
      <label className="welcome-field" htmlFor="register-username">
        アカウント名
        <span className="welcome-written-line">
          <input
            id="register-username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            pattern={"[a-z0-9_\\-]{3,40}"}
            minLength={3}
            maxLength={40}
            required
            value={username}
            disabled={busy}
            onChange={(event) => setUsername(event.target.value)}
            aria-describedby="register-username-help"
          />
        </span>
        <small id="register-username-help">
          半角英小文字・数字・_・-、3〜40文字
        </small>
      </label>
      <label className="welcome-field" htmlFor="register-password">
        パスワード
        <span className="welcome-password welcome-written-line">
          <input
            id="register-password"
            name="new-password"
            type={visible ? "text" : "password"}
            autoComplete="new-password"
            maxLength={256}
            required
            value={password}
            disabled={busy}
            onChange={(event) => setPassword(event.target.value)}
            aria-describedby="register-password-help"
          />
          <button
            className="welcome-password-toggle"
            type="button"
            disabled={busy}
            aria-label={visible ? "パスワードを隠す" : "パスワードを表示"}
            aria-pressed={visible}
            onClick={() => setVisible((value) => !value)}
          >
            {visible ? "隠す" : "表示"}
          </button>
        </span>
        <small id="register-password-help">12〜128文字</small>
      </label>
      <label className="welcome-field" htmlFor="register-confirmation">
        パスワードをもう一度
        <span className="welcome-written-line">
          <input
            id="register-confirmation"
            name="new-password-confirmation"
            type={visible ? "text" : "password"}
            autoComplete="new-password"
            maxLength={256}
            required
            value={confirmation}
            disabled={busy}
            onChange={(event) => setConfirmation(event.target.value)}
            aria-invalid={!!confirmation && password !== confirmation}
            aria-describedby={
              confirmation && password !== confirmation
                ? "register-confirmation-help"
                : undefined
            }
          />
        </span>
        {confirmation && password !== confirmation && (
          <small
            id="register-confirmation-help"
            className="registration-mismatch"
          >
            パスワードが一致していません。
          </small>
        )}
      </label>
      {catalog ? (
        <ResidenceFields
          areas={catalog.items}
          areaId={areaId}
          onAreaChange={setAreaId}
          shared={shared}
          onSharedChange={setShared}
          disabled={busy || skipArea}
        />
      ) : catalogError ? (
        <div>
          <ErrorBox message={catalogError} />
          <button className="text-button" type="button" onClick={loadCatalog}>
            地域を読み直す
          </button>
        </div>
      ) : (
        <output className="residence-loading">
          市区町村を読み込んでいます…
        </output>
      )}
      <label className="residence-sharing">
        <input
          type="checkbox"
          checked={skipArea}
          disabled={busy}
          onChange={(event) => {
            setSkipArea(event.target.checked);
            if (event.target.checked) {
              setAreaId("");
              setShared(false);
            }
          }}
        />
        <span>
          一覧にないため、地域を登録せずに続ける
          <small>
            地域集計には含まれません。あとから居住地域を設定できます。
          </small>
        </span>
      </label>
      <ErrorBox message={error} />
      <button
        className="button primary welcome-submit"
        type="submit"
        disabled={busy || !valid}
        onPointerDown={() => {
          trigger.current = "pointer";
        }}
      >
        <span>{busy ? "登録しています…" : "登録してはじめる"}</span>
        <Icon name="arrow" />
      </button>
    </form>
  );
}
