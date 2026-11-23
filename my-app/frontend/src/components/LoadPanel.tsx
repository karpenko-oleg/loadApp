import { useState } from "react";
import type { LoadJob, LoadKind, LoadProfile } from "../types";

interface Props {
  jobs: LoadJob[];
  onStart: (profile: LoadProfile) => Promise<unknown>;
  onStop: (id: string) => Promise<unknown>;
}

export function LoadPanel({ jobs, onStart, onStop }: Props) {
  const [kind, setKind] = useState<LoadKind>("cpu");
  const [duration, setDuration] = useState(30);
  const [intensity, setIntensity] = useState(0.5);
  const [workers, setWorkers] = useState(1);
  const [memory, setMemory] = useState(64);
  const [disk, setDisk] = useState(16);
  const [concurrency, setConcurrency] = useState(4);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const profile: LoadProfile = { kind, duration_seconds: duration, intensity };
      if (kind === "cpu") profile.workers = workers;
      if (kind === "memory") profile.memory_mb = memory;
      if (kind === "disk") profile.disk_mb = disk;
      if (kind === "http") profile.concurrency = concurrency;
      await onStart(profile);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось запустить задание нагрузки");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="card-heading"><div><span className="eyebrow">управляемый хаос</span><h2>Лаборатория нагрузки</h2></div><span className="pill warning">максимум 2 задания</span></div>
      <p className="panel-copy">Запустите ограниченный профиль, изучите симптом, затем остановите его и объясните восстановление.</p>
      <div className="form-grid">
        <label>Профиль<select value={kind} onChange={(event) => setKind(event.target.value as LoadKind)}><option value="cpu">Нагрузка на CPU</option><option value="memory">Нагрузка на память</option><option value="disk">Дисковый ввод-вывод</option><option value="http">Параллельные HTTP-запросы</option></select></label>
        <label>Длительность (с)<input type="number" min="1" max="300" value={duration} onChange={(event) => setDuration(Number(event.target.value))} /></label>
        <label>Интенсивность<input type="number" min="0" max="1" step="0.1" value={intensity} onChange={(event) => setIntensity(Number(event.target.value))} /></label>
        {kind === "cpu" && <label>Рабочие процессы<input type="number" min="1" max="8" value={workers} onChange={(event) => setWorkers(Number(event.target.value))} /></label>}
        {kind === "memory" && <label>Память (МиБ)<input type="number" min="1" max="512" value={memory} onChange={(event) => setMemory(Number(event.target.value))} /></label>}
        {kind === "disk" && <label>Диск (МиБ)<input type="number" min="1" max="256" value={disk} onChange={(event) => setDisk(Number(event.target.value))} /></label>}
        {kind === "http" && <label>Параллельность<input type="number" min="1" max="50" value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value))} /></label>}
      </div>
      <button className="button primary" onClick={() => void start()} disabled={busy}>{busy ? "Запуск…" : "Запустить профиль нагрузки"}</button>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="jobs-list" aria-label="Активные задания нагрузки">
        {jobs.length === 0 ? <span className="muted">Заданий нагрузки пока нет</span> : jobs.map((job) => {
          const expectedEnd = job.started_at
            ? new Date(new Date(job.started_at).getTime() + job.profile.duration_seconds * 1000).toLocaleTimeString()
            : "в очереди";
          const kindLabels = { cpu: "CPU", memory: "память", disk: "диск", http: "HTTP" } as const;
          const statusLabels = { queued: "в очереди", running: "выполняется", completed: "завершено", stopped: "остановлено", failed: "ошибка" } as const;
          return <div className="job-row" key={job.id}><span><b>{kindLabels[job.profile.kind]}</b><small>{job.id} · {statusLabels[job.status]} · завершение ~{expectedEnd}</small></span>{["queued", "running"].includes(job.status) && <button className="button ghost" onClick={() => void onStop(job.id)}>Остановить</button>}</div>;
        })}
      </div>
    </section>
  );
}

