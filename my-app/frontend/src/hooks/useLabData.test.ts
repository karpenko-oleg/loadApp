import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { validateLoadProfile } from "../api";
import { useLabData } from "./useLabData";

const metricsPayload = {
  latest: {
    timestamp: new Date().toISOString(),
    cpu_percent: 20,
    load_1m: 0.4,
    memory_percent: 35,
    memory_available_mb: 1000,
    disk_usage_percent: 20,
    disk_read_mb: 1,
    disk_write_mb: 2,
    network_rx_mb: 3,
    network_tx_mb: 4,
    process_count: 12,
    api_latency_ms: 5,
    api_requests: 1,
    api_errors: 0,
  },
  history: [],
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  });
}

describe("useLabData", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("rejects unsafe load profiles before sending them", () => {
    expect(validateLoadProfile({ kind: "cpu", duration_seconds: 301 })).toContain(
      "Длительность должна быть от 1 до 300 секунд",
    );
    expect(validateLoadProfile({ kind: "memory", duration_seconds: 5, memory_mb: 513 })).toContain(
      "Память должна быть от 1 до 512 МиБ",
    );
    expect(validateLoadProfile({ kind: "cpu", duration_seconds: 5, intensity: 1.5 })).toContain(
      "Интенсивность должна быть от 0 до 1",
    );
  });

  it("reports offline initially and stale after a later polling failure", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useLabData());

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current.connectionState).toBe("offline");

    fetchMock
      .mockImplementationOnce(() => response(metricsPayload))
      .mockImplementationOnce(() => response([]))
      .mockImplementationOnce(() => response({ api_delay_ms: 0, error_rate: 0, readiness_degraded: false }));
    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.connectionState).toBe("online");

    fetchMock.mockRejectedValue(new Error("network down again"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(result.current.connectionState).toBe("stale");
  });

  it("keeps successful fault state when metrics polling fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = String(input);
        if (path.includes("/api/metrics")) return Promise.reject(new Error("metrics down"));
        if (path.includes("/api/load/jobs")) return response([]);
        return response({ api_delay_ms: 700, error_rate: 0.25, readiness_degraded: false });
      }),
    );
    const { result } = renderHook(() => useLabData());

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.connectionState).toBe("offline");
    expect(result.current.faults.api_delay_ms).toBe(700);
    expect(result.current.faults.error_rate).toBe(0.25);
  });
});

