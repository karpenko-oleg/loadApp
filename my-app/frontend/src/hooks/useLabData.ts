import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type {
  ConnectionState,
  FaultState,
  LabEvent,
  LoadJob,
  LoadProfile,
  MetricsResponse,
  MetricsSnapshot,
} from "../types";

const POLL_INTERVAL_MS = 2000;
let eventSequence = 0;

function event(message: string, tone: LabEvent["tone"] = "info"): LabEvent {
  const randomId = typeof globalThis.crypto?.randomUUID === "function" ? globalThis.crypto.randomUUID() : undefined;
  return { id: randomId ?? `event-${Date.now()}-${eventSequence++}`, timestamp: new Date().toISOString(), message, tone };
}

export function useLabData() {
  const [snapshot, setSnapshot] = useState<MetricsSnapshot | null>(null);
  const [history, setHistory] = useState<MetricsSnapshot[]>([]);
  const [jobs, setJobs] = useState<LoadJob[]>([]);
  const [faults, setFaults] = useState<FaultState>({
    api_delay_ms: 0,
    error_rate: 0,
    readiness_degraded: false,
  });
  const [events, setEvents] = useState<LabEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const hasData = useRef(false);
  const activeRequest = useRef<AbortController | null>(null);

  const addEvent = useCallback((message: string, tone: LabEvent["tone"] = "info") => {
    setEvents((current) => [event(message, tone), ...current].slice(0, 30));
  }, []);

  const refresh = useCallback(async () => {
    if (activeRequest.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    try {
      const [metricsResult, jobsResult, faultsResult] = await Promise.allSettled([
        api.getMetrics(controller.signal),
        api.getJobs(controller.signal),
        api.getFaults(controller.signal),
      ]);
      if (controller.signal.aborted) return;
      if (metricsResult.status === "fulfilled") {
        setSnapshot(metricsResult.value.latest);
        setHistory(metricsResult.value.history);
        hasData.current = true;
        const ageMs = Date.now() - new Date(metricsResult.value.latest.timestamp).getTime();
        setConnectionState(ageMs > 5000 ? "stale" : "online");
      } else {
        setConnectionState(hasData.current ? "stale" : "offline");
        if (!hasData.current) {
          const reason = metricsResult.reason;
          addEvent(reason instanceof ApiError ? reason.message : "Сервис backend недоступен", "error");
        }
      }
      if (jobsResult.status === "fulfilled") setJobs(jobsResult.value);
      if (faultsResult.status === "fulfilled") setFaults(faultsResult.value);
    } catch (error) {
      if (!controller.signal.aborted) {
        setConnectionState(hasData.current ? "stale" : "offline");
        if (!hasData.current) addEvent(error instanceof ApiError ? error.message : "Сервис backend недоступен", "error");
      }
    } finally {
      window.clearTimeout(timeout);
      if (activeRequest.current === controller) activeRequest.current = null;
    }
  }, [addEvent]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
      activeRequest.current?.abort();
      activeRequest.current = null;
    };
  }, [refresh]);

  const startJob = useCallback(
    async (profile: LoadProfile) => {
      const job = await api.startJob(profile);
      setJobs((current) => [job, ...current]);
      addEvent(`Запущена нагрузка «${profile.kind}» на ${profile.duration_seconds} с`, "warning");
      return job;
    },
    [addEvent],
  );

  const stopJob = useCallback(
    async (id: string) => {
      const job = await api.stopJob(id);
      setJobs((current) => current.map((item) => (item.id === id ? job : item)));
      addEvent(`Остановлено задание нагрузки ${id}`, "success");
      return job;
    },
    [addEvent],
  );

  const updateFaults = useCallback(
    async (patch: Partial<FaultState>) => {
      const nextFaults = await api.updateFaults(patch);
      setFaults(nextFaults);
      addEvent("Настройки внедрения отказов обновлены", "warning");
      return nextFaults;
    },
    [addEvent],
  );

  return { snapshot, history, jobs, faults, events, connectionState, refresh, startJob, stopJob, updateFaults };
}

