import { FaultPanel } from "./components/FaultPanel";
import { EventTimeline } from "./components/EventTimeline";
import { LoadPanel } from "./components/LoadPanel";
import { MetricsChart } from "./components/MetricsChart";
import { StatusCards } from "./components/StatusCards";
import { useLabData } from "./hooks/useLabData";
import "./styles.css";

export default function App() {
  const lab = useLabData();
  const connectionLabels = {
    connecting: "подключение",
    online: "онлайн",
    stale: "устарела",
    offline: "нет связи",
  } as const;
  return (
    <main className="app-shell">
      <header className="hero">
        <div><span className="eyebrow">учебный полигон DevOps · v1</span><h1>Лаборатория <em>диагностики VPS</em></h1><p>Создайте симптом. Найдите сигнал. Устраните инцидент.</p></div>
        <div className="hero-meta"><span className={`status-badge ${lab.connectionState}`}><i />{connectionLabels[lab.connectionState]}</span><span className="host-label">метрики контейнера</span></div>
      </header>
      <StatusCards snapshot={lab.snapshot} connectionState={lab.connectionState} />
      <section className="charts-grid">
        <MetricsChart title="Загрузка CPU" data={lab.history} dataKey="cpu_percent" color="#7c8cff" suffix="%" />
        <MetricsChart title="Использование памяти" data={lab.history} dataKey="memory_percent" color="#4fd1a5" suffix="%" />
        <MetricsChart title="Использование диска" data={lab.history} dataKey="disk_usage_percent" color="#ffb86b" suffix="%" />
        <MetricsChart title="Задержка API" data={lab.history} dataKey="api_latency_ms" color="#ff6f91" suffix=" мс" />
        <MetricsChart title="Запись на диск" data={lab.history} dataKey="disk_write_mb" color="#f2a7ff" suffix=" МиБ" />
        <MetricsChart title="Входящий трафик" data={lab.history} dataKey="network_rx_mb" color="#67d8ff" suffix=" МиБ" />
        <MetricsChart title="Количество процессов" data={lab.history} dataKey="process_count" color="#a9e86f" />
      </section>
      <section className="lower-grid"><LoadPanel jobs={lab.jobs} onStart={lab.startJob} onStop={lab.stopJob} /><FaultPanel faults={lab.faults} onUpdate={lab.updateFaults} /></section>
      <EventTimeline events={lab.events} />
      <footer><span>Лаборатория диагностики VPS</span><span>Используйте ответственно · нагрузка ограничена</span></footer>
    </main>
  );
}

