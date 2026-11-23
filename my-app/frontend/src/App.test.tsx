import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FaultPanel } from "./components/FaultPanel";
import { LoadPanel } from "./components/LoadPanel";
import { MetricsChart } from "./components/MetricsChart";
import { StatusCards } from "./components/StatusCards";

describe("application root", () => {
  it("renders the lab title", async () => {
    const { default: App } = await import("./App");

    render(<App />);

    expect(screen.getByRole("heading", { name: /лаборатория диагностики vps/i })).toBeInTheDocument();
  });

  it("shows an explicit empty telemetry state", () => {
    render(<MetricsChart title="CPU" data={[]} dataKey="cpu_percent" color="#fff" />);

    expect(screen.getByText("Телеметрия пока недоступна")).toBeInTheDocument();
  });

  it("renders status values and lets an operator stop a running job", () => {
    const onStop = vi.fn(async () => undefined);
    render(
      <>
        <StatusCards
          snapshot={{
            timestamp: new Date().toISOString(), cpu_percent: 82, load_1m: 2, memory_percent: 70,
            memory_available_mb: 100, disk_usage_percent: 40, disk_read_mb: 1, disk_write_mb: 2,
            network_rx_mb: 3, network_tx_mb: 4, process_count: 8, api_latency_ms: 12, api_requests: 1, api_errors: 0,
          }}
          connectionState="online"
        />
        <LoadPanel
          jobs={[{ id: "job-1", profile: { kind: "cpu", duration_seconds: 20 }, status: "running", created_at: new Date().toISOString() }]}
          onStart={async () => undefined}
          onStop={onStop}
        />
      </>,
    );

    expect(screen.getByText("82.0%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Остановить" }));
    expect(onStop).toHaveBeenCalledWith("job-1");
  });

  it("sends fault toggle changes to the operator callback", () => {
    const onUpdate = vi.fn(async () => undefined);
    render(<FaultPanel faults={{ api_delay_ms: 0, error_rate: 0, readiness_degraded: false }} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByRole("checkbox", { name: /ухудшить readiness/i }));
    expect(onUpdate).toHaveBeenCalledWith({ readiness_degraded: true });
  });
});

