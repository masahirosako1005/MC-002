import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, sessionInvalidEvent } from './api';
import { ErrorNotice, Icon } from './ui';

export function Recovery({ onRecovered }: { onRecovered: () => Promise<void> }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [issued, setIssued] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const invalidated = () => {
      setIssued('');
      setCode('');
      setOpen(false);
    };
    window.addEventListener(sessionInvalidEvent, invalidated);
    return () => window.removeEventListener(sessionInvalidEvent, invalidated);
  }, []);
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else dialog.current?.close();
  }, [open]);
  const close = () => {
    if (lock.current) return;
    setIssued('');
    setCode('');
    setError('');
    setMessage('');
    setOpen(false);
    trigger.current?.focus();
  };
  const issue = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setMessage('');
    setIssued('');
    try {
      const result = await api.recovery();
      setIssued(result.recovery_code);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const recover = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setMessage('');
    setIssued('');
    try {
      await api.recover(code.trim());
      setCode('');
      await onRecovered();
      setMessage('手帳を引き継ぎました。訪問や次の旅を確認できます。');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return (
    <>
      <button
        ref={trigger}
        className="recovery-trigger"
        aria-label="手帳の引き継ぎをひらく"
        onClick={() => setOpen(true)}
      >
        <Icon name="book" />
        <small>引き継ぎ</small>
      </button>
      <dialog
        className="recovery-dialog"
        ref={dialog}
        aria-labelledby="recovery-title"
        onCancel={(e) => {
          e.preventDefault();
          close();
        }}
        onClose={() => {
          setIssued('');
          setCode('');
          setError('');
          setMessage('');
          setOpen(false);
        }}
      >
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">記録を、次の旅へ。</p>
            <h2 id="recovery-title">手帳の引き継ぎ</h2>
          </div>
          <button
            className="round-button"
            onClick={close}
            disabled={busy}
            aria-label="引き継ぎを閉じる"
          >
            <Icon name="close" />
          </button>
        </div>
        <p className="recovery-description">
          別のブラウザーでも手帳を開ける合言葉です。大切に保管してください。
        </p>
        <section className="recovery-section">
          <h3>この手帳を持ち出す</h3>
          <p>
            合言葉を発行し、自分だけが見られる場所に控えてください。再発行すると、前の合言葉は使えなくなります。
          </p>
          {issued ? (
            <div className="recovery-issued" role="status">
              <label htmlFor="issued-code">今回の合言葉</label>
              <textarea
                id="issued-code"
                readOnly
                value={issued}
                rows={3}
                autoComplete="off"
                spellCheck={false}
              />
              <p>この画面を閉じると表示されなくなります。他の人には教えないでください。</p>
            </div>
          ) : (
            <button className="button secondary" disabled={busy} onClick={() => void issue()}>
              {busy ? '処理しています…' : '合言葉を発行する'}
            </button>
          )}
        </section>
        <section className="recovery-section">
          <h3>以前の手帳をひらく</h3>
          <p>控えた合言葉で、以前の手帳へ切り替えます。今の手帳の記録とは統合されません。</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void recover();
            }}
          >
            <label htmlFor="recovery-code">合言葉</label>
            <input
              id="recovery-code"
              type="password"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              minLength={8}
              maxLength={200}
              autoComplete="off"
              spellCheck={false}
            />
            <button className="button" type="submit" disabled={busy || !code.trim()}>
              {busy ? '処理しています…' : 'この手帳を引き継ぐ'}
              <Icon name="arrow" />
            </button>
          </form>
        </section>
        {error && <ErrorNotice message={error} />}{' '}
        {message && (
          <p className="success-message" role="status">
            <Icon name="check" />
            {message}
          </p>
        )}
      </dialog>
    </>
  );
}
