import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricsSnapshot } from "../types";

interface Props {
  title: string;
  data: MetricsSnapshot[];
  dataKey: keyof MetricsSnapshot;
  color: string;
  suffix?: string;
}

export function MetricsChart({ title, data, dataKey, color, suffix = "" }: Props) {
  return (
    <article className="chart-card">
      <div className="card-heading"><div><span className="eyebrow">телеметрия</span><h3>{title}</h3></div><span className="chart-dot" style={{ background: color }} /></div>
      {data.length === 0 ? <div className="empty-state">Телеметрия пока недоступна</div> : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs><linearGradient id={`gradient-${String(dataKey)}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.35} /><stop offset="100%" stopColor={color} stopOpacity={0.02} /></linearGradient></defs>
              <CartesianGrid stroke="#25304a" vertical={false} />
              <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" })} stroke="#68738c" tickLine={false} axisLine={false} />
              <YAxis stroke="#68738c" tickLine={false} axisLine={false} width={36} />
              <Tooltip contentStyle={{ background: "#11182b", border: "1px solid #2b395a", borderRadius: 10 }} formatter={(value: number) => [`${value.toFixed(1)}${suffix}`, title]} labelFormatter={(value) => new Date(value).toLocaleTimeString()} />
              <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#gradient-${String(dataKey)})`} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  );
}

