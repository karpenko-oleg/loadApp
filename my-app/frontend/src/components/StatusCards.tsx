import type { ConnectionState, MetricsSnapshot } from "../types";

function value(number: number, suffix = "") {
  return `${number.toFixed(number >= 100 ? 0 : 1)}${suffix}`;
}

export function StatusCards({ snapshot, connectionState }: { snapshot: MetricsSnapshot | null; connectionState: ConnectionState }) {
  const connectionLabels = { connecting: "подключение", online: "онлайн", stale: "устарела", offline: "нет связи" } as const;
  const cards = [
    ["CPU", snapshot ? value(snapshot.cpu_percent, "%") : "—", "вычислительная нагрузка"],
    ["Средняя нагрузка", snapshot ? value(snapshot.load_1m) : "—", "за 1 мин"],
    ["Память", snapshot ? value(snapshot.memory_percent, "%") : "—", snapshot ? `${value(snapshot.memory_available_mb)} МиБ свободно` : "ожидание"],
    ["Задержка API", snapshot ? value(snapshot.api_latency_ms, " мс") : "—", `${snapshot?.api_errors ?? 0} ошибок`],
  ];
  return (
    <section className="status-grid" aria-label="Текущее состояние системы">
      {cards.map(([label, main, caption]) => (
        <article className="stat-card" key={label}>
          <span className="eyebrow">{label}</span>
          <strong>{main}</strong>
          <span className="muted">{caption}</span>
        </article>
      ))}
      <article className={`stat-card connection ${connectionState}`}>
        <span className="eyebrow">Связь с телеметрией</span>
        <strong>{connectionLabels[connectionState]}</strong>
        <span className="muted">опрос каждые 2 с</span>
      </article>
    </section>
  );
}

