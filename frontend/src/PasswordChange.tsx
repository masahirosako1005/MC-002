import { useEffect, useId, useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { api } from "./api";
import { Modal } from "./ui";
import { errorMessage, passwordLength } from "./validation";

type Field = "current" | "new" | "confirmation";

export default function PasswordChange({
  onClose,
  onChanged,
}: {
  onClose: () => void;
  onChanged: () => void;
}) {
  const id = useId();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [invalidField, setInvalidField] = useState<Field | null>(null);
  const currentInput = useRef<HTMLInputElement>(null);
  const newInput = useRef<HTMLInputElement>(null);
  const confirmationInput = useRef<HTMLInputElement>(null);
  const errorElement = useRef<HTMLParagraphElement>(null);
  const request = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      request.current?.abort();
    };
  }, []);

  function clearError() {
    setError("");
    setInvalidField(null);
  }

  function invalid(field: Field, message: string) {
    setError(message);
    setInvalidField(field);
    const target = field === "current" ? currentInput : field === "new" ? newInput : confirmationInput;
    requestAnimationFrame(() => target.current?.focus());
  }

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current) return;
    if (!currentPassword) return invalid("current", "現在のパスワードを入力してください。");
    if (passwordLength(currentPassword) > 128)
      return invalid("current", "現在のパスワードは128文字以内で入力してください。");
    if (passwordLength(newPassword) < 12 || passwordLength(newPassword) > 128)
      return invalid("new", "新しいパスワードは12〜128文字で入力してください。");
    if (currentPassword === newPassword)
      return invalid("new", "現在と異なるパスワードを入力してください。");
    if (confirmation !== newPassword)
      return invalid("confirmation", "確認用のパスワードが一致しません。もう一度入力してください。");

    lock.current = true;
    setBusy(true);
    clearError();
    const controller = new AbortController();
    request.current = controller;
    try {
      await api<{ ok: true; reauthentication_required: true }>(
        "/account/password", "POST",
        { current_password: currentPassword, new_password: newPassword },
        { signal: controller.signal },
      );
      if (!alive.current) return;
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setVisible(false);
      onChanged();
    } catch (cause) {
      if (!alive.current || controller.signal.aborted) return;
      setError(errorMessage(cause));
      requestAnimationFrame(() => errorElement.current?.focus());
    } finally {
      lock.current = false;
      if (alive.current) setBusy(false);
    }
  }

  return (
    <Modal title="パスワードを変更する" onClose={onClose} busy={busy}>
      <p className="muted" id={`${id}-help`}>
        変更後は、このアカウントで開いているすべての画面で、もう一度ログインが必要です。
      </p>
      <form onSubmit={submit} noValidate aria-busy={busy} aria-describedby={`${id}-help`}>
        <fieldset className="editor-fields" disabled={busy}>
          <legend className="sr-only">現在と新しいパスワード</legend>
          <label className="field" htmlFor={`${id}-current`}>
            現在のパスワード
            <input id={`${id}-current`} ref={currentInput} name="current-password"
              type={visible ? "text" : "password"} autoComplete="current-password"
              required maxLength={256} value={currentPassword} spellCheck={false}
              autoCapitalize="none" autoCorrect="off"
              aria-invalid={invalidField === "current" || undefined}
              aria-describedby={invalidField === "current" ? `${id}-error` : undefined}
              onChange={(event) => { setCurrentPassword(event.target.value); clearError(); }} />
          </label>
          <label className="field" htmlFor={`${id}-new`}>
            新しいパスワード
            <input id={`${id}-new`} ref={newInput} name="new-password"
              type={visible ? "text" : "password"} autoComplete="new-password"
              required maxLength={256} value={newPassword} spellCheck={false}
              autoCapitalize="none" autoCorrect="off"
              aria-invalid={invalidField === "new" || undefined}
              aria-describedby={`${id}-length${invalidField === "new" ? ` ${id}-error` : ""}`}
              onChange={(event) => { setNewPassword(event.target.value); clearError(); }} />
          </label>
          <p className="quiet-note" id={`${id}-length`}>12〜128文字。よく使われるパスワードは避けてください。</p>
          <label className="field" htmlFor={`${id}-confirmation`}>
            新しいパスワードの確認
            <input id={`${id}-confirmation`} ref={confirmationInput} name="confirm-new-password"
              type={visible ? "text" : "password"} autoComplete="new-password"
              required maxLength={256} value={confirmation} spellCheck={false}
              autoCapitalize="none" autoCorrect="off"
              aria-invalid={invalidField === "confirmation" || undefined}
              aria-describedby={invalidField === "confirmation" ? `${id}-error` : undefined}
              onChange={(event) => { setConfirmation(event.target.value); clearError(); }} />
          </label>
          <button type="button" className="text-button" aria-pressed={visible} onClick={() => setVisible((value) => !value)}>
            {visible ? "入力したパスワードを隠す" : "入力したパスワードを表示する"}
          </button>
        </fieldset>
        {error && <p id={`${id}-error`} ref={errorElement} className="error-box" role="alert" tabIndex={-1}>{error}</p>}
        <div className="dialog-actions">
          <button type="button" className="button secondary" disabled={busy} onClick={onClose}>変更せずに戻る</button>
          <button type="submit" className="button primary" disabled={busy}>{busy ? "変更しています…" : "パスワードを変更する"}</button>
        </div>
      </form>
    </Modal>
  );
}
