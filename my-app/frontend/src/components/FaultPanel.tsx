import { useState } from "react";
import type { FaultState } from "../types";

export function FaultPanel({ faults, onUpdate }: { faults: FaultState; onUpdate: (patch: Partial<FaultState>) => Promise<unknown> }) {
  const [error, setError] = useState<string | null>(null);
  const update = async (patch: Partial<FaultState>) => {
    try {
      setError(null);
      await onUpdate(patch);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось обновить настройки отказов");
    }
  };
  return (
    <section className="panel">
      <div className="card-heading"><div><span className="eyebrow">симулятор инцидентов</span><h2>Внедрение отказов</h2></div><span className="pill danger">используйте осторожно</span></div>
      <p className="panel-copy">Добавляйте симптомы намеренно, затем используйте health-check и графики задержки/ошибок, чтобы найти причину.</p>
      <label className="range-label">Задержка API <b>{faults.api_delay_ms} мс</b><input type="range" min="0" max="5000" step="50" value={faults.api_delay_ms} onChange={(event) => void update({ api_delay_ms: Number(event.target.value) })} /></label>
      <label className="range-label">Доля ошибок <b>{Math.round(faults.error_rate * 100)}%</b><input type="range" min="0" max="1" step="0.05" value={faults.error_rate} onChange={(event) => void update({ error_rate: Number(event.target.value) })} /></label>
      <label className="toggle"><input type="checkbox" checked={faults.readiness_degraded} onChange={(event) => void update({ readiness_degraded: event.target.checked })} /><span>Ухудшить readiness</span></label>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="warning-box">Держите лабораторию за firewall или VPN. В v1 намеренно нет аутентификации.</div>
    </section>
  );
}

