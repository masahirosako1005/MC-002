import { useCallback, useEffect, useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { api, ApiError } from "./api";
import ResidenceFields from "./ResidenceFields";
import type { Residence, ResidenceCatalog } from "./ResidenceFields";
import { ErrorBox, Modal } from "./ui";
import { errorMessage } from "./validation";

function ResidenceEditor({
  catalog,
  initial,
  onSaved,
  onReload,
  onBusyChange,
}: {
  catalog: ResidenceCatalog;
  initial: Residence;
  onSaved: () => void;
  onReload: () => void;
  onBusyChange: (value: boolean) => void;
}) {
  const [areaId, setAreaId] = useState(initial.area?.id || "");
  const [shared, setShared] = useState(initial.share_area_analytics);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [incomplete, setIncomplete] = useState(false);
  const request = useRef<AbortController | null>(null);
  const lock = useRef(false);
  useEffect(() => () => request.current?.abort(), []);
  async function save(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current || conflict || incomplete || (shared && !areaId)) return;
    lock.current = true;
    setBusy(true);
    onBusyChange(true);
    setError("");
    const controller = new AbortController();
    request.current = controller;
    try {
      await api<Residence>(
        "/residence/me",
        "PUT",
        {
          residence_area_id: areaId || null,
          share_area_analytics: shared,
          version: initial.version,
        },
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) onSaved();
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(errorMessage(cause));
        setConflict(cause instanceof ApiError && cause.status === 409);
      }
    } finally {
      lock.current = false;
      onBusyChange(false);
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <form className="residence-profile-form" onSubmit={save} aria-busy={busy}>
      <ResidenceFields
        areas={catalog.items}
        areaId={areaId}
        onAreaChange={setAreaId}
        shared={shared}
        onSharedChange={setShared}
        disabled={busy}
        allowUnset
        onIncompleteChange={setIncomplete}
      />
      <p className="residence-note">
        保存した地域と共有設定が、利用した事業者とN西市全体の地域別集計に反映されます。共有を外すと、以後の集計対象から外れます。
      </p>
      <ErrorBox message={error} />
      {incomplete && (
        <p className="residence-note">
          市区町村を選ぶか、「地域を未設定にする」を押してください。
        </p>
      )}
      {conflict && (
        <button className="button secondary" type="button" onClick={onReload}>
          最新の設定を読み直す
        </button>
      )}
      <button
        className="button primary full"
        type="submit"
        disabled={busy || conflict || incomplete || (shared && !areaId)}
      >
        {busy ? "保存しています…" : "地域と共有設定を保存"}
      </button>
    </form>
  );
}

export default function ResidenceProfile({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [result, setResult] = useState<{
    catalog: ResidenceCatalog;
    initial: Residence;
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const load = useCallback(() => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    Promise.all([
      api<ResidenceCatalog>("/residence/areas", "GET", undefined, {
        signal: controller.signal,
      }),
      api<Residence>("/residence/me", "GET", undefined, {
        signal: controller.signal,
      }),
    ])
      .then(([catalog, initial]) => {
        if (!controller.signal.aborted) {
          setResult({ catalog, initial });
          setError("");
        }
        return undefined;
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      });
  }, []);
  useEffect(() => {
    load();
    return () => activeRequest.current?.abort();
  }, [load]);
  function reload() {
    setResult(null);
    setError("");
    load();
  }
  return (
    <Modal title="居住地域と共有設定" onClose={onClose} busy={busy}>
      {result ? (
        <ResidenceEditor
          key={result.initial.version}
          {...result}
          onSaved={onSaved}
          onReload={reload}
          onBusyChange={setBusy}
        />
      ) : error ? (
        <>
          <ErrorBox message={error} />
          <button className="button secondary" onClick={reload}>
            もう一度読み込む
          </button>
        </>
      ) : (
        <output className="residence-loading">
          地域の設定を読み込んでいます…
        </output>
      )}
    </Modal>
  );
}
