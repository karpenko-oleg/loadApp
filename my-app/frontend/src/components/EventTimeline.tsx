import type { LabEvent } from "../types";

export function EventTimeline({ events }: { events: LabEvent[] }) {
  return <section className="panel timeline"><div className="card-heading"><div><span className="eyebrow">журнал оператора</span><h2>Хронология событий</h2></div></div>{events.length === 0 ? <span className="muted">Здесь появятся действия по мере работы с лабораторией.</span> : <div className="timeline-list">{events.map((item) => <div className={`timeline-item ${item.tone}`} key={item.id}><span className="timeline-dot" /><div><b>{item.message}</b><small>{new Date(item.timestamp).toLocaleTimeString()}</small></div></div>)}</div>}</section>;
}

