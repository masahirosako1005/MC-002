import { useRef, useState } from 'react';
import { api, errorMessage } from './api';
import type { Experience, Plan } from './types';
import { ErrorNotice, Icon } from './ui';

export function SaveButton({
  experience,
  plans,
  onSaved,
  reason,
  compact = false,
}: {
  experience: Experience;
  plans: Plan[];
  onSaved: (plan: Plan) => void;
  reason: string;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = useRef(false);
  const saved = plans.some((p) => p.experience_id === experience.id);
  const save = async () => {
    if (lock.current || saved) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      onSaved(await api.save(experience.id, reason));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return (
    <div className="save-control">
      <button
        className={`${compact ? 'text-button' : 'button secondary'} ${saved ? 'is-saved' : ''}`}
        disabled={busy || saved}
        onClick={() => void save()}
        aria-label={`${experience.title}を${saved ? '保存済み' : '次の旅に保存'}`}
      >
        <Icon name={saved ? 'check' : 'bookmark'} />
        {saved ? '次の旅に保存済み' : busy ? '保存しています…' : '次の旅に保存'}
      </button>
      {error && <ErrorNotice message={error} />}
    </div>
  );
}
